import pytest
from pathlib import Path
import yaml

from karakeep_sync.config import load_config, RepoConfig, Config, DEFAULT_CONFIG_PATH


def test_default_config_path_is_repo_relative():
    # config.yaml must resolve next to pyproject.toml in the repo's sync/ dir,
    # not a hardcoded ~/apps/karakeep path (README step 4: `cd sync; cp ... config.yaml`).
    assert DEFAULT_CONFIG_PATH.name == "config.yaml"
    assert (DEFAULT_CONFIG_PATH.parent / "pyproject.toml").exists()

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


def test_repo_exclude_lists_parsed(tmp_path):
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("public")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "karakeep": {"url": "http://localhost:3000", "api_key": "k"},
        "vault_root": "/tmp/vault",
        "repos": {
            "common": {
                "path": "Common",
                "remote": "https://t@github.com/u/c.git",
                "exclude_lists": ["Company"],
            },
        },
        "logs": {"dir": "/tmp/logs", "retention_days": 30},
    }))
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.repos["common"].exclude_lists == ["Company"]


def test_repo_exclude_lists_defaults_empty(tmp_path):
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("public")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(SAMPLE_YAML)  # exclude_lists 미지정
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.repos["common"].exclude_lists == []
    assert config.repos["common"].include_lists == []


def test_repo_include_lists_parsed(tmp_path):
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("internal")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "karakeep": {"url": "http://localhost:3000", "api_key": "k"},
        "vault_root": "/tmp/vault",
        "repos": {
            "company": {
                "path": "Company",
                "remote": "https://t@ghes.internal/u/c.git",
                "include_lists": ["Company"],
            },
        },
        "logs": {"dir": "/tmp/logs", "retention_days": 30},
    }))
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.repos["company"].include_lists == ["Company"]


def test_non_internal_mode_is_home(tmp_path):
    for mode in ["external", "home", "public", "whatever"]:
        mode_file = tmp_path / ".dotfiles-setup-mode"
        mode_file.write_text(mode)
        config_file = tmp_path / "config.yaml"
        config_file.write_text(SAMPLE_YAML)
        config = load_config(config_path=config_file, mode_file=mode_file)
        assert config.is_work is False


def test_unresolved_env_var_raises(tmp_path, monkeypatch):
    # 정의되지 않은 ${GHES_OWNER} 는 조용히 리터럴로 남지 않고 명확히 실패해야 한다
    # (그러지 않으면 git clone 이 ${GHES_OWNER} 가 박힌 URL 로 엉뚱하게 깨진다).
    monkeypatch.delenv("GHES_OWNER", raising=False)
    monkeypatch.delenv("GHES_PAT", raising=False)
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("internal")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "karakeep": {"url": "http://localhost:3000", "api_key": "k"},
        "vault_root": "/tmp/vault",
        "repos": {
            "company": {
                "path": "Company",
                "remote": "https://${GHES_PAT}@ghes.internal/${GHES_OWNER}/c.git",
                "include_lists": ["Company"],
            },
        },
        "logs": {"dir": "/tmp/logs", "retention_days": 30},
    }))
    with pytest.raises(ValueError, match="GHES_OWNER"):
        load_config(config_path=config_file, mode_file=mode_file)


def test_defined_env_var_is_expanded(tmp_path, monkeypatch):
    monkeypatch.setenv("GHES_PAT", "tok")
    monkeypatch.setenv("GHES_OWNER", "byoungwoo-yoon")
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("internal")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "karakeep": {"url": "http://localhost:3000", "api_key": "k"},
        "vault_root": "/tmp/vault",
        "repos": {
            "company": {
                "path": "Company",
                "remote": "https://${GHES_PAT}@ghes.internal/${GHES_OWNER}/c.git",
                "include_lists": ["Company"],
            },
        },
        "logs": {"dir": "/tmp/logs", "retention_days": 30},
    }))
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.repos["company"].remote == "https://tok@ghes.internal/byoungwoo-yoon/c.git"
