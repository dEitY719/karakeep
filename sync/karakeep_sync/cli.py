from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
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
