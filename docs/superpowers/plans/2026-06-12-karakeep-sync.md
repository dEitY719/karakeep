# Karakeep Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Karakeep(로컬) ↔ Obsidian Markdown ↔ Git(GitHub/GHES) 양방향 sync를 수행하는 Python CLI `karakeep-sync`를 구축한다.

**Architecture:** 각 PC에 독립 Karakeep Docker 인스턴스. `~/.dotfiles-setup-mode == "internal"`이면 work(회사) 모드. 집 PC는 Common→GitHub push/pull, 회사 PC는 Company→GHES push/pull + GitHub pull-only. `sync-state.json`으로 북마크 origin을 추적하고, `updated` 타임스탬프 비교로 last-write-wins 충돌 해결.

**Tech Stack:** Python 3.11+, Click, httpx, PyYAML, pytest, pytest-httpx

---

## File Map

```
~/apps/karakeep/
├── docker-compose.yml           # Task 10: Karakeep Docker 설정
├── .env.example                 # Task 10: 환경변수 템플릿
├── .gitignore                   # Task 10
├── README.md                    # Task 11
└── sync/
    ├── pyproject.toml           # Task 1
    ├── config.yaml.example      # Task 10
    ├── tests/
    │   ├── __init__.py          # Task 1
    │   ├── test_config.py       # Task 2
    │   ├── test_state.py        # Task 3
    │   ├── test_karakeep.py     # Task 4
    │   ├── test_markdown.py     # Task 5
    │   ├── test_git_ops.py      # Task 6
    │   └── test_cli.py          # Task 7–9
    └── karakeep_sync/
        ├── __init__.py          # Task 1
        ├── config.py            # Task 2: config.yaml 로드 + mode 감지
        ├── state.py             # Task 3: sync-state.json 읽기/쓰기
        ├── karakeep.py          # Task 4: Karakeep REST API 클라이언트
        ├── markdown.py          # Task 5: bookmark ↔ Markdown 변환
        ├── git_ops.py           # Task 6: git pull/commit/push
        └── cli.py               # Task 7–9: Click CLI 진입점
```

---

### Task 1: 프로젝트 스캐폴딩

**Files:**
- Create: `sync/pyproject.toml`
- Create: `sync/karakeep_sync/__init__.py`
- Create: `sync/tests/__init__.py`

- [ ] **Step 1: `sync/pyproject.toml` 작성**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "karakeep-sync"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "httpx>=0.27",
    "pyyaml>=6.0",
]

[project.scripts]
karakeep-sync = "karakeep_sync.cli:cli"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-httpx>=0.30",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 빈 `__init__` 파일 생성**

```bash
touch sync/karakeep_sync/__init__.py sync/tests/__init__.py
```

- [ ] **Step 3: 패키지 설치**

```bash
cd ~/apps/karakeep/sync
pip install -e ".[dev]"
```

Expected: `Successfully installed karakeep-sync-0.1.0`

- [ ] **Step 4: Commit**

```bash
git add sync/pyproject.toml sync/karakeep_sync/__init__.py sync/tests/__init__.py
git commit -m "feat: scaffold karakeep-sync package"
```

---

### Task 2: config.py — 설정 로드 + PC 모드 감지

**Files:**
- Create: `sync/karakeep_sync/config.py`
- Create: `sync/tests/test_config.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# sync/tests/test_config.py
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml

from karakeep_sync.config import load_config, RepoConfig, Config

SAMPLE_YAML = yaml.dump({
    "karakeep": {"url": "http://localhost:3000", "api_key": "test-key"},
    "vault_root": "/tmp/vault",
    "repos": {
        "common": {"path": "Common", "remote": "https://TOKEN@github.com/user/common.git"},
        "company": {"path": "Company", "remote": "https://TOKEN@ghes.internal/user/company.git"},
    },
    "logs": {"dir": "/tmp/logs", "retention_days": 30},
})


def test_home_mode_excludes_company_repo(tmp_path):
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("public")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(SAMPLE_YAML)

    config = load_config(config_path=config_file, mode_file=mode_file)

    assert config.is_work is False
    assert "company" not in config.repos
    assert "common" in config.repos
    assert config.repos["common"].push is True


def test_work_mode_common_is_pull_only(tmp_path):
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("internal")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(SAMPLE_YAML)

    config = load_config(config_path=config_file, mode_file=mode_file)

    assert config.is_work is True
    assert config.repos["common"].push is False
    assert config.repos["common"].pull is True
    assert config.repos["company"].push is True


def test_non_internal_mode_is_home(tmp_path):
    for mode in ["external", "home", "public", "whatever"]:
        mode_file = tmp_path / ".dotfiles-setup-mode"
        mode_file.write_text(mode)
        config_file = tmp_path / "config.yaml"
        config_file.write_text(SAMPLE_YAML)
        config = load_config(config_path=config_file, mode_file=mode_file)
        assert config.is_work is False
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd ~/apps/karakeep/sync
pytest tests/test_config.py -v
```

