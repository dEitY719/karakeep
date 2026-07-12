#!/usr/bin/env bash
# Karakeep 북마크 파이프라인 부트스트랩 (5-PC 공용)
#
# 신규 PC(Windows+WSL)에서 한 번 실행하면:
#   1) Windows 사용자 자동 탐지 → ObsidianVault-PARA 경로 확정
#   2) Windows vault 자동 생성 (PARA 골격 + .obsidian/Dataview + 대시보드)
#   3) uv sync (venv + karakeep-sync 설치)
#   4) ~/.dotfiles-setup-mode 기반 config.yaml / .env / docker override 생성
#   5) docker compose up + karakeep-sync init
#
# 멱등(idempotent): 이미 있는 것은 건너뛰고, 사용자 비밀(.env)은 덮어쓰지 않는다.
# SSOT: docs/architecture/system/pc-environment.md
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
MODE_OVERRIDE=""                # --mode 로 덮어쓰기 (없으면 ~/.dotfiles-setup-mode)
SYNC_HOST=0                     # --sync-host: docker 미실행(순수 sync 클라이언트). external 외 모드는 자동 적용

usage() {
  cat <<'EOF'
사용법: scripts/bootstrap.sh [옵션]

옵션:
  --mode <internal|external|home>  PC 모드 강제 (기본: ~/.dotfiles-setup-mode 읽음. public=home 별칭)
  --sync-host                  docker 미실행 (순수 sync 클라이언트). external 외 모드는 자동 적용
  --ai <auto|ollama|none|URL>  AI 태깅 백엔드 (기본: auto = external→ollama, 그 외→none)
  --vault-parent <경로>         vault 부모 디렉토리 강제 (기본: <Windows홈>/Documents)
  -h, --help                    도움말

모드 결정 우선순위: --mode 옵션 > ~/.dotfiles-setup-mode 파일.
둘 다 없으면 에러로 종료하며 internal|external|home 중 하나를 지정하라고 안내한다.

docker: external 모드에서만 Karakeep 컨테이너를 띄운다. internal/home 은
공유 인스턴스를 바라보는 순수 sync 클라이언트라 자동으로 --sync-host 가 적용된다
(docker 미실행). external 에서도 컨테이너 없이 돌리려면 --sync-host 를 직접 준다.
EOF
}
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE_OVERRIDE="$2"; shift 2;;
    --sync-host) SYNC_HOST=1; shift;;
    --ai) AI="$2"; shift 2;;
    --vault-parent) VAULT_PARENT_OVERRIDE="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) die "알 수 없는 옵션: $1";;
  esac
done

# ---------- 0. 모드 + sync-host 결정 ----------
say "0/8 모드 감지"
MODE_FILE="$HOME/.dotfiles-setup-mode"
# 우선순위: --mode 옵션 > ~/.dotfiles-setup-mode. 둘 다 없으면 조용히 home 으로
# 떨어지지 않고 에러로 종료한다 (잘못된 모드로 docker/clone 이 도는 사고 방지).
if [ -n "$MODE_OVERRIDE" ]; then
  MODE="$MODE_OVERRIDE"; MODE_SRC="--mode 옵션"
elif [ -f "$MODE_FILE" ]; then
  MODE="$(tr -d '[:space:]' < "$MODE_FILE")"; MODE_SRC="$MODE_FILE"
else
  die "모드를 결정할 수 없습니다 ($MODE_FILE 없음, --mode 옵션 없음).
    다음 중 하나로 지정하세요:
      (a) scripts/bootstrap.sh --mode <internal|external|home>
      (b) echo <internal|external|home> > $MODE_FILE   # 셋 중 하나 골라 입력 후 재실행
      (public 은 home 별칭으로 허용)"
fi
# dotfiles 는 공용 PC 를 'public' 으로 명명한다. karakeep 파이프라인에는 별도 public
# 동작이 없고 home 과 완전히 동일하므로 여기서 home 으로 정규화한다 (home=public).
[ "$MODE" = public ] && MODE=home
case "$MODE" in
  internal|external|home) ;;
  *) die "잘못된 모드 '$MODE' (출처: $MODE_SRC). internal|external|home(또는 home 별칭인 public) 중 하나여야 합니다.";;
