#!/usr/bin/env bash
# karakeep-sync 셋업 점검 — 한 번 실행으로 "어디가 비었는지"를 로그로 보여준다.
#
# 점검 순서:
#   1) config.yaml 로드 (+ .env 의 ${...} 치환 확인)
#   2) Karakeep 연결/인증 (공유 인스턴스든 localhost 든 config 의 url)
#   3) 리스트 멤버십 — repo 별 include/exclude 라우팅으로 실제 export 대상 수
#   4) git remote 접근 (ls-remote)
#   5) 로컬 clone 상태 (init 됐는지, md 몇 개인지)
#
# 모든 점검을 끝까지 돌리고(중간에 안 멈춤) 마지막에 FAIL/WARN 요약 + exit code.
# SSOT: docs/pc-environment.md
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNC_DIR="$REPO_ROOT/sync"
PY="$SYNC_DIR/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3 || true)"
[ -n "$PY" ] || { printf '\033[1;31m✗\033[0m python 을 찾을 수 없습니다 (venv 설치 필요)\n'; exit 1; }

# .env 주입 — config 의 ${...} 치환에 필요. cron 과 동일한 방식.
if [ -f "$REPO_ROOT/.env" ]; then
  set -a; . "$REPO_ROOT/.env"; set +a
else
  printf '\033[1;31m✗\033[0m .env 없음: %s — 먼저 채우세요\n' "$REPO_ROOT/.env"; exit 1
fi

cd "$SYNC_DIR"
"$PY" - <<'PY'
import subprocess, sys

G="\033[1;32m"; R="\033[1;31m"; Y="\033[1;33m"; B="\033[1;34m"; X="\033[0m"
fails = warns = 0
def head(m): print(f"\n{B}▶ {m}{X}")
def ok(m):   print(f"  {G}✓{X} {m}")
def warn(m):
    global warns; warns += 1; print(f"  {Y}!{X} {m}")
def bad(m):
    global fails; fails += 1; print(f"  {R}✗{X} {m}")

# ---------- 1. config ----------
head("1. config.yaml 로드 (+ .env 치환)")
try:
    from karakeep_sync.config import load_config
    cfg = load_config()
except Exception as e:
    bad(f"config 로드 실패: {e}")
    print(f"\n{R}── 점검 중단: config 부터 고치세요 ──{X}")
    print("   대개 .env 의 ${...} 변수(KARAKEEP_URL / GHES_OWNER 등)가 비었을 때입니다.")
    sys.exit(1)
ok(f"mode internal={cfg.is_work}")
ok(f"karakeep.url = {cfg.karakeep_url}")
ok(f"vault_root   = {cfg.vault_root} (exists={cfg.vault_root.exists()})")
if not cfg.vault_root.exists():
    warn("vault_root 경로가 없습니다 — Obsidian vault 경로를 확인하세요")
for n, r in cfg.repos.items():
    ok(f"repo[{n}] push={r.push} pull={r.pull} include={r.include_lists or '-'} exclude={r.exclude_lists or '-'}")

# ---------- 1b. company remote SSOT drift (issue #38) ----------
# config.yaml(company) 과 vault-sync.sh §8 은 둘 다 80-Company/Bookmarks 의 GHES remote 를
# 설정한다. 두 URL 이 다르면(특히 owner/host) 두 엔진이 매 실행 git remote set-url 로 번갈아
# 덮어써 churn 이 난다. vault-sync.sh 는 GHES_HOST/GHES_OWNER 컴포넌트로 조립하므로, config 의
# company remote 도 같은 host/owner 로 정규화되는지 검증한다(리터럴 박힘 → drift 조기 차단).
import os
from urllib.parse import urlparse
head("1b. company remote SSOT (config.yaml ↔ vault-sync.sh, #38)")
comp = cfg.repos.get("company")
if comp is None:
    ok("company repo 비활성 (이 모드/PC) — drift 점검 불필요")