Expected: `ImportError: cannot import name 'load_config'`

- [ ] **Step 3: `sync/karakeep_sync/config.py` 구현**

```python
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class RepoConfig:
    path: Path
    remote: str
    push: bool
    pull: bool


@dataclass
class Config:
    karakeep_url: str
    karakeep_api_key: str
    vault_root: Path
    repos: dict[str, RepoConfig]
    log_dir: Path
    is_work: bool


def _expand(value: str) -> str:
    return os.path.expandvars(str(value))


def load_config(
    config_path: Path | None = None,
    mode_file: Path | None = None,
) -> Config:
    if config_path is None:
        config_path = Path("~/apps/karakeep/sync/config.yaml").expanduser()
    if mode_file is None:
        mode_file = Path("~/.dotfiles-setup-mode").expanduser()

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    is_work = mode_file.read_text().strip() == "internal"
    vault_root = Path(_expand(raw["vault_root"])).expanduser()

    repos: dict[str, RepoConfig] = {}
    for name, repo_raw in raw.get("repos", {}).items():
        if name == "company" and not is_work:
            continue
        push_allowed = True
        if name == "common" and is_work:
            push_allowed = False
        repos[name] = RepoConfig(
            path=vault_root / repo_raw["path"],
            remote=_expand(repo_raw["remote"]),
            push=push_allowed,
            pull=repo_raw.get("pull", True),
        )

    return Config(
        karakeep_url=_expand(raw["karakeep"]["url"]),
        karakeep_api_key=_expand(raw["karakeep"]["api_key"]),
        vault_root=vault_root,
        repos=repos,
        log_dir=Path(_expand(raw["logs"]["dir"])).expanduser(),
        is_work=is_work,
    )
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_config.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add sync/karakeep_sync/config.py sync/tests/test_config.py
git commit -m "feat: add config loader with PC mode detection"
```

---

### Task 3: state.py — sync-state.json 읽기/쓰기

**Files:**
- Create: `sync/karakeep_sync/state.py`
- Create: `sync/tests/test_state.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# sync/tests/test_state.py
import json
from pathlib import Path
from karakeep_sync.state import load_state, save_state, BookmarkState


def test_load_empty_state(tmp_path):
    assert load_state(tmp_path / "state.json") == {}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    original = {
        "abc123": BookmarkState(updated="2024-01-01T00:00:00+09:00", repo="common", imported=False),
        "xyz789": BookmarkState(updated="2024-01-02T00:00:00+09:00", repo="company", imported=True),
    }
    save_state(original, path)
    loaded = load_state(path)
    assert loaded == original


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "state.json"
    save_state({}, path)
    assert path.exists()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_state.py -v
```

Expected: `ImportError: cannot import name 'load_state'`

- [ ] **Step 3: `sync/karakeep_sync/state.py` 구현**

```python
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

DEFAULT_STATE_PATH = Path("~/apps/karakeep/sync/sync-state.json").expanduser()


@dataclass
class BookmarkState:
    updated: str   # ISO 8601
    repo: str      # "common" | "company"
    imported: bool


def load_state(path: Path = DEFAULT_STATE_PATH) -> dict[str, BookmarkState]:
    if not path.exists():
        return {}
    with open(path) as f:
        raw = json.load(f)
    return {k: BookmarkState(**v) for k, v in raw.items()}


def save_state(state: dict[str, BookmarkState], path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({k: asdict(v) for k, v in state.items()}, f, indent=2)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_state.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add sync/karakeep_sync/state.py sync/tests/test_state.py
git commit -m "feat: add sync-state persistence"
```

---

### Task 4: karakeep.py — Karakeep API 클라이언트

**Files:**
- Create: `sync/karakeep_sync/karakeep.py`
- Create: `sync/tests/test_karakeep.py`

> **주의:** Karakeep API 응답 구조는 `http://localhost:3000/api-docs` (실행 중일 때)에서 확인. 아래 코드는 공개 OpenAPI spec 기준이며, 실제 필드명이 다를 경우 `_parse()` 메서드만 수정하면 된다.

- [ ] **Step 1: 실패 테스트 작성**

