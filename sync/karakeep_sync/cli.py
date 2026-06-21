from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import click

from karakeep_sync.config import load_config, RepoConfig
from karakeep_sync.state import load_state, save_state, BookmarkState
from karakeep_sync.karakeep import KarakeepClient, Bookmark, bookmark_in_any_list
from karakeep_sync.markdown import bookmark_to_md, bookmark_filename, md_to_bookmark
from karakeep_sync.git_ops import pull, changed_files_after_pull, commit_and_push
from karakeep_sync import chrome_import

# repo-root/.env — check.sh(set -a; . $REPO_ROOT/.env) 및 cron 주입이 쓰는 위치와 동일.
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


def _load_dotenv_if_present(env_file: Path = ENV_PATH) -> None:
    """repo-root/.env 를 자동 주입한다 — 대화형 실행 시 source 누락을 막는다(#25).

    check.sh·cron 은 .env 를 직접 source 하지만 CLI 직접 실행은 그러지 않아,
    셸에 export 안 된 상태로 ``karakeep-sync push`` 를 돌리면 config 의 ${VAR}
    치환이 ValueError 로 깨졌다. 이미 셸/cron 이 설정한 값은 덮어쓰지 않는다
    (셸 > .env 우선순위 — setdefault 로 보장).
    """
    if not env_file.exists():
        return
    with open(env_file) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            if key.startswith("export "):  # `export FOO=bar` 형태도 허용
                key = key[len("export "):].strip()
            os.environ.setdefault(key, val.strip().strip('"').strip("'"))


@click.group()
def cli() -> None:
    # 모든 서브커맨드 진입 전 .env 주입 — push/pull/auto/status/init/import-chrome 공통.
    _load_dotenv_if_present()


def _bookmark_needs_push(
    bm: Bookmark, bm_state: BookmarkState | None, *, force: bool = False
) -> bool:
    """state 기준으로 이 북마크가 아직 push 대상인지 판단한다 (리스트 라우팅은 별도).

    - pull 로 들어온 북마크(imported)는 되돌려 export 하지 않는다.
    - 마지막 export 이후 타임스탬프 변화가 없으면 skip (--force 면 무시).
    """
    if bm_state and bm_state.imported:
        return False
    if not force and bm_state and bm_state.updated >= bm.updated:
        return False
    return True


def _repo_accepts_bookmark(repo: RepoConfig, bm_lists: list[str]) -> bool:
    """리스트 라우팅(include/exclude)상 이 repo 가 이 북마크를 받는지 판단한다.

    push 와 status 가 공유하는 단일 판정 — 과거 status 는 이 필터를 적용하지 않아,
    어느 push repo 로도 라우팅되지 않는 북마크(예: external PC 의 Company 북마크)를
    영원히 'Pending push' 로 잘못 셌다.
    """
    if repo.include_lists and not bookmark_in_any_list(bm_lists, repo.include_lists):
        return False
    if bookmark_in_any_list(bm_lists, repo.exclude_lists):
        return False
    return True


@cli.command(name="import-chrome")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--commit", is_flag=True, help="실제 등록 (기본은 dry-run)")
@click.option("--no-folder-tags", is_flag=True, help="폴더→태그 매핑 끔")
@click.option("--exclude-folder", "exclude_folders", multiple=True,
              help="이 폴더명을 경로에 포함한 북마크는 제외 (반복 가능, 대소문자 무시)")
@click.option("--export-excluded", type=click.Path(path_type=Path),
              help="제외된 북마크를 JSON 으로 따로 저장 (사내 repo 처리용)")
def import_chrome(file: Path, commit: bool, no_folder_tags: bool,
                  exclude_folders: tuple[str, ...], export_excluded: Path | None) -> None:
    """Chrome 북마크(HTML 내보내기/원본 JSON) → Karakeep import.

    폴더→태그 매핑 + 기존 URL dedup 후 멱등 업서트. 본문 크롤·AI 태깅은 cron 이 처리.
    """
    config = load_config()
    client = KarakeepClient(config.karakeep_url, config.karakeep_api_key)

    entries = chrome_import.parse_chrome_bookmarks(file.read_text(encoding="utf-8", errors="replace"))
    click.echo(f"[parse] {len(entries)} 개 URL")

    kept, excluded = chrome_import.split_excluded(entries, exclude_folders)
    if exclude_folders:
        click.echo(f"[exclude] {len(excluded)} 개 제외 ({', '.join(exclude_folders)})")
        if export_excluded:
            export_excluded.write_text(chrome_import.excluded_to_json(excluded), encoding="utf-8")
            click.echo(f"[exclude] 제외분 저장 → {export_excluded}")

    def _progress(i: int, n: int) -> None:
        if i % 25 == 0:
            click.echo(f"  …{i}/{n}")

    result = chrome_import.import_entries(
        client, kept, folder_tags=not no_folder_tags,
        dry_run=not commit, progress=_progress,
    )
    click.echo(f"[dedup] 대상 {result.todo} (신규 {result.to_create} / 기존 {result.todo - result.to_create})")
    if not commit:
        click.echo("[dry-run] 실제 등록 안 함. 확인되면 --commit 을 붙여 다시 실행.")
    else:
        click.echo(f"[done] 신규 생성 {result.created} · 태그 부착 {result.tagged} · 실패 {result.failed}.")


@cli.command()
@click.option("--force", is_flag=True,
              help="타임스탬프 변화가 없어도 전체 재내보내기 (리스트 멤버십 백필용)")
def push(force: bool) -> None:
    """Karakeep → Markdown → git push"""
    config = load_config()
    state = load_state()
    client = KarakeepClient(config.karakeep_url, config.karakeep_api_key)
    bookmarks = client.get_all_bookmarks()
    # 북마크 id → 소속 리스트 full path. frontmatter 의 lists 필드로 단방향 반영한다.
    list_paths = client.get_bookmark_list_paths()

    for repo_name, repo in config.repos.items():
        if not repo.push:
            continue

        changed: list[Path] = []
        for bm in bookmarks:
            if not _bookmark_needs_push(bm, state.get(bm.id), force=force):
                continue

            bm.lists = list_paths.get(bm.id, [])
            # repo 별 리스트 라우팅 (include_lists / exclude_lists). status 와 동일 판정.
            if not _repo_accepts_bookmark(repo, bm.lists):
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
    list_paths = client.get_bookmark_list_paths()

    push_repos = [repo for repo in config.repos.values() if repo.push]
    # push 와 동일 판정: state 상 변경분이면서, 적어도 한 push repo 로 라우팅되는 것만 pending.
    # 어느 repo 로도 안 가는 북마크(예: external PC 의 Company)는 영구 pending 오탐을 막는다.
    pending = 0
    for bm in bookmarks:
        if not _bookmark_needs_push(bm, state.get(bm.id)):
            continue
        bm_lists = list_paths.get(bm.id, [])
        if any(_repo_accepts_bookmark(repo, bm_lists) for repo in push_repos):
            pending += 1
    click.echo(f"Pending push: {pending} bookmark(s)")


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
    env_path = ENV_PATH
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