else:
    env_host = os.environ.get("GHES_HOST", "")
    env_owner = os.environ.get("GHES_OWNER", "")
    u = urlparse(comp.remote)
    r_host = u.hostname or ""
    r_owner = u.path.lstrip("/").split("/")[0] if u.path else ""
    if env_host and r_host != env_host:
        bad(f"company remote host '{r_host}' ≠ GHES_HOST '{env_host}' — vault-sync.sh 와 drift. config.yaml 에서 ${{GHES_HOST}} 를 쓰세요 (#38)")
    elif env_owner and r_owner != env_owner:
        bad(f"company remote owner '{r_owner}' ≠ GHES_OWNER '{env_owner}' — vault-sync.sh 와 drift. config.yaml 에서 ${{GHES_OWNER}} 를 쓰세요 (#38)")
    else:
        ok(f"company remote 가 GHES_HOST/GHES_OWNER 와 일치 ({r_host}/{r_owner}) — churn 없음")

# ---------- 2. Karakeep ----------
head("2. Karakeep 연결/인증")
client = bms = None
try:
    from karakeep_sync.karakeep import KarakeepClient, bookmark_in_any_list
    client = KarakeepClient(cfg.karakeep_url, cfg.karakeep_api_key)
    bms = client.get_all_bookmarks()
    ok(f"인증 OK — 전체 북마크 {len(bms)}개")
except Exception as e:
    bad(f"Karakeep 접근 실패: {e}")
    warn("KARAKEEP_URL / KARAKEEP_API_KEY 를 확인하세요 (사내 TLS MITM 이면 SSL_CERT_FILE 필요)")

# ---------- 3. 리스트 멤버십 / export 대상 ----------
if bms is not None:
    head("3. 리스트 멤버십 / repo 별 push 대상 수")
    try:
        list_paths = client.get_bookmark_list_paths()
    except Exception as e:
        bad(f"리스트 조회 실패: {e}"); list_paths = {}
    from collections import Counter
    top = Counter()
    for b in bms:
        for p in list_paths.get(b.id, []):
            top[p.split("/")[0]] += 1
    if top:
        ok("top-level 리스트별 북마크 수: " + ", ".join(f"{k}={v}" for k, v in top.most_common()))
    else:
        warn("어떤 북마크도 리스트에 속해있지 않습니다 (include_lists 매칭 0)")
    for n, r in cfg.repos.items():
        if not r.push:
            ok(f"repo[{n}] push=False (이 PC 는 export 안 함) — skip")
            continue
        cand = 0
        for b in bms:
            lists = list_paths.get(b.id, [])
            if r.include_lists and not bookmark_in_any_list(lists, r.include_lists):
                continue
            if bookmark_in_any_list(lists, r.exclude_lists):
                continue
            cand += 1
        if r.include_lists and cand == 0:
            bad(f"repo[{n}] push 대상 0개 — include_lists={r.include_lists} 에 속한 북마크가 없음")
            warn(f"   → Karakeep 웹에서 북마크를 '{r.include_lists[0]}' 리스트에 넣으세요 (안 그러면 빈 repo)")
        else:
            ok(f"repo[{n}] push 대상 {cand}개")

# ---------- 4. git remote ----------
head("4. git remote 접근 (ls-remote)")
for n, r in cfg.repos.items():
    p = subprocess.run(["git", "ls-remote", r.remote], capture_output=True, text=True)
    if p.returncode == 0:
        nref = len([ln for ln in p.stdout.splitlines() if ln.strip()])
        ok(f"repo[{n}] 접근 OK" + (" (빈 repo — 첫 push 전)" if nref == 0 else f" (ref {nref}개)"))
    else:
        last = (p.stderr.strip().splitlines() or ["unknown"])[-1]
        bad(f"repo[{n}] 접근 실패: {last}")

# ---------- 5. clone 상태 ----------
head("5. 로컬 clone 상태")
for n, r in cfg.repos.items():
    if (r.path / ".git").is_dir():
        nmd = len(list(r.path.glob("*.md")))
        ok(f"repo[{n}] clone 됨: {r.path} (md {nmd}개)")
    elif r.path.exists():
        warn(f"repo[{n}] 경로는 있으나 git repo 가 아님: {r.path}")
    else:
        warn(f"repo[{n}] 아직 clone 안 됨: {r.path} → 'karakeep-sync init' 필요")

# ---------- 요약 ----------
print()
if fails:
    print(f"{R}━━ 결과: {fails} FAIL, {warns} WARN — 위 ✗ 항목을 고치세요 ━━{X}")
    sys.exit(1)
print(f"{G}━━ 결과: 통과 ({warns} WARN) — push 준비 완료 ━━{X}")
PY
