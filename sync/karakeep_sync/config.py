from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
import yaml

# config.yaml lives alongside pyproject.toml in the repo's sync/ dir
# (= karakeep_sync/../config.yaml), matching README step 4 and .gitignore.
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


@dataclass
class RepoConfig:
    path: Path
    remote: str
    push: bool
    pull: bool
    # 이 top-level 리스트에 속한 북마크는 이 repo export 에서 제외한다.
    # 회사(사내) 북마크가 공개 github repo 로 새어나가지 않게 하는 안전장치.
    exclude_lists: list[str] = field(default_factory=list)
    # 지정 시: 이 top-level 리스트에 속한 북마크만 이 repo 로 export 한다.
    # 예: 사내 GHES repo 는 include_lists=[Company] 로 회사 북마크만 담는다.
    include_lists: list[str] = field(default_factory=list)
    # 이 repo 가 사내(80-Company) 전용인지. True 면 §4.3 가드레일상 confidential
    # (company_lists 소속) 북마크의 유일한 합법 목적지가 된다. 기본은 repo 이름
    # 'company' 에서 자동 유추되며 config 의 is_company 로 override 할 수 있다.
    is_company: bool = False


@dataclass
class Config:
    karakeep_url: str
    karakeep_api_key: str
    vault_root: Path
    repos: dict[str, RepoConfig]
    log_dir: Path
    is_work: bool
    # 사내 전용으로 취급할 Karakeep top-level 리스트들 (§4.3 가드레일의 confidential 집합).
    # 이 리스트에 속한 북마크는 is_company repo 로만 export 된다.
    company_lists: list[str] = field(default_factory=list)


def _to_ssh(remote: str) -> str:
    """HTTPS git remote 를 SSH 형식(git@host:path.git)으로 변환한다.

    핵심: 변환은 반드시 _expand(치환) '이전'의 RAW 문자열에 적용한다. 그래야
    ${GHES_HOST}/${GHES_OWNER} 처럼 내부에 '/'·'@' 가 없는 변수가 host/path 안에
    그대로 보존된 채 나중에 _expand 로 정상 확장된다. 또한 SSH 형식은 자격증명
    (`${GITHUB_PAT}@`)을 통째로 버리므로 PAT 미설정 시에도 _expand 가 raise 하지
    않는다 — SSH 인증엔 PAT 가 필요 없기 때문이다.

    이미 `git@`/`ssh://` 형식이거나 매칭에 실패하면 원본을 그대로 반환한다.
    """
    if remote.startswith("git@") or remote.startswith("ssh://"):
        return remote
    m = re.match(r"^https?://(?:[^@/]*@)?([^/]+)/(.+?)(?:\.git)?/?$", remote)
    if not m:
        return remote
    host, path = m.group(1), m.group(2)
    return f"git@{host}:{path}.git"


def _expand(value: str) -> str:
    """${VAR} 를 환경변수로 치환한다.

    os.path.expandvars 는 정의되지 않은 ${VAR} 를 조용히 그대로 남겨서, 예를 들어
    remote URL 에 리터럴 ${GHES_OWNER} 가 박힌 채 git clone 이 엉뚱하게 실패한다.
    그런 침묵 실패 대신, 미치환 ${VAR} 가 남으면 어떤 변수가 비었는지 명확히 알린다.
    """
    expanded = os.path.expandvars(str(value))
    unresolved = re.findall(r"\$\{(\w+)\}", expanded)
    if unresolved:
        names = ", ".join(sorted(set(unresolved)))
        raise ValueError(
            f"환경변수가 설정되지 않았습니다: {names}. "
            f".env 에 추가한 뒤 'set -a && source ../.env && set +a' 로 다시 주입하세요. "
            f"(원본: {value})"
        )
    return expanded


def load_config(
    config_path: Path | None = None,
    mode_file: Path | None = None,
) -> Config:
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    if mode_file is None:
        mode_file = Path("~/.dotfiles-setup-mode").expanduser()

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    is_work = mode_file.read_text().strip() == "internal"
    vault_root = Path(_expand(raw["vault_root"])).expanduser()

    # transport 는 1회만 읽는다 (config.py 는 네트워크 프로브를 하지 않는다).
    # 'ssh' 일 때만 remote 를 git@ 형식으로 재작성하고, 그 외(unset/auto/https/미지의
    # 값)는 HTTPS 원본을 유지한다 → 완전 하위호환. auto→ssh/https 해소는 bootstrap 담당.
    transport = os.environ.get("GIT_TRANSPORT", "https").strip().lower()

    raw_repos = raw.get("repos", {})

    # 사내 리스트(§4.3): 명시 top-level company_lists 우선, 없으면 company repo 의
    # include_lists 에서 유도한다. raw 기준이라 external/home 에서 company repo 가
    # 드롭돼도(아래 skip) 사내 리스트 정의는 살아 있다 — 유출 위험이 가장 큰 PC 에서
    # 가드레일이 꺼지지 않게 하는 핵심.
    company_lists = raw.get("company_lists")
    if company_lists is None:
        company_lists = raw_repos.get("company", {}).get("include_lists", [])

    repos: dict[str, RepoConfig] = {}
    for name, repo_raw in raw_repos.items():
        if name == "company" and not is_work:
            continue
        push_allowed = True
        if name == "common" and is_work:
            push_allowed = False
        repo_remote_raw = repo_raw["remote"]
        if transport == "ssh":
            repo_remote_raw = _to_ssh(repo_remote_raw)
        repos[name] = RepoConfig(
            path=vault_root / repo_raw["path"],
            remote=_expand(repo_remote_raw),
            push=push_allowed,
            pull=repo_raw.get("pull", True),
            exclude_lists=repo_raw.get("exclude_lists", []),
            include_lists=repo_raw.get("include_lists", []),
            is_company=repo_raw.get("is_company", name == "company"),
        )

    return Config(
        karakeep_url=_expand(raw["karakeep"]["url"]),
        karakeep_api_key=_expand(raw["karakeep"]["api_key"]),
        vault_root=vault_root,
        repos=repos,
        log_dir=Path(_expand(raw["logs"]["dir"])).expanduser(),
        is_work=is_work,
        company_lists=list(company_lists),
    )
