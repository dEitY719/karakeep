# karakeep

개인 북마크 관리 시스템. Karakeep(로컬 캡처) → Obsidian Markdown → Git(GitHub/GHES) 양방향 sync.

## 요구사항

- Docker, Docker Compose
- Python 3.11+
- Git

## 최초 설치

    # 1. Karakeep 실행
    cp .env.example .env   # .env 편집: API key + PAT 입력
    docker compose up -d

    # 2. sync 패키지 설치
    cd sync
    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

    # 3. config 설정
    cp config.yaml.example config.yaml   # config.yaml 편집

    # 4. 초기화 (git clone + cron 등록)
    karakeep-sync init

    # 5. 기존 북마크 import
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
