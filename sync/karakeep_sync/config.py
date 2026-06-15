from __future__ import annotations
import os
from dataclasses import dataclass
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
        )

    return Config(
        karakeep_url=_expand(raw["karakeep"]["url"]),
        karakeep_api_key=_expand(raw["karakeep"]["api_key"]),
        vault_root=vault_root,
        repos=repos,
        log_dir=Path(_expand(raw["logs"]["dir"])).expanduser(),
        is_work=is_work,
    )
