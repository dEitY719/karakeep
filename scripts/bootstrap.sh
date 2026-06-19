#!/usr/bin/env bash
# Karakeep 북마크 파이프라인 부트스트랩 (5-PC 공용)
#
# 신규 PC(Windows+WSL)에서 한 번 실행하면:
#   1) Windows 사용자 자동 탐지 → ObsidianVault-PARA 경로 확정
#   2) Windows vault 자동 생성 (PARA 골격 + .obsidian/Dataview + 대시보드)
#   3) python venv + karakeep-sync 설치
#   4) ~/.dotfiles-setup-mode 기반 config.yaml / .env / docker override 생성
#   5) docker compose up + karakeep-sync init
#
# 멱등(idempotent): 이미 있는 것은 건너뛰고, 사용자 비밀(.env)은 덮어쓰지 않는다.
# SSOT: docs/pc-environment.md
set -euo pipefail

# ---------- UX ----------
c() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
say()  { printf '%s %s\n' "$(c '1;34' '▶')" "$*"; }
ok()   { printf '%s %s\n' "$(c '1;32' '✓')" "$*"; }
warn() { printf '%s %s\n' "$(c '1;33' '!')" "$*"; }
die()  { printf '%s %s\n' "$(c '1;31' '✗')" "$*" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNC_DIR="$REPO_ROOT/sync"
AI="${KARAKEEP_AI:-auto}"      # auto|ollama|none|<url>   (--ai 로 덮어쓰기)
VAULT_PARENT_OVERRIDE=""        # --vault-parent 로 덮어쓰기

usage() {
  cat <<'EOF'
사용법: scripts/bootstrap.sh [옵션]

옵션:
  --ai <auto|ollama|none|URL>  AI 태깅 백엔드 (기본: auto = external→ollama, 그 외→none)
  --vault-parent <경로>         vault 부모 디렉토리 강제 (기본: <Windows홈>/Documents)
  -h, --help                    도움말

모드는 ~/.dotfiles-setup-mode (internal|external|home) 로 결정된다.
EOF
}
while [ $# -gt 0 ]; do
  case "$1" in
    --ai) AI="$2"; shift 2;;
    --vault-parent) VAULT_PARENT_OVERRIDE="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) die "알 수 없는 옵션: $1";;
  esac
done

# ---------- 0. preflight ----------
say "0/8 사전 점검"
for bin in docker python3 git curl openssl; do
  command -v "$bin" >/dev/null || die "$bin 가 필요합니다."
done
docker compose version >/dev/null 2>&1 || die "docker compose(v2) 가 필요합니다."
ok "필수 도구 확인"

# ---------- 1. 모드 ----------
say "1/8 모드 감지"
MODE_FILE="$HOME/.dotfiles-setup-mode"
MODE="$( [ -f "$MODE_FILE" ] && tr -d '[:space:]' < "$MODE_FILE" || echo home )"
case "$MODE" in internal|external|home) ;; *) warn "알 수 없는 모드 '$MODE' → home 으로 처리"; MODE=home;; esac
ok "모드: $MODE"

# ---------- 2. Windows vault 경로 ----------
say "2/8 Windows 사용자/vault 경로 탐지"
if [ -n "$VAULT_PARENT_OVERRIDE" ]; then
  VAULT_PARENT="$VAULT_PARENT_OVERRIDE"
else
  # Windows USERPROFILE 를 cmd.exe 로 얻어 WSL 경로로 변환 (\r 제거)
  WIN_PROFILE="$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r' || true)"
  if [ -n "$WIN_PROFILE" ] && command -v wslpath >/dev/null; then
    VAULT_PARENT="$(wslpath -u "$WIN_PROFILE")/Documents"
  else
    # 폴백: /mnt/c/Users 에서 시스템 계정 제외하고 추정
    guess="$(ls /mnt/c/Users 2>/dev/null | grep -viE '^(public|default|defaultuser0|all users)$' | head -1 || true)"
    [ -n "$guess" ] || die "Windows 사용자 자동 탐지 실패. --vault-parent 로 직접 지정하세요."
    VAULT_PARENT="/mnt/c/Users/$guess/Documents"
  fi
fi
VAULT="$VAULT_PARENT/ObsidianVault-PARA"
[ -d "$VAULT_PARENT" ] || die "vault 부모 경로 없음: $VAULT_PARENT"
ok "vault: $VAULT"

# ---------- 3. vault 골격 + .obsidian + 대시보드 ----------
say "3/8 Windows vault 생성/보강"
# 북마크 폴더(30-Resource/Bookmarks, 80-Company/Bookmarks)는 karakeep-sync init 의
# git clone 이 만든다. 여기선 상위 PARA 폴더만 생성.
for d in 10-Project 20-Area 30-Resource 40-Archive 80-Company 99-Inbox; do
  mkdir -p "$VAULT/$d"
