from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import click

from karakeep_sync.config import load_config
from karakeep_sync.state import load_state, save_state, BookmarkState
from karakeep_sync.karakeep import KarakeepClient
from karakeep_sync.markdown import bookmark_to_md, bookmark_filename, md_to_bookmark
from karakeep_sync.git_ops import pull, changed_files_after_pull, commit_and_push


@click.group()
def cli() -> None:
    pass


@cli.command()
def push() -> None:
    """Karakeep → Markdown → git push"""
    config = load_config()
    state = load_state()
    client = KarakeepClient(config.karakeep_url, config.karakeep_api_key)
    bookmarks = client.get_all_bookmarks()

    for repo_name, repo in config.repos.items():
        if not repo.push:
            continue

        changed: list[Path] = []
        for bm in bookmarks:
            bm_state = state.get(bm.id)
            if bm_state and bm_state.imported:
                continue
            if bm_state and bm_state.updated >= bm.updated:
                continue

            md_path = repo.path / bookmark_filename(bm)
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(bookmark_to_md(bm))
            changed.append(md_path)
            state[bm.id] = BookmarkState(updated=bm.updated, repo=repo_name, imported=False)

        if changed:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            commit_and_push(repo.path, changed, f"sync: push {len(changed)} bookmarks [{now}]")

    save_state(state)
    click.echo("Push complete.")


@cli.command(name="pull")
def pull_cmd() -> None:
    """git pull → Markdown → Karakeep import"""
    config = load_config()
    state = load_state()
    client = KarakeepClient(config.karakeep_url, config.karakeep_api_key)
    existing = {bm.url: bm for bm in client.get_all_bookmarks()}

    for repo_name, repo in config.repos.items():
        if not repo.pull:
            continue
        pull(repo.path)
        changed_files = changed_files_after_pull(repo.path)

        for md_path in changed_files:
            if md_path.suffix != ".md":
                continue
            try:
                bm = md_to_bookmark(md_path.read_text())
            except (ValueError, KeyError):
                continue

            existing_bm = existing.get(bm.url)
            if existing_bm is None:
                created = client.create_bookmark(bm)
                state[created.id] = BookmarkState(
                    updated=bm.updated, repo=repo_name, imported=True
                )
            elif bm.updated > existing_bm.updated:
                client.update_bookmark(existing_bm.id, bm)
                state[existing_bm.id] = BookmarkState(
                    updated=bm.updated, repo=repo_name, imported=True
                )

    save_state(state)
    click.echo("Pull complete.")


@cli.command()
@click.pass_context
def auto(ctx: click.Context) -> None:
    """git pull → Karakeep import → Karakeep export → git push (cron용)"""
    ctx.invoke(pull_cmd)
    ctx.invoke(push)


@cli.command()
def status() -> None:
    """동기화되지 않은 북마크 수 출력"""
    config = load_config()
    state = load_state()
    client = KarakeepClient(config.karakeep_url, config.karakeep_api_key)
    bookmarks = client.get_all_bookmarks()

    pending = [
        bm for bm in bookmarks
        if bm.id not in state or state[bm.id].updated < bm.updated
    ]
    click.echo(f"Pending push: {len(pending)} bookmark(s)")


@cli.command()
def init() -> None:
    """git clone + cron 등록"""
    config = load_config()

    for repo_name, repo in config.repos.items():
        if repo.path.exists():
            click.echo(f"[{repo_name}] Already exists: {repo.path}")
            continue
        click.echo(f"[{repo_name}] Cloning {repo.remote} → {repo.path}")
        repo.path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", repo.remote, str(repo.path)], check=True)
        click.echo(f"[{repo_name}] Done.")

    # cron 등록
    sync_bin = Path(__file__).parent.parent / ".venv" / "bin" / "karakeep-sync"
    log_path = config.log_dir / "cron.log"
    config.log_dir.mkdir(parents=True, exist_ok=True)
    cron_line = f"*/30 * * * * {sync_bin} auto >> {log_path} 2>&1"
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""
    if cron_line in existing:
        click.echo("Cron already registered.")
    else:
        new_crontab = existing.rstrip("\n") + f"\n{cron_line}\n"
        subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)
        click.echo(f"Cron registered: {cron_line}")
