#!/usr/bin/env bash
# vault-sync.sh — ObsidianVault-PARA git 동기화 (모드 인지 · 경로 자동탐지 · 멱등)
#
# 원칙 (docs/pc-environment.md SSOT):
#   internal : GitHub(common)  = PULL ONLY  (push 절대 금지)
#              GHES(company)    = read/write (80-Company 만)
#   external : common read/write · company 비활성
#   home     : common read/write · company 비활성
#   → bookmarks 와 동일 원칙: internal 은 upstream 에서 pull 만.
#
# 경로/사용자명 하드코딩 안 함:
#   - Windows 사용자  : cmd.exe %USERPROFILE% 로 탐지 (bwyoon / byoungwoo.yoon / msi-labtop 자동)
#   - Linux HOME      : $HOME 사용
#   - 수동 지정       : VAULT_ROOT 환경변수로 override 가능
#
# 시크릿은 코드/리포에 두지 않고 untracked 파일에서 로드:
#   기본: $HOME/.config/obsidian-para/secrets.env   (없으면 템플릿 생성 후 종료)
#
# 사용법:
#   ./vault-sync.sh            # 현재 모드대로 clone(최초) 또는 pull(이후)
#   ./vault-sync.sh -h         # 도움말
#   MODE=internal ./vault-sync.sh     # 모드 강제 (테스트용)

set -euo pipefail

# ── 설정 (필요시 환경변수로 override) ────────────────────────────────
GH_OWNER="${GH_OWNER:-dEitY719}"
PARA_REPO="${PARA_REPO:-obsidian-para}"
COMMON_REPO="${COMMON_REPO:-bookmarks-common}"
SUBMODULE_PATH="${SUBMODULE_PATH:-30-Resource/Bookmarks}"
COMPANY_BM_PATH="${COMPANY_BM_PATH:-80-Company/Bookmarks}"
MODE_FILE="${MODE_FILE:-$HOME/.dotfiles-setup-mode}"
SECRETS="${VAULT_SECRETS:-$HOME/.config/obsidian-para/secrets.env}"
NO_PUSH_SENTINEL="no-push://internal-is-pull-only"   # internal 에서 push 차단용 더미

usage() { sed -n '2,30p' "$0"; exit 0; }
[ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] && usage

log()  { printf '  %s\n' "$*"; }
ok()   { printf '  ✅ %s\n' "$*"; }
warn() { printf '  ⚠️  %s\n' "$*" >&2; }
die()  { printf '  ❌ %s\n' "$*" >&2; exit 1; }
redact() { sed -E 's#(://[^:@/]+:)[^@/]+@#\1***@#g; s/(gh[oprs]_|github_pat_)[A-Za-z0-9_]+/\1***/g'; }

# 연결 리셋(사내 방화벽) 대비 재시도 래퍼
git_retry() {
  local n=0 max=3
  until git "$@"; do
    n=$((n + 1)); [ "$n" -ge "$max" ] && return 1
    warn "git $1 실패 — 재시도 $n/$max (연결 리셋?)"; sleep 2
  done
}

# ── 0. 모드 ──────────────────────────────────────────────────────────
MODE="${MODE:-}"
if [ -z "$MODE" ]; then
  [ -f "$MODE_FILE" ] || die "모드 파일 없음: $MODE_FILE (internal|external|home 중 하나를 적어주세요)"
  MODE="$(tr -d '[:space:]' < "$MODE_FILE")"
fi
case "$MODE" in internal|external|home) ;; *) die "잘못된 모드: '$MODE'" ;; esac
log "모드: $MODE"

# ── 1. 시크릿 로드 (없으면 템플릿 생성) ──────────────────────────────
if [ ! -f "$SECRETS" ]; then
  mkdir -p "$(dirname "$SECRETS")"; chmod 700 "$(dirname "$SECRETS")"
  cat > "$SECRETS" <<'TPL'
# obsidian-para 동기화 시크릿 (이 파일은 git 에 절대 올리지 마세요)
# GitHub 토큰은 각 repo 전용 fine-grained PAT (Contents: Read 또는 Read/Write) 권장.

OBSIDIAN_PARA_PAT=""      # obsidian-para repo 용 PAT (internal=Read 면 충분, external/home=Read/Write)
BOOKMARKS_COMMON_PAT=""   # bookmarks-common (submodule) 용 PAT

# ── internal 모드에서만 필요 ───────────────────────────────────────
# 회사 GHES bookmarks-company remote (토큰 포함 전체 URL 권장; 사내 비밀이므로 여기에만)
BOOKMARKS_COMPANY_REMOTE=""   # 예: https://<user>:<ghes-pat>@<ghes-host>/<org>/bookmarks-company.git
CORP_CA=""                    # 사내 루트 CA pem 경로 (TLS 재서명 환경; 없으면 비움)
TPL
  chmod 600 "$SECRETS"
  die "시크릿 템플릿을 생성했습니다 → $SECRETS
       값을 채운 뒤 다시 실행하세요."
fi
set -a
# shellcheck disable=SC1090
. "$SECRETS"
set +a
[ -n "${OBSIDIAN_PARA_PAT:-}" ]    || die "$SECRETS 에 OBSIDIAN_PARA_PAT 미설정"
[ -n "${BOOKMARKS_COMMON_PAT:-}" ] || die "$SECRETS 에 BOOKMARKS_COMMON_PAT 미설정"

# ── 2. Windows vault 경로 탐지 ───────────────────────────────────────
if [ -z "${VAULT_ROOT:-}" ]; then
  WINHOME="$(wslpath "$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')" 2>/dev/null || true)"
  [ -n "$WINHOME" ] || die "Windows 홈 탐지 실패 — VAULT_ROOT 로 직접 지정하세요"
  VAULT_ROOT="$WINHOME/Documents/ObsidianVault-PARA"