done
# .obsidian 가 없으면 vault 로 인식되도록 최소 생성
mkdir -p "$VAULT/.obsidian/plugins/dataview"
# Dataview 다운로드 (멱등: main.js 있으면 skip). 사내망 간헐 차단 대비 재시도.
DV="$VAULT/.obsidian/plugins/dataview"
if [ ! -s "$DV/main.js" ]; then
  base="https://github.com/blacksmithgu/obsidian-dataview/releases/latest/download"
  for f in manifest.json main.js styles.css; do
    for i in 1 2 3 4 5; do
      curl -sL --fail --max-time 30 "$base/$f" -o "$DV/$f" && [ -s "$DV/$f" ] && break
      sleep 3
    done
    [ -s "$DV/$f" ] || warn "Dataview $f 다운로드 실패 (나중에 Obsidian에서 직접 설치 가능)"
  done
  [ -s "$DV/main.js" ] && ok "Dataview 설치" || warn "Dataview 미설치 — 수동 설치 필요"
else
  ok "Dataview 이미 설치됨"
fi
# 커뮤니티 플러그인 활성화 (dataview 포함, 중복 없이)
CP="$VAULT/.obsidian/community-plugins.json"
if [ ! -f "$CP" ] || ! grep -q dataview "$CP" 2>/dev/null; then
  echo '["dataview"]' > "$CP"
fi
# 대시보드 노트 (Bookmarks 폴더 밖 = git 제외). 없을 때만 생성.
DASH="$VAULT/30-Resource/Bookmarks Dashboard.md"
if [ ! -f "$DASH" ]; then
  cat > "$DASH" <<'EOF'
---
title: Bookmarks Dashboard
tags: [dashboard]
---

# 📚 북마크 대시보드

> Dataview 필요. 안 보이면 Ctrl+R 새로고침.

## 🏷️ 태그별 분류
```dataview
TABLE WITHOUT ID map(rows, (r) => elink(r.url, r.title)) AS "북마크", length(rows) AS "수"
FROM "30-Resource/Bookmarks"
FLATTEN tags AS tag
GROUP BY tag AS "태그"
SORT length(rows) DESC
```

## 🆕 최근 추가순
```dataview
TABLE WITHOUT ID elink(url, title) AS "북마크", tags AS "태그", created AS "추가일"
FROM "30-Resource/Bookmarks"
SORT created DESC
```
EOF
fi
ok "PARA 골격 + 대시보드 준비"

# ---------- 4. python venv + 설치 ----------
say "4/8 sync 패키지 설치"
cd "$SYNC_DIR"
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install -q -e ".[dev]" && ok "karakeep-sync 설치"
SYNC_BIN="$SYNC_DIR/.venv/bin/karakeep-sync"

# ---------- 5. config.yaml ----------
say "5/8 config.yaml 생성"
if [ -f "$SYNC_DIR/config.yaml" ]; then
  warn "config.yaml 이미 존재 → 유지 (vault_root 만 점검하세요)"
else
  sed "s#^vault_root:.*#vault_root: $VAULT#" "$SYNC_DIR/config.yaml.example" > "$SYNC_DIR/config.yaml"
  ok "config.yaml 생성 (vault_root=$VAULT)"
fi

# ---------- 6. .env ----------
say "6/8 .env 스캐폴드"
if [ -f "$REPO_ROOT/.env" ]; then
  ok ".env 이미 존재 → 유지"
else
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  warn ".env 생성됨 — 비밀값을 채우세요: NEXTAUTH_SECRET, (기동 후)KARAKEEP_API_KEY, GITHUB_PAT$([ "$MODE" = internal ] && echo ', GHES_PAT, GHES_HOST')"
fi

# ---------- 7. docker-compose.override.yml (모드별) ----------
say "7/8 docker override 생성 (모드: $MODE)"
OVERRIDE="$REPO_ROOT/docker-compose.override.yml"
CERTS_DIR="$REPO_ROOT/certs"
# 7a. 사내 TLS 가로채기(CA) 자동 감지 — 공개사이트 leaf 의 발급자가 호스트 번들의
#     self-signed 루트면 MITM 으로 보고 그 CA 를 추출한다 (회사 무관 일반 로직).
CA_INJECT=0
issuer="$(echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
          | openssl x509 -noout -issuer 2>/dev/null | sed 's/^issuer=//' || true)"
