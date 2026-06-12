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
