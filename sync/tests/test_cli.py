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


def test_push_writes_lists_to_frontmatter(tmp_path):
    config = make_config(tmp_path)

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value={}),
        patch("karakeep_sync.cli.save_state"),
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
        patch("karakeep_sync.cli.commit_and_push"),
    ):
        mc = MockClient.return_value
        mc.get_all_bookmarks.return_value = [NEW_BM]
        mc.get_bookmark_list_paths.return_value = {
            "abc123": ["AI 도구", "미국 주식 사이트/11 IPO·SPAC"]
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["push"])

    assert result.exit_code == 0, result.output
    md = (config.repos["common"].path / "abc123.md").read_text()
    assert "lists:" in md
    assert "미국 주식 사이트/11 IPO·SPAC" in md


def test_push_force_reexports_unchanged(tmp_path):
    config = make_config(tmp_path)
    # 이미 같은 타임스탬프로 내보낸 상태 → 평소엔 skip 되지만 --force 는 다시 쓴다.
    existing_state = {
        "abc123": BookmarkState(updated="2024-01-02T00:00:00Z", repo="common", imported=False)
    }

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value=existing_state),
        patch("karakeep_sync.cli.save_state"),
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
        patch("karakeep_sync.cli.commit_and_push") as mock_git,
    ):
        mc = MockClient.return_value
        mc.get_all_bookmarks.return_value = [NEW_BM]
        mc.get_bookmark_list_paths.return_value = {"abc123": ["AI 도구"]}

        runner = CliRunner()
        result = runner.invoke(cli, ["push", "--force"])

    assert result.exit_code == 0, result.output
    assert (config.repos["common"].path / "abc123.md").exists()
    mock_git.assert_called_once()


def test_push_without_force_skips_unchanged(tmp_path):
    config = make_config(tmp_path)
    existing_state = {
        "abc123": BookmarkState(updated="2024-01-02T00:00:00Z", repo="common", imported=False)
    }

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value=existing_state),
        patch("karakeep_sync.cli.save_state"),
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
        patch("karakeep_sync.cli.commit_and_push") as mock_git,
    ):
        mc = MockClient.return_value
        mc.get_all_bookmarks.return_value = [NEW_BM]
        mc.get_bookmark_list_paths.return_value = {"abc123": ["AI 도구"]}

        runner = CliRunner()
        result = runner.invoke(cli, ["push"])

    assert result.exit_code == 0, result.output
    mock_git.assert_not_called()


def test_push_excludes_bookmarks_in_excluded_list(tmp_path):
    config = make_config(tmp_path)
    config.repos["common"].exclude_lists = ["Company"]
    company_bm = Bookmark(
        id="comp1", url="https://kor2.samsung.net/portalapp/home", title="사내",
        tags=[], created="2024-01-01T00:00:00Z", updated="2024-01-02T00:00:00Z", note="",
    )

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value={}),
        patch("karakeep_sync.cli.save_state"),
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
        patch("karakeep_sync.cli.commit_and_push"),
    ):
        mc = MockClient.return_value
        mc.get_all_bookmarks.return_value = [NEW_BM, company_bm]
        mc.get_bookmark_list_paths.return_value = {
            "abc123": ["미국 주식 사이트"],
            "comp1": ["Company"],
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["push"])

    assert result.exit_code == 0, result.output
    # 공통 북마크는 export, 회사 북마크는 제외(공개 repo 로 안 나감)
    assert (config.repos["common"].path / "abc123.md").exists()
    assert not (config.repos["common"].path / "comp1.md").exists()


def test_push_include_lists_exports_only_matching(tmp_path):
    config = make_config(tmp_path)
    config.repos["common"].include_lists = ["Company"]  # 회사 repo 흉내: Company 만
    company_bm = Bookmark(
        id="comp1", url="https://kor2.samsung.net/portalapp/home", title="사내",
        tags=[], created="2024-01-01T00:00:00Z", updated="2024-01-02T00:00:00Z", note="",
    )

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.load_state", return_value={}),
        patch("karakeep_sync.cli.save_state"),
        patch("karakeep_sync.cli.KarakeepClient") as MockClient,
        patch("karakeep_sync.cli.commit_and_push"),
    ):
        mc = MockClient.return_value
        mc.get_all_bookmarks.return_value = [NEW_BM, company_bm]
        mc.get_bookmark_list_paths.return_value = {
            "abc123": ["미국 주식 사이트"],  # Company 아님 → 제외
            "comp1": ["Company"],            # Company → export
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["push"])

    assert result.exit_code == 0, result.output
    assert (config.repos["common"].path / "comp1.md").exists()
    assert not (config.repos["common"].path / "abc123.md").exists()


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


