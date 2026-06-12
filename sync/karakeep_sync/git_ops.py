from __future__ import annotations
import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True
        )
    except OSError as exc:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {cwd}:\n{exc}"
        ) from exc
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
    run_git(["push", "origin", "HEAD"], cwd=path)
