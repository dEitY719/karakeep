# karakeep

개인 북마크 관리 시스템. Karakeep(로컬 캡처) → Obsidian Markdown → Git(GitHub/GHES) 양방향 sync.

## 요구사항

- Docker, Docker Compose
- Python 3.11+
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

    # 3. sync 패키지 설치
    cd sync
    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

    # 4. config 설정
    cp config.yaml.example config.yaml   # config.yaml 편집

    # 5. 초기화 (git clone + cron 등록)
    karakeep-sync init

    # 6. 기존 북마크 import
    karakeep-sync pull

## 일상 사용

| 명령 | 설명 |
|------|------|
| `karakeep-sync push` | Karakeep → git push |
| `karakeep-sync pull` | git pull → Karakeep import |
| `karakeep-sync auto` | pull + push (cron 자동 실행) |
| `karakeep-sync status` | 미동기 북마크 수 확인 |

cron은 `init` 시 자동 등록됨 (30분마다 `auto` 실행).

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