def test_init_aborts_when_vault_root_missing(tmp_path):
    config = make_config(tmp_path)
    config.vault_root = tmp_path / "does-not-exist"

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.subprocess.run") as mock_run,
    ):
        runner = CliRunner()
        # confirm 프롬프트에 "n" 입력 → 중단
        result = runner.invoke(cli, ["init"], input="n\n")

    assert result.exit_code == 1, result.output
    assert "존재하지 않습니다" in result.output
    mock_run.assert_not_called()


def test_init_warns_when_not_obsidian_vault(tmp_path):
    config = make_config(tmp_path)  # vault_root=tmp_path 존재하지만 .obsidian 없음

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.subprocess.run") as mock_run,
    ):
        runner = CliRunner()
        result = runner.invoke(cli, ["init"], input="n\n")

    assert result.exit_code == 1, result.output
    assert ".obsidian" in result.output
    mock_run.assert_not_called()


def test_init_proceeds_when_obsidian_vault_present(tmp_path):
    config = make_config(tmp_path)
    (tmp_path / ".obsidian").mkdir()  # 진짜 vault 마커

    with (
        patch("karakeep_sync.cli.load_config", return_value=config),
        patch("karakeep_sync.cli.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        runner = CliRunner()
        result = runner.invoke(cli, ["init"])

    assert result.exit_code == 0, result.output
    # 경고/중단 없이 검증을 통과해 cron 등록 단계(subprocess.run)까지 진행됨
    assert "존재하지 않습니다" not in result.output
    assert "init 중단" not in result.output
    assert mock_run.called


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


# --- .env 자동 로드 (#25) ---

def test_dotenv_loads_keys(tmp_path, monkeypatch):
    from karakeep_sync.cli import _load_dotenv_if_present
    env = tmp_path / ".env"
    env.write_text('GHES_PAT=abc123\nGHES_HOST="ghe.example"\nexport GHES_OWNER=acme\n')
    for k in ("GHES_PAT", "GHES_HOST", "GHES_OWNER"):
        monkeypatch.delenv(k, raising=False)

    _load_dotenv_if_present(env)

    import os
    assert os.environ["GHES_PAT"] == "abc123"
    assert os.environ["GHES_HOST"] == "ghe.example"   # 따옴표 제거
    assert os.environ["GHES_OWNER"] == "acme"          # `export ` 접두 허용


def test_dotenv_shell_value_wins(tmp_path, monkeypatch):
    """이미 셸/cron 이 export 한 값은 .env 가 덮어쓰지 않는다 (setdefault)."""
    from karakeep_sync.cli import _load_dotenv_if_present
    env = tmp_path / ".env"
    env.write_text("KARAKEEP_API_KEY=from-file\n")
    monkeypatch.setenv("KARAKEEP_API_KEY", "from-shell")

    _load_dotenv_if_present(env)

    import os
    assert os.environ["KARAKEEP_API_KEY"] == "from-shell"


def test_dotenv_missing_file_is_noop(tmp_path):
    from karakeep_sync.cli import _load_dotenv_if_present
    _load_dotenv_if_present(tmp_path / "does-not-exist.env")  # raises 없이 통과


def test_dotenv_ignores_comments_and_blanks(tmp_path, monkeypatch):
    from karakeep_sync.cli import _load_dotenv_if_present
    env = tmp_path / ".env"
    env.write_text("# comment\n\n   \nFOO=bar\n")
    monkeypatch.delenv("FOO", raising=False)

    _load_dotenv_if_present(env)

    import os
    assert os.environ["FOO"] == "bar"