```python
# sync/tests/test_karakeep.py
import pytest
import httpx
from pytest_httpx import HTTPXMock
from karakeep_sync.karakeep import KarakeepClient, Bookmark

BASE = "http://localhost:3000"
KEY = "test-api-key"

BOOKMARK_RESPONSE = {
    "bookmarks": [
        {
            "id": "abc123",
            "url": "https://example.com",
            "title": "Example",
            "note": "my note",
            "tags": [{"name": "topic/python"}, {"name": "area/work"}],
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-02T00:00:00.000Z",
        }
    ]
}


def test_get_all_bookmarks(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="GET",
        url=f"{BASE}/api/v1/bookmarks",
        json=BOOKMARK_RESPONSE,
    )
    client = KarakeepClient(BASE, KEY)
    bookmarks = client.get_all_bookmarks()

    assert len(bookmarks) == 1
    bm = bookmarks[0]
    assert bm.id == "abc123"
    assert bm.url == "https://example.com"
    assert bm.tags == ["topic/python", "area/work"]
    assert bm.note == "my note"


def test_create_bookmark(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE}/api/v1/bookmarks",
        json={
            "id": "new001",
            "url": "https://new.com",
            "title": "New",
            "note": "",
            "tags": [],
            "createdAt": "2024-01-03T00:00:00.000Z",
            "updatedAt": "2024-01-03T00:00:00.000Z",
        },
    )
    client = KarakeepClient(BASE, KEY)
    bm = Bookmark(id="", url="https://new.com", title="New",
                  tags=[], created="", updated="", note="")
    created = client.create_bookmark(bm)
    assert created.id == "new001"


def test_update_bookmark(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="PATCH", url=f"{BASE}/api/v1/bookmarks/abc123", json={})
    client = KarakeepClient(BASE, KEY)
    bm = Bookmark(id="abc123", url="https://example.com", title="Updated",
                  tags=[], created="", updated="", note="new note")
    client.update_bookmark("abc123", bm)  # should not raise
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_karakeep.py -v
```

Expected: `ImportError: cannot import name 'KarakeepClient'`

- [ ] **Step 3: `sync/karakeep_sync/karakeep.py` 구현**

```python
from __future__ import annotations
from dataclasses import dataclass
import httpx


@dataclass
class Bookmark:
    id: str
    url: str
    title: str
    tags: list[str]
    created: str
    updated: str
    note: str = ""


class KarakeepClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def get_all_bookmarks(self) -> list[Bookmark]:
        resp = httpx.get(f"{self._base}/api/v1/bookmarks", headers=self._headers)
        resp.raise_for_status()
        return [self._parse(item) for item in resp.json()["bookmarks"]]

    def create_bookmark(self, bm: Bookmark) -> Bookmark:
        payload = {"url": bm.url, "title": bm.title, "note": bm.note}
        resp = httpx.post(
            f"{self._base}/api/v1/bookmarks", json=payload, headers=self._headers
        )
        resp.raise_for_status()
        return self._parse(resp.json())

    def update_bookmark(self, bookmark_id: str, bm: Bookmark) -> None:
        payload = {"title": bm.title, "note": bm.note}
        resp = httpx.patch(
            f"{self._base}/api/v1/bookmarks/{bookmark_id}",
            json=payload,
            headers=self._headers,
        )
        resp.raise_for_status()

    def _parse(self, item: dict) -> Bookmark:
        return Bookmark(
            id=item["id"],
            url=item["url"],
            title=item.get("title") or "",
            tags=[t["name"] for t in item.get("tags", [])],
            created=item["createdAt"],
            updated=item["updatedAt"],
            note=item.get("note") or "",
        )
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_karakeep.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add sync/karakeep_sync/karakeep.py sync/tests/test_karakeep.py
git commit -m "feat: add Karakeep API client"
```

---

### Task 5: markdown.py — Bookmark ↔ Markdown 변환

**Files:**
- Create: `sync/karakeep_sync/markdown.py`
- Create: `sync/tests/test_markdown.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# sync/tests/test_markdown.py
from karakeep_sync.karakeep import Bookmark
from karakeep_sync.markdown import bookmark_to_md, md_to_bookmark, bookmark_filename


BM = Bookmark(
    id="abc123",
    url="https://example.com/article",
    title="Example Article",
    tags=["topic/python", "area/work"],
    created="2024-01-01T00:00:00+09:00",
    updated="2024-01-02T00:00:00+09:00",
    note="my note here",
)


def test_bookmark_filename():
    assert bookmark_filename(BM) == "abc123.md"


def test_bookmark_to_md_contains_frontmatter():
    md = bookmark_to_md(BM)
    assert "id: abc123" in md
    assert "url: https://example.com/article" in md
    assert "topic/python" in md
    assert "my note here" in md
    assert md.startswith("---\n")


def test_md_to_bookmark_roundtrip():
    md = bookmark_to_md(BM)
    result = md_to_bookmark(md)
    assert result.id == BM.id
    assert result.url == BM.url
    assert result.title == BM.title
    assert result.tags == BM.tags
    assert result.note == BM.note
    assert result.updated == BM.updated


def test_md_to_bookmark_no_note():
    bm_no_note = Bookmark(
        id="xyz", url="https://x.com", title="X",
        tags=[], created="2024-01-01T00:00:00Z",
        updated="2024-01-01T00:00:00Z", note=""
    )
    md = bookmark_to_md(bm_no_note)
    result = md_to_bookmark(md)
    assert result.note == ""
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_markdown.py -v
```