esac
# docker 로 Karakeep 을 실제 띄우는 건 external(공유 인스턴스 호스트)뿐.
# internal/home 은 공유 인스턴스를 바라보는 순수 sync 클라이언트 → docker 미실행.
AUTO_SYNC=0
if [ "$MODE" != external ] && [ "$SYNC_HOST" = 0 ]; then SYNC_HOST=1; AUTO_SYNC=1; fi
MODE_NOTE=""
[ "$SYNC_HOST" = 1 ] && MODE_NOTE=" · sync-host(docker 미실행)$([ "$AUTO_SYNC" = 1 ] && echo ' [자동]')"
ok "모드: $MODE (출처: $MODE_SRC)$MODE_NOTE"

# ---------- 1. preflight ----------
say "1/8 사전 점검"
for bin in python3 git curl openssl; do
  command -v "$bin" >/dev/null || die "$bin 가 필요합니다."
done
command -v uv >/dev/null 2>&1 || die "uv 가 필요합니다 — https://docs.astral.sh/uv/ 설치 후 재실행"
if [ "$SYNC_HOST" = 0 ]; then
  command -v docker >/dev/null || die "docker 가 필요합니다 (external 모드). sync 전용이면 --sync-host 를 쓰세요."
  docker compose version >/dev/null 2>&1 || die "docker compose(v2) 가 필요합니다."
