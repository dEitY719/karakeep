import pytest
from pathlib import Path
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