Expected: `ImportError: cannot import name 'bookmark_to_md'`

- [ ] **Step 3: `sync/karakeep_sync/markdown.py` 구현**

```python
from __future__ import annotations
import re
import yaml
from karakeep_sync.karakeep import Bookmark


def bookmark_filename(bm: Bookmark) -> str:
    return f"{bm.id}.md"


def bookmark_to_md(bm: Bookmark) -> str:
    frontmatter = {
        "id": bm.id,
        "url": bm.url,
        "title": bm.title,
        "tags": bm.tags,
        "created": bm.created,
        "updated": bm.updated,
        "source": "karakeep",
    }
    fm = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False).strip()
    body = bm.note.strip()
    if body:
        return f"---\n{fm}\n---\n\n{body}\n"
    return f"---\n{fm}\n---\n"


def md_to_bookmark(content: str) -> Bookmark:
    match = re.match(r"^---\n(.*?)\n---\n?(.*)?$", content, re.DOTALL)
    if not match:
        raise ValueError("Invalid Markdown: missing frontmatter")
    fm = yaml.safe_load(match.group(1))
    note = (match.group(2) or "").strip()
    return Bookmark(
        id=str(fm["id"]),
        url=fm["url"],
        title=fm.get("title") or "",
        tags=fm.get("tags") or [],
        created=str(fm["created"]),
        updated=str(fm["updated"]),
        note=note,
    )
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_markdown.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add sync/karakeep_sync/markdown.py sync/tests/test_markdown.py
git commit -m "feat: add bookmark/markdown conversion"
```

---

### Task 6: git_ops.py — git 연산

**Files:**
- Create: `sync/karakeep_sync/git_ops.py`
- Create: `sync/tests/test_git_ops.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# sync/tests/test_git_ops.py
import subprocess
from pathlib import Path
import pytest
from karakeep_sync.git_ops import run_git, pull, commit_and_push, changed_files_after_pull


def make_bare_remote(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    remote.mkdir()
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    return remote


def init_repo_with_commit(tmp_path: Path, remote: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True, capture_output=True)
    (repo / "init.txt").write_text("init")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init",
                    "--author=Test <test@test.com>"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", "HEAD:main"], check=True, capture_output=True)
    return repo


def test_run_git_returns_stdout(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    out = run_git(["status", "--short"], cwd=repo)
    assert isinstance(out, str)


def test_run_git_raises_on_failure(tmp_path):
    with pytest.raises(RuntimeError):
        run_git(["status"], cwd=tmp_path / "nonexistent")


def test_commit_and_push(tmp_path):
    remote = make_bare_remote(tmp_path)
    repo = init_repo_with_commit(tmp_path, remote)

    new_file = repo / "test.md"
    new_file.write_text("hello")
    commit_and_push(repo, [new_file], "test: add file")

    # Verify pushed
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline"],
        capture_output=True, text=True
    )
    assert "test: add file" in out.stdout


def test_changed_files_after_pull_on_first_commit(tmp_path):
    remote = make_bare_remote(tmp_path)
    repo = init_repo_with_commit(tmp_path, remote)
    files = changed_files_after_pull(repo)
    # First commit: all files returned
    assert any(f.name == "init.txt" for f in files)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_git_ops.py -v
```

Expected: `ImportError: cannot import name 'run_git'`

- [ ] **Step 3: `sync/karakeep_sync/git_ops.py` 구현**

```python
from __future__ import annotations
import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {cwd}:\n{result.stderr}"
        )
    return result.stdout.strip()


def clone(remote: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", remote, str(path)], check=True)


def pull(path: Path) -> None:
    run_git(["pull", "--ff-only"], cwd=path)


def changed_files_after_pull(path: Path) -> list[Path]:
    try:
        output = run_git(["diff", "--name-only", "HEAD~1..HEAD"], cwd=path)
    except RuntimeError:
        # Only one commit exists (initial clone) — treat all tracked files as changed
        output = run_git(["ls-files"], cwd=path)
    if not output:
        return []
    return [path / f for f in output.splitlines() if f]


def commit_and_push(path: Path, files: list[Path], message: str) -> None:
    for f in files:
        run_git(["add", str(f)], cwd=path)
    run_git(["commit", "-m", message], cwd=path)
    run_git(["push"], cwd=path)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_git_ops.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add sync/karakeep_sync/git_ops.py sync/tests/test_git_ops.py
git commit -m "feat: add git operations wrapper"
```

