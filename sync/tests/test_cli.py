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