if [ -n "$issuer" ]; then
  bundle=/etc/ssl/certs/ca-certificates.crt
  if [ -f "$bundle" ]; then
    tmp="$(mktemp -d)"; awk 'BEGIN{n=0} /BEGIN CERT/{n++} {print > ("'"$tmp"'/c"n)}' "$bundle"
    for cf in "$tmp"/c*; do
      subj="$(openssl x509 -in "$cf" -noout -subject 2>/dev/null | sed 's/^subject=//' || true)"
      iss="$(openssl x509 -in "$cf" -noout -issuer 2>/dev/null | sed 's/^issuer=//' || true)"
      if [ "$subj" = "$issuer" ] && [ "$subj" = "$iss" ]; then  # 발급자 == self-signed 루트
        mkdir -p "$CERTS_DIR"; openssl x509 -in "$cf" -out "$CERTS_DIR/corp-ca.crt"; CA_INJECT=1; break
      fi
    done
    rm -rf "$tmp"
  fi
fi
[ "$CA_INJECT" = 1 ] && ok "사내 CA 감지·추출 (certs/corp-ca.crt)" || ok "사내 CA 없음 (MITM 아님)"

# 7b. AI 백엔드 결정
[ "$AI" = auto ] && { [ "$MODE" = external ] && AI=ollama || AI=none; }
OLLAMA_URL=""; OLLAMA_MODEL="${KARAKEEP_MODEL:-qwen2.5:7b}"
case "$AI" in
  ollama) OLLAMA_URL="http://host.docker.internal:11434";;
  none) ;;
  http*) OLLAMA_URL="$AI"; AI=ollama;;
  *) warn "알 수 없는 --ai '$AI' → none"; AI=none;;
esac

# 7c. override 작성 (이미 있으면 유지)
if [ -f "$OVERRIDE" ]; then
  warn "docker-compose.override.yml 이미 존재 → 유지 (수동 확인)"
else
  {
    echo "# bootstrap.sh 생성 — 머신 로컬 (gitignore). 모드: $MODE"
    echo "services:"
    echo "  karakeep:"
    if [ "$AI" = ollama ] || [ "$CA_INJECT" = 1 ]; then
      [ "$AI" = ollama ] && { echo "    extra_hosts:"; echo '      - "host.docker.internal:host-gateway"'; }
      echo "    environment:"
      [ "$CA_INJECT" = 1 ] && echo "      NODE_EXTRA_CA_CERTS: /certs/corp-ca.crt"
      [ "$AI" = ollama ] && { echo "      OLLAMA_BASE_URL: $OLLAMA_URL"; echo "      INFERENCE_TEXT_MODEL: $OLLAMA_MODEL"; echo '      INFERENCE_CONTEXT_LENGTH: "8192"'; }
      [ "$CA_INJECT" = 1 ] && { echo "    volumes:"; echo "      - ./certs:/certs:ro"; }
    fi
    echo "  chrome:"
    echo "    command:"
    echo "      - --no-sandbox"
    echo "      - --disable-gpu"
    echo "      - --disable-dev-shm-usage"
    echo "      - --remote-debugging-address=0.0.0.0"
    echo "      - --remote-debugging-port=9222"
    echo "      - --hide-scrollbars"
    [ "$CA_INJECT" = 1 ] && echo "      - --ignore-certificate-errors"
  } > "$OVERRIDE"
  ok "override 생성 (AI=$AI, CA=$CA_INJECT)"
fi

# ---------- 8. 기동 + init ----------
say "8/8 컨테이너 기동 + init"
ENV_OK=1
grep -q '^KARAKEEP_API_KEY=.\+' "$REPO_ROOT/.env" 2>/dev/null || ENV_OK=0
( cd "$REPO_ROOT" && docker compose up -d ) && ok "컨테이너 기동"
if [ "$ENV_OK" = 1 ]; then
  ( cd "$SYNC_DIR" && set -a && . "$REPO_ROOT/.env" && set +a && "$SYNC_BIN" init ) && ok "karakeep-sync init 완료"
else
  warn "KARAKEEP_API_KEY 미입력 → init 보류. .env 채운 뒤 수동 실행:"
  echo "    cd $SYNC_DIR && source .venv/bin/activate && set -a && source ../.env && set +a && karakeep-sync init"
fi

# ---------- 안내 ----------
echo
ok "부트스트랩 완료 (모드: $MODE)"
echo "남은 수동 단계:"
echo "  • .env 의 비밀값(API key/PAT) 확인 — 미입력 시 위 init 명령 수동 실행"
if [ "$AI" = ollama ]; then
  echo "  • Ollama 가 0.0.0.0 으로 떠야 컨테이너가 닿음. 안 되면:"
  echo "      sudo mkdir -p /etc/systemd/system/ollama.service.d && \\"
  echo "      printf '[Service]\\nEnvironment=\"OLLAMA_HOST=0.0.0.0\"\\n' | sudo tee /etc/systemd/system/ollama.service.d/override.conf && \\"
  echo "      sudo systemctl daemon-reload && sudo systemctl restart ollama"
  echo "  • 모델 준비: ollama pull $OLLAMA_MODEL"
fi
echo "  • Obsidian 에서 ObsidianVault-PARA 열기 → 커뮤니티 플러그인 켜기(제한모드 해제) → Ctrl+R"