---

### Task 7: cli.py — `push` 커맨드

**Files:**
- Create: `sync/karakeep_sync/cli.py`
- Create: `sync/tests/test_cli.py` (push 부분)

- [ ] **Step 1: 실패 테스트 작성**

```python
# sync/tests/test_cli.py
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from karakeep_sync.cli import cli
from karakeep_sync.karakeep import Bookmark
from karakeep_sync.state import BookmarkState


def make_config(tmp_path, is_work=False):
    from karakeep_sync.config import Config, RepoConfig
    repo_path = tmp_path / "Common"
    repo_path.mkdir(parents=True)
    return Config(
        karakeep_url="http://localhost:3000",
        karakeep_api_key="key",
        vault_root=tmp_path,
        repos={
            "common": RepoConfig(
                path=repo_path,
                remote="https://token@github.com/user/common.git",
                push=True,
                pull=True,
            )
        },
        log_dir=tmp_path / "logs",
        is_work=is_work,
    )


NEW_BM = Bookmark(
    id="abc123", url="https://example.com", title="Example",
    tags=["topic/python"], created="2024-01-01T00:00:00Z",
    updated="2024-01-02T00:00:00Z", note="note"
)


def test_push_creates_md_and_calls_git(tmp_path):
    config = make_config(tmp_path)
    state_path = tmp_path / "state.json"

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value={}),
        patch("karakeep_sync.cli.save_state") as mock_save,
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
        patch("karakeep_sync.cli.commit_and_push") as mock_git,
    ):
        MockClient.return_value.get_all_bookmarks.return_value = [NEW_BM]

        runner = CliRunner()
        result = runner.invoke(cli, ["push"])

    assert result.exit_code == 0, result.output
    md_file = config.repos["common"].path / "abc123.md"
    assert md_file.exists()
    mock_git.assert_called_once()
    mock_save.assert_called_once()


def test_push_skips_imported_bookmark(tmp_path):
    config = make_config(tmp_path)
    existing_state = {
        "abc123": BookmarkState(updated="2024-01-02T00:00:00Z", repo="common", imported=True)
    }

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value=existing_state),
        patch("karakeep_sync.cli.save_state"),
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
        patch("karakeep_sync.cli.commit_and_push") as mock_git,
    ):
        MockClient.return_value.get_all_bookmarks.return_value = [NEW_BM]

        runner = CliRunner()
        result = runner.invoke(cli, ["push"])

    assert result.exit_code == 0
    mock_git.assert_not_called()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_cli.py::test_push_creates_md_and_calls_git tests/test_cli.py::test_push_skips_imported_bookmark -v
```

Expected: `ImportError: cannot import name 'cli'`

- [ ] **Step 3: `sync/karakeep_sync/cli.py` — push 구현**

```python
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import click

from karakeep_sync.config import load_config
from karakeep_sync.state import load_state, save_state, BookmarkState
from karakeep_sync.karakeep import KarakeepClient
from karakeep_sync.markdown import bookmark_to_md, bookmark_filename
from karakeep_sync.git_ops import pull, changed_files_after_pull, commit_and_push


@click.group()
def cli() -> None:
    pass


@cli.command()
def push() -> None:
    """Karakeep → Markdown → git push"""
    config = load_config()
    state = load_state()
    client = KarakeepClient(config.karakeep_url, config.karakeep_api_key)
    bookmarks = client.get_all_bookmarks()

    for repo_name, repo in config.repos.items():
        if not repo.push:
            continue

        changed: list[Path] = []
        for bm in bookmarks:
            bm_state = state.get(bm.id)
            if bm_state and bm_state.imported:
                continue
            if bm_state and bm_state.updated >= bm.updated:
                continue

            md_path = repo.path / bookmark_filename(bm)
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(bookmark_to_md(bm))
            changed.append(md_path)
            state[bm.id] = BookmarkState(updated=bm.updated, repo=repo_name, imported=False)

        if changed:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            commit_and_push(repo.path, changed, f"sync: push {len(changed)} bookmarks [{now}]")

    save_state(state)
    click.echo("Push complete.")
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_cli.py::test_push_creates_md_and_calls_git tests/test_cli.py::test_push_skips_imported_bookmark -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add sync/karakeep_sync/cli.py sync/tests/test_cli.py
git commit -m "feat: add cli push command"
```

---

### Task 8: cli.py — `pull` 커맨드

