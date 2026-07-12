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
# dotfiles 의 공용 PC 명칭 'public' 은 home 과 동일 동작 → home 으로 정규화 (home=public).
[ "$MODE" = public ] && MODE=home
case "$MODE" in internal|external|home) ;; *) die "잘못된 모드: '$MODE' (internal|external|home, 또는 home 별칭 public)" ;; esac
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

# ── 3. SCHEMA.md 배치 (멱등) ─────────────────────────────────────────
# 정확한 대소문자로 생성한다. /mnt/c 는 case-insensitive 지만 git/WSL 은
# case-sensitive 라 잘못된 표기는 phantom 디렉터리/case-only rename 을 만든다.
DEST_DIR="$VAULT_ROOT/$WIKI_SUBPATH"
DEST="$DEST_DIR/SCHEMA.md"

mkdir -p "$DEST_DIR"
if [ -f "$DEST" ] && cmp -s "$SRC" "$DEST"; then
  ok "SCHEMA.md 이미 최신 — 변경 없음 (멱등)"
else
  cp "$SRC" "$DEST"
  ok "SCHEMA.md 배치 완료: $DEST"
fi

# ── 4. stub 스캐폴딩 (없을 때만 — 누적 콘텐츠를 절대 덮어쓰지 않음) ──
# 스킬은 위키가 없으면 SCHEMA.md + index.md + log.md + raw-sources/index.md
# 4개 stub 을 첫 ingest 전에 만들라고 요구한다(SKILL.md L30). SCHEMA.md 는 위에서
# 처리했고, 여기서 나머지 3개를 생성한다. 이 파일들은 ingest 가 내용을 누적하므로
# 이미 있으면 손대지 않는다(멱등·clobber 금지).
TODAY="$(date +%F)"   # KST 로컬

scaffold() {  # <relative-path> <heredoc-content-on-stdin>
  local rel="$1" path="$DEST_DIR/$1"
  mkdir -p "$(dirname "$path")"
  if [ -e "$path" ]; then
    log "stub 존재 — 보존: $rel"
  else
    cat > "$path"
    ok "stub 생성: $rel"
  fi
}

scaffold "index.md" <<EOF
---
title: llm-wiki index
type: reference
updated: $TODAY
sources: []
---

# llm-wiki — index

컴파일된 모든 페이지를 정확히 1회 등록하는 카탈로그. ingest/compile 가 이 목록을
갱신한다. (규칙은 SCHEMA.md, 동작은 스킬 SKILL.md.)

<!-- 형식: - [<page>](<path>.md) — <한 줄 요약> -->
EOF

scaffold "log.md" <<EOF
# llm-wiki — operation log

쓰기를 동반하는 op 는 여기에 한 줄을 남긴다(단일 append-only 파일, per-day 디렉터리 아님).
형식: \`## [YYYY-MM-DD] <op> | <title>\` + 필요 시 \`- Updated: <page>\`.
조회: \`grep -n "^## \[" log.md\`.
EOF

scaffold "raw-sources/index.md" <<EOF
---
title: raw-sources registry
type: reference
updated: $TODAY
sources: []
---

# raw-sources — registry

모든 소스를 버킷별로 등록한다. 각 항목은 \`path | slug | topics\` 테이블 행.
terse 하게 — 요약이 아니라 레지스트리다. (버킷 정의는 SCHEMA.md §Source buckets.)

## articles
| path | slug | topics |
|------|------|--------|

## conversations
| path | slug | topics |
|------|------|--------|

## notes
| path | slug | topics |
|------|------|--------|

## skills
| path | slug | topics |
|------|------|--------|
EOF

log "다음: 첫 ingest 1건 dogfooding (#42 운영 체크박스) — external/home PC."
