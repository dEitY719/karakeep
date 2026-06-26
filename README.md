# karakeep

개인 북마크 관리 시스템. Karakeep(로컬 캡처) → Obsidian Markdown → Git(GitHub/GHES) 양방향 sync.

## 요구사항

- Git, Python 3.11+, `curl`, `openssl`
- [uv](https://docs.astral.sh/uv/) (Python 패키지·가상환경 관리) — [mise](https://mise.jdx.dev/)로 함께 관리 권장
- Docker, Docker Compose — **`external` 모드(Karakeep 호스트)에서만** 필요.
  `internal`/`home` 은 공유 인스턴스를 바라보는 sync 클라이언트라 docker 가 필요 없습니다.

## 최초 설치

신규 PC(Windows+WSL)는 이 repo 를 clone 한 뒤 **`scripts/bootstrap.sh` 한 번**이면 됩니다.
모드만 먼저 정해두면 나머지(vault 골격 · `uv sync` · `config.yaml` · `.env` · docker
override · `karakeep-sync init`)는 스크립트가 모드에 맞춰 자동 처리합니다.
멱등(idempotent)이라 다시 돌려도 안전합니다. (SSOT: [docs/pc-environment.md](docs/pc-environment.md))

    # 1. 이 PC의 모드 지정 (한 번만)
    echo home > ~/.dotfiles-setup-mode          # internal | external | home 중 하나
    #   (또는 매 실행마다: ./scripts/bootstrap.sh --mode home)

    # 2. 부트스트랩 — 한 방에
    ./scripts/bootstrap.sh

    # 3. .env 비밀값 채우기
    #   스크립트가 끝에 "비밀값을 채우세요: ..." 로 모드별 필요한 키만 알려줍니다.
    #     - external : NEXTAUTH_SECRET · KARAKEEP_API_KEY(웹 UI 발급) · GITHUB_PAT
    #     - internal : KARAKEEP_URL(공유 인스턴스) · KARAKEEP_API_KEY · GHES_PAT/GHES_HOST/GHES_OWNER
    #     - home     : KARAKEEP_URL(공유 인스턴스) · KARAKEEP_API_KEY · GITHUB_PAT
    #   external 의 KARAKEEP_API_KEY 는 http://localhost:3001 → Settings → API Keys 에서 발급.
    #   API key 가 비어 init 이 보류됐다면, 채운 뒤 스크립트가 출력한 init 명령을 그대로 실행.

    # 4. 노트(vault 전체) 동기화 — 북마크 외 일반 노트까지 PC 간 git 공유
    ./scripts/vault-sync.sh
    #   첫 실행 시 시크릿 템플릿(~/.config/obsidian-para/secrets.env)을 만들고 멈춥니다.
    #   값을 채운 뒤 다시 실행하세요. 상세: scripts/README.md

### 모드별 차이 (요약)

| 모드 | Karakeep | 공용 북마크·노트 (GitHub) | 사내 (`80-Company`, GHES) |
|------|----------|---------------------------|----------------------------|
| `external` | 로컬 컨테이너 **호스트** (docker ✓) | push/pull (생성·수정 담당) | — |
| `internal` | 공유 인스턴스 **sync 클라이언트** (docker ✗) | **pull only** | push/pull |
| `home` | 공유 인스턴스 **sync 클라이언트** (docker ✗) | push/pull | — |

- **external** 만 Karakeep 컨테이너를 띄웁니다. `internal`/`home` 은 external 이 호스팅하는
  공유 인스턴스(`.env` 의 `KARAKEEP_URL`)에 붙는 순수 sync 클라이언트라 docker 가 필요 없습니다
  (bootstrap 이 `--sync-host` 를 자동 적용).
- **internal** 은 공용 repo push 불가(pull-only) — 공용 노트의 *생성·수정은 external/home 에서*.
  사내 콘텐츠는 **`80-Company/` 아래에만** 두며(밖에 두면 `vault-sync.sh` 가 거부), GHES 로만 동기화됩니다.
- 토폴로지·동기화 규칙 전체는 [docs/pc-environment.md](docs/pc-environment.md) 참고.

<details>
<summary>수동 설치 (bootstrap 없이, 고급/디버깅용)</summary>

`bootstrap.sh` 가 자동화하는 단계를 손으로 밟는 방법입니다. 보통은 필요 없습니다.

    # 1. Karakeep 실행 (external 모드) — 서버 변수만 먼저 채움
    cp .env.example .env
    #   .env 편집: NEXTAUTH_SECRET / NEXTAUTH_URL / DATA_DIR 만 입력
    #   (KARAKEEP_API_KEY 는 비워둔 채로 진행 — 2단계에서 채움)
    docker compose up -d

    # 2. API key 발급
    #   브라우저로 http://localhost:3001 접속 → 회원가입/로그인
    #   → Settings → API Keys 에서 키 발급 → .env 의 KARAKEEP_API_KEY= 에 붙여넣기
    #   GitHub/GHES PAT 는 github.com/settings/tokens 등에서 미리 발급해 함께 채움

    # 3. sync 패키지 설치 (mise + uv)
    cd sync
    mise install        # mise.toml 의 python·uv 설치 (mise 사용 시; 미사용이면 생략)
    uv sync             # .venv 생성 + 의존성 설치 (dev 포함)
    #   이후 entry point 는 `uv run karakeep-sync ...` (또는 `mise run run`).

    # 4. config 설정
    cp config.yaml.example config.yaml
    #   (a) vault_root — 이 PC의 Obsidian vault 경로로 반드시 수정 (PC마다 다름).
    #   (b) repos.*.remote — clone 대상 repo 가 GitHub/GHES 에 미리 존재해야 함
    #       (init 은 git clone 만 함). 없으면: gh repo create dEitY719/bookmarks-common --private
    #   (c) PAT/API key 는 .env 가 아니라 쉘 환경변수로 주입 — init/pull 전:
    #         set -a && source ../.env && set +a

    # 5. 초기화 + 기존 북마크 import
    uv run karakeep-sync init
    uv run karakeep-sync pull

</details>

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

모드는 `~/.dotfiles-setup-mode` 파일(또는 `--mode`)로 결정됩니다 — 모드별 차이는
위 [모드별 차이 (요약)](#모드별-차이-요약) 표를, 전체 토폴로지는
[docs/pc-environment.md](docs/pc-environment.md) 를 참고하세요.

노트 동기화(`scripts/vault-sync.sh`)는 모드를 인지해 경로를 자동 탐지하고
`internal` 은 pull-only 로 동작합니다. 상세 가이드: [scripts/README.md](scripts/README.md).

## llm-wiki 연동

`/llm-wiki` 스킬(Karpathy-style LLM-curated 지식 베이스)을 Obsidian vault 와
연동합니다. 중앙 위키의 **canonical 위치**(모든 PC 공통, `<USERNAME>` 만 상이):

    C:\Users\<USERNAME>\Documents\ObsidianVault-PARA\30_Resources\llm-wiki\
    # WSL: /mnt/c/Users/<USERNAME>/Documents/ObsidianVault-PARA/30_Resources/llm-wiki/

> ⚠️ underscore `30_Resources` 가 위키 경로입니다. 하이픈 `30-Resource/Bookmarks`
> 는 별개의 Karakeep 북마크 서브모듈이며 위키와 무관합니다.

각 프로젝트에서 위키를 찾도록, global `~/.claude/CLAUDE.md` 에 아래 한 줄을 둡니다
(글로벌 설정 파일이라 이 repo 에 두지 않고 스니펫으로 제공 — `<USERNAME>` 만 교체):

    llm-wiki location: C:\Users\<USERNAME>\Documents\ObsidianVault-PARA\30_Resources\llm-wiki\

프로젝트 SCHEMA.md([docs/proposals/llm-wiki/SCHEMA.md](docs/proposals/llm-wiki/SCHEMA.md))를
vault 로 배치하려면 — **external/home PC 에서만** (internal 은 쓰기 경계로 거부):

    ./scripts/llm-wiki-deploy.sh

멱등(재실행 안전)이며, vault 경로를 자동 탐지합니다. stub 생성·첫 ingest 는 이슈
#42, 쓰기 경계 정책은 #44 를 참고하세요.

## 태그 체계 (권장)

    area/work        area/personal
    topic/python     topic/ai       topic/infra    topic/finance
    status/read-later  status/reference  status/archive
    source/blog      source/docs    source/company