**Files:**
- Modify: `sync/karakeep_sync/cli.py`
- Modify: `sync/tests/test_cli.py`

- [ ] **Step 1: 실패 테스트 추가**

`sync/tests/test_cli.py` 하단에 추가:

```python
def test_pull_imports_new_bookmark(tmp_path):
    config = make_config(tmp_path)
    # Create an MD file in the repo path (simulating git pull result)
    md_path = config.repos["common"].path / "abc123.md"
    md_path.write_text(
        "---\nid: abc123\nurl: https://example.com\ntitle: Example\n"
        "tags: [topic/python]\ncreated: '2024-01-01T00:00:00Z'\n"
        "updated: '2024-01-02T00:00:00Z'\nsource: karakeep\n---\n"
    )

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value={}),
        patch("karakeep_sync.cli.save_state") as mock_save,
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
        patch("karakeep_sync.cli.pull"),
        patch("karakeep_sync.cli.changed_files_after_pull", return_value=[md_path]),
    ):
        mock_client = MockClient.return_value
        mock_client.get_all_bookmarks.return_value = []
        mock_client.create_bookmark.return_value = NEW_BM

        runner = CliRunner()
        result = runner.invoke(cli, ["pull"])

    assert result.exit_code == 0, result.output
    mock_client.create_bookmark.assert_called_once()
    mock_save.assert_called_once()


def test_pull_skips_when_karakeep_is_newer(tmp_path):
    config = make_config(tmp_path)
    md_path = config.repos["common"].path / "abc123.md"
    md_path.write_text(
        "---\nid: abc123\nurl: https://example.com\ntitle: Old\n"
        "tags: []\ncreated: '2024-01-01T00:00:00Z'\n"
        "updated: '2024-01-01T00:00:00Z'\nsource: karakeep\n---\n"
    )
    # Karakeep has newer version (2024-01-02)
    newer_bm = Bookmark(id="abc123", url="https://example.com", title="Newer",
                        tags=[], created="2024-01-01T00:00:00Z",
                        updated="2024-01-02T00:00:00Z", note="")

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value={}),
        patch("karakeep_sync.cli.save_state"),
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
        patch("karakeep_sync.cli.pull"),
        patch("karakeep_sync.cli.changed_files_after_pull", return_value=[md_path]),
    ):
        mock_client = MockClient.return_value
        mock_client.get_all_bookmarks.return_value = [newer_bm]

        runner = CliRunner()
        result = runner.invoke(cli, ["pull"])

    assert result.exit_code == 0
    mock_client.update_bookmark.assert_not_called()
    mock_client.create_bookmark.assert_not_called()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_cli.py::test_pull_imports_new_bookmark tests/test_cli.py::test_pull_skips_when_karakeep_is_newer -v
```

Expected: `Error: No such command 'pull'`

- [ ] **Step 3: `pull` 커맨드를 cli.py에 추가**

먼저 cli.py 상단 import에 `md_to_bookmark` 추가:

```python
from karakeep_sync.markdown import bookmark_to_md, bookmark_filename, md_to_bookmark
```

그 다음 `push()` 함수 아래에 추가:

```python
@cli.command(name="pull")
def pull_cmd() -> None:
    """git pull → Markdown → Karakeep import"""
    config = load_config()
    state = load_state()
    client = KarakeepClient(config.karakeep_url, config.karakeep_api_key)
    existing = {bm.url: bm for bm in client.get_all_bookmarks()}

    for repo_name, repo in config.repos.items():
        if not repo.pull:
            continue
        pull(repo.path)
        changed_files = changed_files_after_pull(repo.path)

        for md_path in changed_files:
            if md_path.suffix != ".md":
                continue
            try:
                bm = md_to_bookmark(md_path.read_text())
            except (ValueError, KeyError):
                continue

            existing_bm = existing.get(bm.url)
            if existing_bm is None:
                created = client.create_bookmark(bm)
                state[created.id] = BookmarkState(
                    updated=bm.updated, repo=repo_name, imported=True
                )
            elif bm.updated > existing_bm.updated:
                client.update_bookmark(existing_bm.id, bm)
                state[existing_bm.id] = BookmarkState(
                    updated=bm.updated, repo=repo_name, imported=True
                )

    save_state(state)
    click.echo("Pull complete.")
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_cli.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add sync/karakeep_sync/cli.py sync/tests/test_cli.py
git commit -m "feat: add cli pull command"
```

---

### Task 9: cli.py — `auto`, `status`, `init` 커맨드

**Files:**
- Modify: `sync/karakeep_sync/cli.py`
- Modify: `sync/tests/test_cli.py`

- [ ] **Step 1: 실패 테스트 추가**

