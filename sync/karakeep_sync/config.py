from __future__ import annotations
import os
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
        config_path = DEFAULT_CONFIG_PATH
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
            exclude_lists=repo_raw.get("exclude_lists", []),
            include_lists=repo_raw.get("include_lists", []),
        )

    return Config(
        karakeep_url=_expand(raw["karakeep"]["url"]),
        karakeep_api_key=_expand(raw["karakeep"]["api_key"]),
        vault_root=vault_root,
        repos=repos,
        log_dir=Path(_expand(raw["logs"]["dir"])).expanduser(),
        is_work=is_work,
    )