fi
log "vault: $VAULT_ROOT"

# ── 3. 사내 CA (있으면 git 에 등록) ──────────────────────────────────
if [ -n "${CORP_CA:-}" ] && [ -f "$CORP_CA" ]; then
  git config --global http.sslCAInfo "$CORP_CA"
  ok "사내 CA 등록: $CORP_CA"
fi

PARA_URL="https://${GH_OWNER}:${OBSIDIAN_PARA_PAT}@github.com/${GH_OWNER}/${PARA_REPO}.git"
SUB_URL="https://${GH_OWNER}:${BOOKMARKS_COMMON_PAT}@github.com/${GH_OWNER}/${COMMON_REPO}.git"

# ── 4. obsidian-para clone(최초) 또는 pull(이후) ─────────────────────
if [ -d "$VAULT_ROOT/.git" ]; then
  log "기존 vault 발견 → 원격 URL 갱신 후 pull"
  git -C "$VAULT_ROOT" remote set-url origin "$PARA_URL"
  git_retry -C "$VAULT_ROOT" pull --ff-only origin main || die "pull 실패"
else
  log "최초 clone"
  mkdir -p "$(dirname "$VAULT_ROOT")"
  git_retry clone "$PARA_URL" "$VAULT_ROOT" || die "clone 실패"
  git -C "$VAULT_ROOT" checkout main 2>/dev/null || true
fi
ok "obsidian-para 동기화 완료 ($(git -C "$VAULT_ROOT" rev-parse --short HEAD))"

# ── 4b. 사내 경계 가드레일 (§4.3 능동 차단) ──────────────────────────
# 공용 obsidian-para(GitHub)는 80-Company/ 를 .gitignore 로 제외해야 한다. 만약 그 경로가
# 공용 repo 에 '추적(tracked)'되고 있으면 다음 push 때 사내 콘텐츠가 공개 GitHub 로 새어나간다.
# 구조적 방어(.gitignore)에만 의존하지 않고, push 정책을 적용하기 전에 능동적으로 거부한다.
COMPANY_DIR="${COMPANY_DIR:-80-Company}"
tracked_company="$(git -C "$VAULT_ROOT" ls-files -- "$COMPANY_DIR" 2>/dev/null || true)"
if [ -n "$tracked_company" ]; then
  warn "공용 repo 에 사내 경로($COMPANY_DIR)가 추적되고 있습니다 — 사내 콘텐츠 유출 위험:"
  printf '%s\n' "$tracked_company" | sed 's/^/      /' >&2
  die "사내 경계 위반(§4.3). 공용 obsidian-para 의 .gitignore 에 '$COMPANY_DIR/' 를 추가하고
       'git -C \"$VAULT_ROOT\" rm -r --cached $COMPANY_DIR' 로 추적을 해제한 뒤 다시 실행하세요."
fi
ok "사내 경계 OK ($COMPANY_DIR 는 공용 repo 에 미추적)"

# ── 5. 모드별 push 정책 ──────────────────────────────────────────────
if [ "$MODE" = "internal" ]; then
  git -C "$VAULT_ROOT" remote set-url --push origin "$NO_PUSH_SENTINEL"
  ok "internal → obsidian-para PUSH 차단 (pull-only)"
else
  git -C "$VAULT_ROOT" remote set-url --push origin "$PARA_URL"
  ok "$MODE → obsidian-para push 허용"
fi

# ── 6. Bookmarks 서브모듈 (토큰은 로컬 .git/config 에만, .gitmodules 는 clean) ──
git -C "$VAULT_ROOT" submodule init "$SUBMODULE_PATH" 2>/dev/null || true
git -C "$VAULT_ROOT" config "submodule.${SUBMODULE_PATH}.url" "$SUB_URL"
git_retry -C "$VAULT_ROOT" submodule update "$SUBMODULE_PATH" \
  || warn "submodule update 실패 (karakeep-sync 가 별도 관리 중이면 무시 가능)"
if [ -d "$VAULT_ROOT/$SUBMODULE_PATH/.git" ] || [ -f "$VAULT_ROOT/$SUBMODULE_PATH/.git" ]; then
  if [ "$MODE" = "internal" ]; then
    git -C "$VAULT_ROOT/$SUBMODULE_PATH" remote set-url --push origin "$NO_PUSH_SENTINEL" 2>/dev/null || true
    ok "internal → Bookmarks PUSH 차단 (pull-only)"
  fi
fi

# ── 7. internal 전용: 80-Company/Bookmarks (GHES, read/write) ────────
if [ "$MODE" = "internal" ]; then
  if [ -z "${BOOKMARKS_COMPANY_REMOTE:-}" ]; then
    warn "BOOKMARKS_COMPANY_REMOTE 미설정 → 80-Company 북마크 건너뜀 ($SECRETS 에 추가하세요)"
  else
    CDIR="$VAULT_ROOT/$COMPANY_BM_PATH"
    if [ -d "$CDIR/.git" ]; then
      git -C "$CDIR" remote set-url origin "$BOOKMARKS_COMPANY_REMOTE"
      git_retry -C "$CDIR" pull --ff-only || warn "company 북마크 pull 실패"
    else
      mkdir -p "$(dirname "$CDIR")"
      git_retry clone "$BOOKMARKS_COMPANY_REMOTE" "$CDIR" || warn "company 북마크 clone 실패"
    fi
    ok "80-Company/Bookmarks (GHES) read/write 준비됨"
  fi
fi

printf '\n'
ok "완료 — 모드=$MODE, vault=$VAULT_ROOT"
log "원격/푸시 상태:"
git -C "$VAULT_ROOT" remote -v | redact | sed 's/^/    /'