`sync/tests/test_cli.py` 하단에 추가:

```python
def test_auto_runs_pull_then_push(tmp_path):
    config = make_config(tmp_path)
    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value={}),
        patch("karakeep_sync.cli.save_state"),
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
        patch("karakeep_sync.cli.pull"),
        patch("karakeep_sync.cli.changed_files_after_pull", return_value=[]),
        patch("karakeep_sync.cli.commit_and_push"),
    ):
        MockClient.return_value.get_all_bookmarks.return_value = []
        runner = CliRunner()
        result = runner.invoke(cli, ["auto"])

    assert result.exit_code == 0
    assert "Pull complete" in result.output
    assert "Push complete" in result.output


def test_status_shows_pending_count(tmp_path):
    config = make_config(tmp_path)
    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value={}),
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
    ):
        MockClient.return_value.get_all_bookmarks.return_value = [NEW_BM]
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

    assert result.exit_code == 0
    assert "1" in result.output
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_cli.py::test_auto_runs_pull_then_push tests/test_cli.py::test_status_shows_pending_count -v
```

Expected: `Error: No such command 'auto'`

- [ ] **Step 3: `auto`, `status`, `init` 커맨드를 cli.py에 추가**

`cli.py` 하단에 추가:

```python
@cli.command()
@click.pass_context
def auto(ctx: click.Context) -> None:
    """git pull → Karakeep import → Karakeep export → git push (cron용)"""
    ctx.invoke(pull_cmd)
    ctx.invoke(push)


@cli.command()
def status() -> None:
    """동기화되지 않은 북마크 수 출력"""
    config = load_config()
    state = load_state()
    client = KarakeepClient(config.karakeep_url, config.karakeep_api_key)
    bookmarks = client.get_all_bookmarks()

    pending = [
        bm for bm in bookmarks
        if bm.id not in state or state[bm.id].updated < bm.updated
    ]
    click.echo(f"Pending push: {len(pending)} bookmark(s)")


@cli.command()
def init() -> None:
    """git clone, cron 등록"""
    import subprocess
    config = load_config()

    for repo_name, repo in config.repos.items():
        if repo.path.exists():
            click.echo(f"[{repo_name}] Already exists: {repo.path}")
            continue
        click.echo(f"[{repo_name}] Cloning {repo.remote} → {repo.path}")
        repo.path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", repo.remote, str(repo.path)], check=True)
        click.echo(f"[{repo_name}] Done.")

    # cron 등록
    sync_bin = Path(__file__).parent.parent / ".venv" / "bin" / "karakeep-sync"
    log_path = config.log_dir / "cron.log"
    config.log_dir.mkdir(parents=True, exist_ok=True)
    cron_line = f"*/30 * * * * {sync_bin} auto >> {log_path} 2>&1"
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""
    if cron_line in existing:
        click.echo("Cron already registered.")
    else:
        new_crontab = existing.rstrip("\n") + f"\n{cron_line}\n"
        subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)
        click.echo(f"Cron registered: {cron_line}")
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_cli.py -v
```

Expected: `6 passed`

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
pytest sync/tests/ -v
```

Expected: `모든 테스트 passed`

- [ ] **Step 6: Commit**

```bash
git add sync/karakeep_sync/cli.py sync/tests/test_cli.py
git commit -m "feat: add cli auto/status/init commands"
```

---

### Task 10: Docker Compose + 설정 파일 템플릿

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `sync/config.yaml.example`

- [ ] **Step 1: `docker-compose.yml` 작성**

```yaml
# ~/apps/karakeep/docker-compose.yml
services:
  karakeep:
    image: ghcr.io/karakeep-app/karakeep:release
    ports:
      - "3000:3000"
    volumes:
      - ./data:/data
    env_file: .env
    restart: unless-stopped
```

- [ ] **Step 2: `.env.example` 작성**

```bash
# ~/apps/karakeep/.env.example
KARAKEEP_API_KEY=your-api-key-here
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
GHES_PAT=ghes_xxxxxxxxxxxxxxxxxxxx   # 회사 PC만 필요
GHES_HOST=ghes.your-company.internal  # 실제 GHES 호스트명
```

- [ ] **Step 3: `.gitignore` 작성**

```gitignore
# ~/apps/karakeep/.gitignore
.env
data/
logs/
sync/sync-state.json
sync/config.yaml
sync/.venv/
sync/__pycache__/
sync/**/__pycache__/
sync/**/*.pyc
sync/.pytest_cache/
```

- [ ] **Step 4: `sync/config.yaml.example` 작성**

```yaml
# sync/config.yaml.example
# 이 파일을 config.yaml로 복사하고 값을 채워넣으세요
karakeep:
  url: http://localhost:3000
  api_key: ${KARAKEEP_API_KEY}

