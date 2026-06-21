# karakeep

개인 북마크 관리 시스템. Karakeep(로컬 캡처) → Obsidian Markdown → Git(GitHub/GHES) 양방향 sync.

## 요구사항

- Docker, Docker Compose
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python 패키지·가상환경 관리) — [mise](https://mise.jdx.dev/)로 함께 관리 권장
- Git

## 최초 설치

`.env` 변수는 **사용 시점이 둘로 나뉩니다.** 컨테이너 기동에 필요한 값만 먼저
채우고, `KARAKEEP_API_KEY`는 컨테이너를 띄운 뒤 웹 UI에서 발급해 채웁니다.
(컨테이너는 API key를 읽지 않으므로, 발급 후 재시작 불필요)

    # 1. Karakeep 실행 — 서버 변수만 먼저 채움
    cp .env.example .env
    #   .env 편집: NEXTAUTH_SECRET / NEXTAUTH_URL / DATA_DIR 만 입력
    #   (KARAKEEP_API_KEY 는 비워둔 채로 진행 — 3단계에서 채움)
    docker compose up -d

    # 2. API key 발급
    #   브라우저로 http://localhost:3001 접속 → 회원가입/로그인
    #   → Settings → API Keys 에서 키 발급
    #   → .env 의 KARAKEEP_API_KEY= 에 붙여넣기
    #   GitHub/GHES PAT 는 github.com/settings/tokens 등에서 미리 발급해 함께 채움

    # 3. sync 패키지 설치 (mise + uv)
    cd sync
    mise install        # mise.toml 의 python·uv 설치 (mise 사용 시; 미사용이면 생략)
    uv sync             # .venv 생성 + 의존성 설치 (dev 포함)
    #   이후 entry point 는 `uv run karakeep-sync ...` 로 실행 (또는 `mise run run`).
    #   .venv 를 직접 활성화해 `karakeep-sync` 를 쓰려면: source .venv/bin/activate

    # 4. config 설정
    cp config.yaml.example config.yaml

    #   (a) vault_root — 이 PC의 Obsidian vault 경로로 반드시 수정.
    #       PC마다 다릅니다. Obsidian 앱에서 vault 위치를 확인하거나:
    #         ls -d ~/obsidian-vault 2>/dev/null || echo "없음 → 직접 지정"
    #       vault가 아직 없으면 먼저 만들고(또는 Obsidian에서 생성) 그 경로를 적습니다.
    #       Bookmarks 하위 폴더까지 포함 (예: ~/Documents/MyVault/10_Bookmarks)

    #   (b) repos.*.remote — clone 대상 repo가 GitHub/GHES에 미리 존재해야 함.
    #       init 은 git clone 만 합니다(자동 생성 X). 없으면 먼저 생성:
    #         gh repo create dEitY719/bookmarks-common --private
    #       PAT 에 해당 repo Contents:Read 권한이 있는지 확인.

    #   (c) PAT/API key 는 .env 가 아니라 쉘 환경변수로 주입됩니다.
    #       init/pull/push 실행 전 반드시:
    #         set -a && source ../.env && set +a

    # 5. 초기화 (git clone + cron 등록)
    uv run karakeep-sync init

    # 6. 기존 북마크 import
    uv run karakeep-sync pull

## 일상 사용

`sync/` 디렉토리에서 실행 (또는 `.venv` 활성화 후 `karakeep-sync` 직접 호출):

| 명령 | 설명 |
|------|------|
| `uv run karakeep-sync push` | Karakeep → git push |
| `uv run karakeep-sync pull` | git pull → Karakeep import |
| `uv run karakeep-sync auto` | pull + push (cron 자동 실행) |
| `uv run karakeep-sync status` | 미동기 북마크 수 확인 |

cron은 `init` 시 자동 등록됨 (30분마다 `auto` 실행). cron 라인은
`sync/.venv/bin/karakeep-sync` 절대 경로를 쓰므로 `uv sync` 로 만든 venv 에서
그대로 동작함.

## Docker 운영

    docker compose up -d                          # 시작
    docker compose down                           # 중지
    docker compose pull && docker compose up -d   # 업데이트
    docker compose logs -f                        # 로그 확인

## PC 모드

`~/.dotfiles-setup-mode` 파일 기준:
- `internal` → 회사 모드: Company(GHES) push/pull + Common(GitHub) pull only
- 그 외 → 집 모드: Common(GitHub) push/pull

## 태그 체계 (권장)

    area/work        area/personal
    topic/python     topic/ai       topic/infra    topic/finance
    status/read-later  status/reference  status/archive
    source/blog      source/docs    source/company
