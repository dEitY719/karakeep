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
        if (bm.id not in state or state[bm.id].updated < bm.updated)
        and not (bm.id in state and state[bm.id].imported)
    ]
    click.echo(f"Pending push: {len(pending)} bookmark(s)")


def _looks_like_obsidian_vault(path: Path) -> bool:
    """path 자신부터 home 까지 거슬러 올라가며 .obsidian/ 마커를 찾는다."""
    for parent in [path, *path.parents]:
        if (parent / ".obsidian").is_dir():
            return True
        if parent == Path.home():
            break
    return False


def _validate_vault_root(vault_root: Path) -> None:
    """vault_root 가 틀린 경로일 때 조용히 빈 폴더를 만들지 않도록 사용자에게 확인."""
    if not vault_root.exists():
        click.echo(f"⚠️  vault_root 가 존재하지 않습니다: {vault_root}")
        click.echo("    config.yaml 의 vault_root 가 이 PC의 실제 Obsidian vault 경로인지 확인하세요.")
        click.echo("    (Obsidian vault 는 보통 .obsidian/ 폴더를 포함합니다.)")
        if not click.confirm("    이 경로를 새로 만들고 계속할까요?", default=False):
            click.echo("init 중단. config.yaml 의 vault_root 를 수정한 뒤 다시 실행하세요.")
            raise SystemExit(1)
    elif not _looks_like_obsidian_vault(vault_root):
        click.echo(f"⚠️  vault_root 에서 Obsidian vault(.obsidian/)가 보이지 않습니다: {vault_root}")
        click.echo("    경로가 틀리면 북마크가 엉뚱한 폴더에 쌓입니다. 경로를 다시 확인하세요.")
        if not click.confirm("    이대로 계속할까요?", default=False):
            click.echo("init 중단. config.yaml 의 vault_root 를 확인하세요.")
            raise SystemExit(1)


@cli.command()
def init() -> None:
    """git clone + cron 등록"""
    config = load_config()

    _validate_vault_root(config.vault_root)

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
    env_path = Path(__file__).parent.parent.parent / ".env"
    log_path = config.log_dir / "cron.log"
    config.log_dir.mkdir(parents=True, exist_ok=True)
    # cron 은 로그인 셸이 아니라 API key/PAT 가 env 에 없다. .env 를 직접 주입하지
    # 않으면 auto 가 401 로 실패한다.
    cron_cmd = f"set -a; . {env_path}; set +a; {sync_bin} auto"
    cron_line = f"*/30 * * * * {cron_cmd} >> {log_path} 2>&1"
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""
    # 기존 karakeep-sync auto 라인(구버전 포함)을 제거하고 새 라인으로 교체한다.
    kept = [ln for ln in existing.splitlines() if f"{sync_bin} auto" not in ln]
    if cron_line in existing:
        click.echo("Cron already registered.")
    else:
        new_crontab = "\n".join([*kept, cron_line]).strip("\n") + "\n"
        subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)
        click.echo(f"Cron registered: {cron_line}")