fi
ok "필수 도구 확인"

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
# Dataview FROM 절은 internal/external/home 공통 통합 쿼리다 (이슈 #27):
#   - 30-Resource/Bookmarks : 공용 북마크 (전 PC 존재).
#   - 80-Company/Bookmarks  : 사내 북마크. 공용 obsidian-para 가 80-Company 를
#     .gitignore 로 제외하고 external/home 은 GHES 사내 repo 에 접속할 수 없어 그 PC 에는
#     폴더 자체가 없다 → OR 대상이어도 결과에 잡히지 않는다.
# 따라서 OR 조합은 모든 모드에서 안전하다: external/home 은 공용만, internal 은
# 공용+사내 북마크가 함께 표시된다. 대시보드는 git(obsidian-para)로 전 PC 공유되므로
# 모드별로 다른 내용을 쓰면 충돌 → 단일 통합 쿼리가 정답.
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
FROM "30-Resource/Bookmarks" OR "80-Company/Bookmarks"
FLATTEN tags AS tag
GROUP BY tag AS "태그"
SORT length(rows) DESC
```

## 🆕 최근 추가순
```dataview
TABLE WITHOUT ID elink(url, title) AS "북마크", tags AS "태그", created AS "추가일"
FROM "30-Resource/Bookmarks" OR "80-Company/Bookmarks"
SORT created DESC
```
EOF
  ok "대시보드 생성 (통합 쿼리)"
else
  # 구버전 대시보드 마이그레이션: 단일 경로 FROM → 통합 OR. 멱등(이미 OR 면 no-op).
  if grep -q '^FROM "30-Resource/Bookmarks"$' "$DASH"; then
    sed -i 's#^FROM "30-Resource/Bookmarks"$#FROM "30-Resource/Bookmarks" OR "80-Company/Bookmarks"#' "$DASH"
    ok "대시보드 FROM 절 통합 쿼리로 갱신 (#27)"
  else
    ok "대시보드 이미 통합 쿼리 (유지)"
  fi
fi
ok "PARA 골격 + 대시보드 준비"

# 참고: 전체 vault 노트 동기화는 git(`obsidian-para`) 기반이다 — `scripts/vault-sync.sh`
# 가 모드별 clone/pull + internal push 차단을 적용한다 (SSOT: docs/architecture/system/pc-environment.md §6).
# (구 Syncthing `.stignore` 배치 단계는 폐기됨.)

# ---------- 4. uv sync (venv + 설치) ----------
say "4/8 sync 패키지 설치 (uv)"
cd "$SYNC_DIR"
# uv sync: .venv 생성 + 의존성 + dev 그룹(pytest) 설치. dev 는 기본 그룹이라 자동 포함.
# (uv 존재 여부는 1단계 preflight 에서 확인)
uv sync -q && ok "karakeep-sync 설치 (uv sync — .venv + dev 의존성)"
SYNC_BIN="$SYNC_DIR/.venv/bin/karakeep-sync"

# ---------- 5. config.yaml (모드별) ----------
say "5/8 config.yaml 생성 (모드: $MODE)"
CFG="$SYNC_DIR/config.yaml"
if [ -f "$CFG" ]; then
  warn "config.yaml 이미 존재 → 유지 (vault_root/url 만 점검하세요)"
else
  # 모드별 구성:
  #   external : 공유 Karakeep 호스트(localhost) + 공용 북마크(GitHub), Company 제외.
  #   internal : 공유 인스턴스(sync 클라이언트) + 사내 북마크(GHES) only.
  #   home     : 공유 인스턴스(sync 클라이언트) + 공용 북마크(GitHub), Company 제외.
  # ⚠️ 공유 인스턴스 URL·사내 GHES owner 는 공개 repo 에 못 박지 않고 .env 변수로
  #    둔다(config.py 가 ${...} 를 런타임에 치환). config.yaml 자체도 gitignore 됨.
  {
    echo "# bootstrap.sh 생성 (mode=$MODE) — 머신 로컬(gitignore). SSOT: docs/architecture/system/pc-environment.md"
    echo "karakeep:"
    if [ "$MODE" = external ]; then
      echo "  url: http://localhost:3001"
    else
      echo "  url: \${KARAKEEP_URL}        # .env 의 공유 인스턴스 URL (예: Tailscale Funnel)"
    fi
    echo "  api_key: \${KARAKEEP_API_KEY}"
    echo "vault_root: $VAULT"
    echo "repos:"
    if [ "$MODE" = internal ]; then
      echo "  company:"
      echo "    path: 80-Company/Bookmarks"
      echo "    remote: https://\${GHES_PAT}@\${GHES_HOST}/\${GHES_OWNER}/bookmarks-company.git"
      echo "    pull: true"
      echo "    include_lists: [Company]   # Company 리스트만 GHES 로 (화이트리스트)"
    else
      echo "  common:"
      echo "    path: 30-Resource/Bookmarks"
      echo "    remote: https://\${GITHUB_PAT}@github.com/dEitY719/bookmarks-common.git"
      echo "    pull: true"
      echo "    exclude_lists: [Company]   # Company(사내) 는 공개 repo 에서 제외 (유출 방지)"
    fi
    echo "logs:"
    echo "  dir: ~/apps/karakeep/logs"
    echo "  retention_days: 30"
  } > "$CFG"
  ok "config.yaml 생성 (mode=$MODE, vault_root=$VAULT)"
  [ "$MODE" != external ] && warn "공유 인스턴스 URL 을 .env 의 KARAKEEP_URL 에 설정하세요 (미설정 시 빈 URL 로 실패)."
  [ "$MODE" = internal ] && warn "사내 GHES owner 를 .env 의 GHES_OWNER 에 설정하세요 (예: byoungwoo-yoon)."
fi

# ---------- 6. .env ----------
say "6/8 .env 스캐폴드"
ENV_CREATED=0
if [ -f "$REPO_ROOT/.env" ]; then
  ok ".env 이미 존재 → 유지"
else
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  ENV_CREATED=1
fi

# ---------- 6b. GIT_TRANSPORT 해소 (auto → ssh/https, 1회) ----------
# 값: auto(기본)|ssh|https. ssh/https 로 이미 고정돼 있으면 존중하고 프로브 생략.
# auto 면 repo host 별로 SSH 인증을 1회 프로브해 하나라도 성공하면 ssh, 아니면 https 로
# 고정한다. config.py/cron 은 절대 프로브하지 않는다(결정적) — 오직 여기서만 해소한다.
grep -q '^GIT_TRANSPORT=' "$REPO_ROOT/.env" || printf 'GIT_TRANSPORT=auto\n' >> "$REPO_ROOT/.env"
GIT_TRANSPORT="$(grep '^GIT_TRANSPORT=' "$REPO_ROOT/.env" | head -1 | cut -d= -f2- | tr -d '[:space:]' || true)"
[ -n "$GIT_TRANSPORT" ] || GIT_TRANSPORT=auto
if [ "$GIT_TRANSPORT" = ssh ] || [ "$GIT_TRANSPORT" = https ]; then
  ok "GIT_TRANSPORT=$GIT_TRANSPORT (고정값 존중 — 프로브 생략)"
else
  say "GIT_TRANSPORT=auto → SSH 인증 프로브"
  # 항상 github.com, internal 이면 .env 의 GHES_HOST 도 프로브(있을 때만).
  PROBE_HOSTS="github.com"
  if [ "$MODE" = internal ]; then
    GHES_HOST_ENV="$(grep '^GHES_HOST=' "$REPO_ROOT/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '[:space:]' || true)"
    [ -n "$GHES_HOST_ENV" ] && PROBE_HOSTS="$PROBE_HOSTS $GHES_HOST_ENV"
  fi
  SSH_OK=0
  for probe_host in $PROBE_HOSTS; do
    # GitHub/GHES 는 인증 성공이어도 shell 이 없어 non-zero 로 끝난다. 성공 여부는
    # exit code 가 아니라 배너 문구로 판정한다(성공 시 'successfully authenticated ...
    # does not provide shell access'). 타임아웃/Permission denied/resolve 실패는 실패.
    probe_out="$(ssh -T -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new "git@$probe_host" 2>&1 || true)"
    if printf '%s' "$probe_out" | grep -qiE 'success|authenticated|does not provide shell'; then
      SSH_OK=1; ok "SSH 인증 성공: git@$probe_host"; break
    else
      warn "SSH 인증 안 됨: git@$probe_host"
    fi
  done
  if [ "$SSH_OK" = 1 ]; then
    GIT_TRANSPORT=ssh
    tmp_env="$(mktemp)"; sed 's#^GIT_TRANSPORT=.*#GIT_TRANSPORT=ssh#' "$REPO_ROOT/.env" > "$tmp_env" && mv "$tmp_env" "$REPO_ROOT/.env"
    ok "SSH 인증 성공 → GIT_TRANSPORT=ssh (PAT 불필요)"
  else
    GIT_TRANSPORT=https
    tmp_env="$(mktemp)"; sed 's#^GIT_TRANSPORT=.*#GIT_TRANSPORT=https#' "$REPO_ROOT/.env" > "$tmp_env" && mv "$tmp_env" "$REPO_ROOT/.env"
    warn "SSH 인증 실패 → GIT_TRANSPORT=https (기존처럼 PAT 필요)"
  fi
fi

# 6c. .env 를 새로 만든 경우에만 채워야 할 비밀값을 안내한다.
# PAT(GITHUB_PAT/GHES_PAT)는 transport=https 일 때만 필요 — ssh 면 목록에서 뺀다.
# (GHES_HOST/GHES_OWNER 는 SSH remote 조립에도 쓰이므로 internal 이면 계속 필요.)
if [ "$ENV_CREATED" = 1 ]; then
  NEED="KARAKEEP_API_KEY"
  [ "$SYNC_HOST" = 0 ] && NEED="NEXTAUTH_SECRET, $NEED"
  [ "$MODE" != external ] && NEED="$NEED, KARAKEEP_URL"
  if [ "$GIT_TRANSPORT" = https ]; then
    if [ "$MODE" = internal ]; then NEED="$NEED, GHES_PAT, GHES_HOST, GHES_OWNER"; else NEED="$NEED, GITHUB_PAT"; fi
  elif [ "$MODE" = internal ]; then
    NEED="$NEED, GHES_HOST, GHES_OWNER"
  fi
  warn ".env 생성됨 — 비밀값을 채우세요: $NEED"
fi
[ "$GIT_TRANSPORT" = ssh ] && ok "PAT 불필요 (SSH 사용) — ~/.ssh 키로 git 인증"

# ---------- 7. docker-compose.override.yml (모드별) ----------
say "7/8 docker override 생성 (모드: $MODE)"
if [ "$SYNC_HOST" = 1 ]; then
  ok "sync-host → 로컬 컨테이너 없음, override 생략"
else
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
fi

# ---------- 8. 기동 + init ----------
say "8/8 $([ "$SYNC_HOST" = 1 ] && echo 'init (sync-host: docker 미실행)' || echo '컨테이너 기동 + init')"
ENV_OK=1
grep -q '^KARAKEEP_API_KEY=.\+' "$REPO_ROOT/.env" 2>/dev/null || ENV_OK=0
if [ "$SYNC_HOST" = 0 ]; then
  ( cd "$REPO_ROOT" && docker compose up -d ) && ok "컨테이너 기동"
fi
if [ "$ENV_OK" = 1 ]; then
  ( cd "$SYNC_DIR" && set -a && . "$REPO_ROOT/.env" && set +a && "$SYNC_BIN" init ) && ok "karakeep-sync init 완료"
else
  warn "KARAKEEP_API_KEY 미입력 → init 보류. .env 채운 뒤 수동 실행:"
  echo "    cd $SYNC_DIR && set -a && source ../.env && set +a && uv run karakeep-sync init"
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
echo "  • 전체 vault 노트 동기화(git) — SSOT: docs/architecture/system/pc-environment.md §6:"
echo "      - scripts/vault-sync.sh 실행 → 공용 obsidian-para clone/pull (전 PC)"
echo "      - 80-Company/ 는 공용 repo 에서 .gitignore 로 제외 (사내 노트 유출 방지)"
if [ "$MODE" = internal ]; then
  echo "      - internal 은 공용 repo PULL ONLY. 사내 노트는 GHES obsidian-para(80-Company)로만"
  echo "        push/pull — external/home PC 에는 존재하지 않음"
fi
