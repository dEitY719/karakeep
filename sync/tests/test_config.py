import pytest
from pathlib import Path
import yaml

from karakeep_sync.config import load_config, RepoConfig, Config, DEFAULT_CONFIG_PATH, _to_ssh


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

SAMPLE_YAML_WITH_COMPANY = yaml.dump({
    "karakeep": {"url": "http://localhost:3000", "api_key": "test-key"},
    "vault_root": "/tmp/vault",
    "repos": {
        "common": {
            "path": "Common",
            "remote": "https://TOKEN@github.com/user/common.git",
            "exclude_lists": ["Company"],
        },
        "company": {
            "path": "Company",
            "remote": "https://TOKEN@ghes.internal/user/company.git",
            "include_lists": ["Company"],
        },
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


def test_company_lists_defaults_empty_without_company_repo(tmp_path):
    # company repo 도 없고 명시 company_lists 도 없으면 가드레일은 꺼진 상태(빈 리스트).
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("public")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "karakeep": {"url": "http://localhost:3000", "api_key": "k"},
        "vault_root": "/tmp/vault",
        "repos": {
            "common": {"path": "Common", "remote": "https://t@github.com/u/c.git"},
        },
        "logs": {"dir": "/tmp/logs", "retention_days": 30},
    }))
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.company_lists == []


def test_company_lists_derived_from_company_repo_even_in_public_mode(tmp_path):
    # 핵심: external/home(public) 모드에선 company repo 가 드롭되지만, 사내 리스트 정의는
    # raw config 에서 유도되어야 한다 — 안 그러면 유출 위험이 가장 큰 PC 에서 가드레일이 꺼진다.
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("public")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(SAMPLE_YAML_WITH_COMPANY)
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.is_work is False
    assert "company" not in config.repos          # 모드상 드롭됨
    assert config.company_lists == ["Company"]     # 그래도 사내 리스트는 인지


def test_company_lists_explicit_top_level_overrides_derivation(tmp_path):
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("internal")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "karakeep": {"url": "http://localhost:3000", "api_key": "k"},
        "vault_root": "/tmp/vault",
        "company_lists": ["Company", "사내"],
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
    assert config.company_lists == ["Company", "사내"]


def test_company_repo_is_flagged_is_company(tmp_path):
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("internal")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(SAMPLE_YAML_WITH_COMPANY)
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.repos["company"].is_company is True
    assert config.repos["common"].is_company is False


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


# ── GIT_TRANSPORT / _to_ssh ──────────────────────────────────────────────

@pytest.mark.parametrize("https_url,ssh_url", [
    # PAT 자격증명 제거 + github.com
    ("https://ghp_x@github.com/dEitY719/bookmarks-common.git",
     "git@github.com:dEitY719/bookmarks-common.git"),
    # GHES ${VAR} 형식: 변환은 확장 전 RAW 에 적용 → host/owner 변수 보존(뒤에서 _expand).
    ("https://${GHES_PAT}@${GHES_HOST}/${GHES_OWNER}/bookmarks-company.git",
     "git@${GHES_HOST}:${GHES_OWNER}/bookmarks-company.git"),
    # owner:pat@ 형태 자격증명도 통째로 제거.
    ("https://owner:pat@github.com/o/r.git", "git@github.com:o/r.git"),
    # 이미 git@ 형식이면 무변경.
    ("git@github.com:o/r.git", "git@github.com:o/r.git"),
    # 이미 ssh:// 형식이면 무변경.
    ("ssh://git@github.com/o/r.git", "ssh://git@github.com/o/r.git"),
    # .git 접미사가 없어도 붙여준다.
    ("https://github.com/o/r", "git@github.com:o/r.git"),
])
def test_to_ssh(https_url, ssh_url):
    assert _to_ssh(https_url) == ssh_url


def test_load_config_ssh_transport_needs_no_pat(tmp_path, monkeypatch):
    # GIT_TRANSPORT=ssh + PAT 미설정 → remote 가 git@ 형식이 되어 ${GITHUB_PAT} 자격증명이
    # 통째로 사라지므로 _expand 가 raise 하지 않는다(하위 미해소 ${VAR} 도 없음).
    monkeypatch.setenv("GIT_TRANSPORT", "ssh")
    monkeypatch.delenv("GITHUB_PAT", raising=False)
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("home")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "karakeep": {"url": "http://localhost:3000", "api_key": "k"},
        "vault_root": "/tmp/vault",
        "repos": {
            "common": {
                "path": "Common",
                "remote": "https://${GITHUB_PAT}@github.com/dEitY719/bookmarks-common.git",
            },
        },
        "logs": {"dir": "/tmp/logs", "retention_days": 30},
    }))
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.repos["common"].remote == "git@github.com:dEitY719/bookmarks-common.git"
    assert "${" not in config.repos["common"].remote


def test_load_config_ssh_transport_internal_ghes(tmp_path, monkeypatch):
    # internal + ssh: GHES remote 도 git@${GHES_HOST}:... 로 재작성된 뒤 host/owner 변수만
    # _expand 로 확장된다 — GHES_PAT 는 SSH 라 필요 없다.
    monkeypatch.setenv("GIT_TRANSPORT", "ssh")
    monkeypatch.delenv("GHES_PAT", raising=False)
    monkeypatch.setenv("GHES_HOST", "ghes.example.com")
    monkeypatch.setenv("GHES_OWNER", "my-org")
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("internal")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "karakeep": {"url": "http://localhost:3000", "api_key": "k"},
        "vault_root": "/tmp/vault",
        "repos": {
            "company": {
                "path": "Company",
                "remote": "https://${GHES_PAT}@${GHES_HOST}/${GHES_OWNER}/bookmarks-company.git",
                "include_lists": ["Company"],
            },
        },
        "logs": {"dir": "/tmp/logs", "retention_days": 30},
    }))
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.repos["company"].remote == "git@ghes.example.com:my-org/bookmarks-company.git"


def test_load_config_https_transport_backward_compat(tmp_path, monkeypatch):
    # GIT_TRANSPORT unset(=기본 https) + PAT 설정 → 기존 HTTPS remote 유지(하위호환).
    monkeypatch.delenv("GIT_TRANSPORT", raising=False)
    monkeypatch.setenv("GITHUB_PAT", "ghp_tok")
    mode_file = tmp_path / ".dotfiles-setup-mode"
    mode_file.write_text("home")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "karakeep": {"url": "http://localhost:3000", "api_key": "k"},
        "vault_root": "/tmp/vault",
        "repos": {
            "common": {
                "path": "Common",
                "remote": "https://${GITHUB_PAT}@github.com/dEitY719/bookmarks-common.git",
            },
        },
        "logs": {"dir": "/tmp/logs", "retention_days": 30},
    }))
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.repos["common"].remote == "https://ghp_tok@github.com/dEitY719/bookmarks-common.git"

    # 명시적 https 도 동일.
    monkeypatch.setenv("GIT_TRANSPORT", "https")
    config = load_config(config_path=config_file, mode_file=mode_file)
    assert config.repos["common"].remote.startswith("https://")
