#!/usr/bin/env bash
# llm-wiki-deploy.sh — 프로젝트 SCHEMA.md 를 Obsidian vault 의 llm-wiki 로 배치 (멱등·모드 인지)
#
# 동료의 llm-wiki 스킬은 "SCHEMA.md overrides everything below" 로 프로젝트별
# SCHEMA.md 를 요구한다. 이 스크립트는 repo 의 SCHEMA.md 초안
#   docs/proposals/llm-wiki/SCHEMA.md
# 을 vault 의
#   <VAULT_ROOT>/30_Resources/llm-wiki/SCHEMA.md
# 로 복사한다. 디렉터리가 없으면 만든다. 내용이 같으면 아무것도 하지 않는다(멱등).
#
# 모드 경계 (#44): internal 모드는 vault 공용 영역이 pull-only 이고,
# 30_Resources/llm-wiki/ 는 vault-sync.sh 의 작성 화이트리스트 밖이라 한 줄도
# 쓰면 동기화가 깨진다. 따라서 internal 에서는 거부한다. 배치는 external/home 에서만.
#
# 경로/사용자명 하드코딩 안 함 (vault-sync.sh 와 동일 관례):
#   - Windows 사용자 : cmd.exe %USERPROFILE% 로 탐지
#   - 수동 지정      : VAULT_ROOT 환경변수로 override
#
# 사용법:
#   ./scripts/llm-wiki-deploy.sh           # 현재 모드에서 배치 (internal 은 거부)
#   ./scripts/llm-wiki-deploy.sh -h        # 도움말
#   VAULT_ROOT=/path ./scripts/llm-wiki-deploy.sh   # vault 경로 강제
#   MODE=external ./scripts/llm-wiki-deploy.sh       # 모드 강제 (테스트용)

set -euo pipefail

# ── 설정 ─────────────────────────────────────────────────────────────
MODE_FILE="${MODE_FILE:-$HOME/.dotfiles-setup-mode}"
WIKI_SUBPATH="${WIKI_SUBPATH:-30_Resources/llm-wiki}"   # underscore canonical (vs 서브모듈 30-Resource)

usage() { sed -n '2,30p' "$0"; exit 0; }
for arg in "$@"; do
  case "$arg" in -h|--help|help) usage ;; *) ;; esac
done

log()  { printf '  %s\n' "$*"; }
ok()   { printf '  ✅ %s\n' "$*"; }
die()  { printf '  ❌ %s\n' "$*" >&2; exit 1; }

# ── 0. repo 내 SCHEMA.md 원본 위치 ───────────────────────────────────
REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null)" \
  || die "git repo 안에서 실행하세요"
SRC="$REPO_ROOT/docs/proposals/llm-wiki/SCHEMA.md"
[ -f "$SRC" ] || die "원본 SCHEMA.md 없음: $SRC"

# ── 1. 모드 ──────────────────────────────────────────────────────────
MODE="${MODE:-}"
if [ -z "$MODE" ]; then
  [ -f "$MODE_FILE" ] || die "모드 파일 없음: $MODE_FILE (internal|external|home)"
  MODE="$(tr -d '[:space:]' < "$MODE_FILE")"
fi
case "$MODE" in internal|external|home) ;; *) die "잘못된 모드: '$MODE'" ;; esac
log "모드: $MODE"

if [ "$MODE" = "internal" ]; then
  die "internal 모드에서는 배치하지 않습니다 (#44 쓰기 경계).
       30_Resources/llm-wiki/ 는 vault-sync 작성 화이트리스트 밖 → 쓰면 동기화가 깨집니다.
       external/home PC 에서 실행하세요."
fi

# ── 2. vault 경로 탐지 (vault-sync.sh 와 동일 방식) ──────────────────
if [ -z "${VAULT_ROOT:-}" ]; then
  WINHOME="$(wslpath "$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')" 2>/dev/null || true)"
  [ -n "$WINHOME" ] || die "Windows 홈 탐지 실패 — VAULT_ROOT 로 직접 지정하세요"
  VAULT_ROOT="$WINHOME/Documents/ObsidianVault-PARA"
fi
[ -d "$VAULT_ROOT" ] || die "vault 없음: $VAULT_ROOT (vault-sync.sh 를 먼저 실행했는지 확인)"
log "vault: $VAULT_ROOT"

# ── 3. 배치 (멱등) ───────────────────────────────────────────────────
# 정확한 대소문자로 생성한다. /mnt/c 는 case-insensitive 지만 git/WSL 은
# case-sensitive 라 잘못된 표기는 phantom 디렉터리/case-only rename 을 만든다.
DEST_DIR="$VAULT_ROOT/$WIKI_SUBPATH"
DEST="$DEST_DIR/SCHEMA.md"

if [ -f "$DEST" ] && cmp -s "$SRC" "$DEST"; then
  ok "이미 최신 — 변경 없음 (멱등): $DEST"
  exit 0
fi

mkdir -p "$DEST_DIR"
cp "$SRC" "$DEST"
ok "배치 완료: $DEST"
log "다음: stub(index.md·log.md·raw-sources/index.md) 생성 + 첫 ingest 는 #42 참조."