vault_root: ~/obsidian-vault/10_Bookmarks

repos:
  common:
    path: Common
    remote: https://${GITHUB_PAT}@github.com/dEitY719/bookmarks-common.git
    pull: true
  company:
    path: Company
    remote: https://${GHES_PAT}@${GHES_HOST}/dEitY719/bookmarks-company.git
    pull: true

logs:
  dir: ~/apps/karakeep/logs
  retention_days: 30
```

- [ ] **Step 5: Karakeep 실행 확인**

```bash
cd ~/apps/karakeep
cp .env.example .env
# .env 파일 편집: API key 등 실제 값으로 채우기
docker compose up -d
docker compose logs -f
```

Expected: `karakeep-1  | Listening on port 3000`

브라우저에서 `http://localhost:3000` 열어서 계정 생성 후 API key 발급 → `.env`에 저장.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml .env.example .gitignore sync/config.yaml.example
git commit -m "feat: add docker-compose and config templates"
```

---

### Task 11: README.md 작성

**Files:**
- Create: `README.md`

- [ ] **Step 1: `README.md` 작성**

아래 내용으로 `~/apps/karakeep/README.md` 파일 생성:

    # karakeep

    개인 북마크 관리 시스템. Karakeep(로컬 캡처) → Obsidian Markdown → Git(GitHub/GHES) 양방향 sync.

    ## 요구사항

    - Docker, Docker Compose
    - Python 3.11+
    - Git

    ## 최초 설치

        # 1. Karakeep 실행
        cp .env.example .env   # .env 편집: API key + PAT 입력
        docker compose up -d

        # 2. sync 패키지 설치
        cd sync
        python -m venv .venv
        source .venv/bin/activate
        pip install -e ".[dev]"

        # 3. config 설정
        cp config.yaml.example config.yaml   # config.yaml 편집

        # 4. 초기화 (git clone + cron 등록)
        karakeep-sync init

        # 5. 기존 북마크 import
        karakeep-sync pull

    ## 일상 사용

    | 명령 | 설명 |
    |------|------|
    | `karakeep-sync push` | Karakeep → git push |
    | `karakeep-sync pull` | git pull → Karakeep import |
    | `karakeep-sync auto` | pull + push (cron 자동 실행) |
    | `karakeep-sync status` | 미동기 북마크 수 확인 |

    cron은 `init` 시 자동 등록됨 (30분마다 `auto` 실행).

    ## Docker 운영

        docker compose up -d                          # 시작
        docker compose down                           # 중지
        docker compose pull && docker compose up -d   # 업데이트
        docker compose logs -f                        # 로그 확인

    ## PC 모드

    `~/.dotfiles-setup-mode` 파일 기준:
    - `internal` → 회사 모드: Company(GHES) push/pull + Common(GitHub) pull only
    - 그 외 → 집 모드: Common(GitHub) push/pull

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with installation and operation guide"
```

---

### Task 12: Obsidian Vault 폴더 구조 설정

**Files:**
- Create: `~/obsidian-vault/10_Bookmarks/Common/` (git init → GitHub)
- Create: `~/obsidian-vault/10_Bookmarks/Company/` (git init → GHES, 회사 PC만)
- Create: `~/obsidian-vault/.gitignore`

- [ ] **Step 1: Vault 폴더 생성 및 git 초기화 (집 PC)**

```bash
mkdir -p ~/obsidian-vault/10_Bookmarks/Common
cd ~/obsidian-vault/10_Bookmarks/Common
git init
git remote add origin https://${GITHUB_PAT}@github.com/dEitY719/bookmarks-common.git
# GitHub에 빈 private repo 먼저 생성 후:
git commit --allow-empty -m "init"
git push -u origin main
```

- [ ] **Step 2: Vault 루트 `.gitignore` 작성**

```gitignore
# ~/obsidian-vault/.gitignore
10_Bookmarks/Common/
10_Bookmarks/Company/
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.trash/
.DS_Store
Thumbs.db
```

- [ ] **Step 3: 동작 확인**

```bash
karakeep-sync init    # Common repo clone
karakeep-sync status  # 동기화 대기 북마크 수 확인
karakeep-sync auto    # 첫 번째 full sync
```

Expected:
```
Pending push: N bookmark(s)
Pull complete.
Push complete.
```

- [ ] **Step 4: Commit**

```bash
git add README.md   # Obsidian vault setup 참고 내용 추가 시
git commit -m "docs: add obsidian vault setup instructions"
```

---

## 전체 테스트

```bash
cd ~/apps/karakeep/sync
pytest tests/ -v
```

Expected: `모든 테스트 passed`
