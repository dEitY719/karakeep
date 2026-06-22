# PC Environment (SSOT)

Karakeep 북마크 파이프라인을 운영하는 **5개 PC 환경의 단일 진실 공급원(SSOT)**.
모든 PC는 동일한 북마크를 공유하고, 동일한 `ObsidianVault-PARA` 를 구성한다.

> 비밀(토큰·CA·내부 호스트·회사명)은 이 문서에 적지 않는다. 그것들은
> gitignore 된 `.env` / `docker-compose.override.yml` / 개인 메모리에만 존재한다.
> 이 repo 가 public 이면 이 문서는 토폴로지만 담아야 한다.

## 1. 공통 전제

- 모든 PC: **Windows + WSL**. Windows 사용자명과 WSL 사용자명은 **PC마다 다름**
  → 경로를 하드코딩하지 말고 런타임에 탐지한다 (부트스트랩 스크립트 참고).
- 모드 스위치: `~/.dotfiles-setup-mode` 파일에 `internal` | `external` | `home` 중 하나.

## 2. PC 인벤토리 (5대)

| 모드 | 대수 | 사양 / LLM | 네트워크 | 비고 |
|------|------|-----------|----------|------|
| `internal` | 2 | 1대만 사내 local LLM 연동 가능 | 사내망 | GHES 사용 |
| `external` | 1 | 최고 사양, **Ollama 로컬 서빙** | 회사에서 외부 접속 가능 | (이 세션 PC) |
| `home` | 2 | 노트북, 저사양 → **local LLM 불가** | 집 | |

> 모바일 앱이나 `home` PC 에서 추가한 즐겨찾기는 AI 태깅이 안 된다.
> → `external`(또는 internal-LLM) PC 에서 나중에 **재태깅**하고 sync 되면 충족.

## 3. 접근/동기화 규칙 (모드별)

| 모드 | GitHub (common) | GHES (company) | AI 자동 태깅 |
|------|-----------------|----------------|--------------|
| `internal` | **pull only** (upstream, push 절대 금지) | **read/write** | local LLM 있는 1대만 |
| `external` | read/write | 접속 불가 | Ollama 로컬 |
| `home` | read/write | 접속 불가 | 없음 (재태깅은 다른 PC에서) |

- `bookmarks-common` (GitHub) = 5대 전부 공유하는 공용 북마크.
- `bookmarks-company` (GHES) = `internal` 모드에서만 존재하는 사내 전용 북마크.
- 코드상 분기: `is_work = (mode == "internal")`
  - `internal` → common 은 pull-only, company 활성.
  - `external`/`home` → common push/pull, company 비활성. (둘은 sync 동작 동일,
    차이는 AI 태깅 가능 여부뿐.)

## 4. ObsidianVault-PARA 디렉토리 구조

모든 PC 에서 동일하게 생성한다. PARA + Inbox + Company.

명명 컨벤션: **하이픈·단수** (`10-Project` 형태)로 통일한다 (확정).

```
ObsidianVault-PARA/
  .obsidian/              # Obsidian 설정 (Dataview 플러그인 포함)
  10-Project/
  20-Area/
  30-Resource/
    Bookmarks/            # 공용 북마크 (전 PC 공유) = bookmarks-common 클론
      <id>.md ...         #   평면 저장
    Bookmarks Dashboard.md  # Dataview 대시보드 (Bookmarks 폴더 밖 = git 제외)
  40-Archive/
  80-Company/             # 사내 전용 (internal 모드에서만, GHES)
    Bookmarks/            # 사내 북마크 = bookmarks-company 클론 (GHES)
    docs/                 # 사내 문서/노트 (사내 vault repo, GHES)
  99-Inbox/               # 미분류 임시 보관 → 분류 후 이동
```

### 4.1 sync 매핑 (목표 구조)

`vault_root` 를 **vault 최상위**로 두고 각 repo 가 PARA 경로에 클론되게 한다:

```yaml
vault_root: /mnt/c/Users/<winuser>/Documents/ObsidianVault-PARA
repos:
  common:  { path: 30-Resource/Bookmarks, remote: <GitHub bookmarks-common>, pull: true }
  company: { path: 80-Company/Bookmarks,  remote: <GHES bookmarks-company>,  pull: true }
```

- 공용 북마크 → `30-Resource/Bookmarks/` (Resource = reference 자료)
- 사내 북마크 → `80-Company/Bookmarks/` (명확한 분리)
- 대시보드 노트는 `30-Resource/Bookmarks Dashboard.md` (Bookmarks 폴더 밖이라 git push 제외)

### 4.2 사용 시나리오 (Usage Examples)

"파일을 어디에 두면 어디로 동기화되는가"의 규칙. (공용 노트 동기화 메커니즘은 §6 참조)

| # | 동작 | 저장 위치 | 동기화 범위 | 메커니즘 |
|---|------|-----------|-------------|----------|
| 1 | Home 에서 `20-Area/finance/xxx.md` 생성 | `20-Area/finance/` | Internal · External 로 전파 | 공용 노트 동기화(§6) |
| 2 | External 에서 `20-Area/health/xxx.md` 생성 | `20-Area/health/` | Internal · Home 로 전파 | 공용 노트 동기화(§6) |
| 3 | External 에서 karakeep 으로 URL 등록 | `30-Resource/Bookmarks/<id>.md` | 5 PC 전부 (Internal·Home 포함) | karakeep-sync + `bookmarks-common`(§3) — **동작 확인됨** |
| 4 | Internal 에서 북마크 저장 | `80-Company/Bookmarks/<id>.md` | **Internal PC 끼리만** | karakeep-sync + `bookmarks-company`(GHES) |
| 5 | Internal 에서 사내 문서 작성 | `80-Company/docs/…` | **Internal PC 끼리만** | 사내 vault repo(GHES) |
| 6 | Internal 에서 사내 문서를 `80-Company/` **밖**에 저장 | (금지) | — | **에러 — §4.3 가드레일** |

핵심:

- **공용(common)** 노트·북마크는 5 PC 전부 공유. 단 **internal 은 GitHub push 불가**
  (pull-only)이므로, 공용 콘텐츠의 *생성·수정은 external·home 에서* 하고 internal 은 받기만 한다.
  (그래서 예시 1·2 의 생성 주체가 Home·External 이다.)
- **사내(company)** 콘텐츠는 `80-Company/` 안에서만 만들고, internal PC 끼리 **GHES** 로만 공유한다.
  external·home 에는 절대 내려가지 않는다.

### 4.3 사내 콘텐츠 가드레일 (`80-Company/` 경계)

- 사내 전용 문서·북마크는 **반드시 `80-Company/` 하위**에만 저장한다.
- `80-Company/` 밖(예: `20-Area/`, `30-Resource/`)에 사내 콘텐츠를 저장하는 것은
  **규칙 위반(에러)**이다 — 공용 repo(GitHub)로 새어나갈 수 있기 때문.
- 경계가 지켜지는 이유(다층 방어):
  1. `80-Company/` 는 공용 `obsidian-para`(GitHub)에서 `.gitignore` 로 제외 → 공용 push 에 안 실림.
  2. internal 은 GitHub push 자체가 불가(pull-only) → 공용 영역에 잘못 둔 사내 글도 밖으로 못 나감.
  3. 전체-vault 동기화(§6)의 공용 공유는 `80-Company/` 를 통째 제외.
- **능동적 차단(구현됨)** — 위 구조적 방어에 더해 두 지점에서 능동 거부한다:
  1. **북마크(karakeep-sync 라우팅)**: `company_lists`(예: `Company`)에 속한 북마크는
     `is_company` repo(`80-Company/Bookmarks`, GHES)로만 export 된다. per-repo `exclude_lists`
     설정이 누락돼도 공용 GitHub repo 로 새지 않으며, 사내 repo 가 없는 PC 에선 보류하고 경고한다.
     (`sync/karakeep_sync/cli.py` `_repo_accepts_bookmark` 가드레일)
  2. **노트/문서(pre-sync 가드)** — `scripts/vault-sync.sh` 가 동기화 전 두 가지를 검사한다:
     - **작성 경계(주 방어)**: `internal` 모드에서 공용 작업트리에 `80-Company/`·북마크·
       `.obsidian` *밖*의 변경/신규 파일이 있으면 = 사내 문서를 잘못된 폴더에 둔 것으로 보고
       **에러로 거부**한다. internal 은 공용 repo pull-only + 작성은 `80-Company/`(GHES)에만
       하므로, 그 밖의 변경은 정의상 오배치다(경로+모드만으로 판정 → 태그·내용 추측 불필요,
       오탐 0). 의도된 변경이면 `--allow-outside`(또는 `ALLOW_OUTSIDE=1`)로 우회.
     - **추적 방어(보조)**: 공용 `obsidian-para` 에 `80-Company/` 가 추적(tracked)되고 있으면
       (`.gitignore` 누락 등) 동기화를 거부한다 — 폴더 통째 유출 방지.

## 5. 신규 PC 부트스트랩 (목표: 1-스크립트)

`scripts/bootstrap.sh` (repo 에 포함 → karakeep clone 하면 어디서나 실행 가능).
동작 순서:

1. Windows 사용자/홈 탐지 → `/mnt/c/Users/<winuser>/Documents/ObsidianVault-PARA` 확정.
2. `~/.dotfiles-setup-mode` 읽어 모드 결정 (internal/external/home).
3. **Windows vault 자동 생성**: PARA 골격 폴더 + `.obsidian/`(Dataview 플러그인
   다운로드·활성화) + `Bookmarks Dashboard.md`. ← 사용자 #2 필수 요구.
4. `uv sync` (sync/ 에 `.venv` + 의존성·dev 그룹 설치).
5. `config.yaml` 을 템플릿에서 생성 (탐지한 vault 경로 + 모드별 repos).
6. `.env` 를 `.env.example` 에서 만들고 비밀값(API key/PAT) 입력 안내.
7. 모드별 `docker-compose.override.yml` 생성:
   - `external` → Ollama(`host.docker.internal`) + 사내 CA(해당 시).
   - `internal`(LLM PC) → 사내 LLM URL + 사내 CA.
   - `home` → AI 없음, CA 없음.
8. `docker compose up -d` → `karakeep-sync init` (모드별 repo 클론).

### 경계(스코프)

- 부트스트랩은 **북마크 파이프라인 + vault 골격**만 만든다.
- vault 의 실제 **노트 본문** 동기화(전 PC 공유)는 git(`obsidian-para`) → **§6** ·
  `scripts/vault-sync.sh`. 북마크 폴더는 submodule/별도 repo 로 분리해 중첩 `.git` 충돌을 피한다.

## 6. 전체 vault 노트 동기화 (북마크 폴더 제외)

북마크는 karakeep-sync 의 git(`bookmarks-common`/`bookmarks-company`)으로 이미
PC 간 공유되지만, 그 외 일반 노트(`10-Project`/`20-Area`/`30-Resource` 등)는
공유 메커니즘이 없었다. 5-PC 가 동일 정보를 공유하려면 전체 vault 동기화가 필요하다.

### 6.1 선정: git (`obsidian-para`) — Syncthing 폐기

노트 동기화는 **git(`obsidian-para`)** 으로 한다. (이전 Syncthing 안은 폐기 — 운영 결정)

| 옵션 | 채택 | 이유 |
|------|------|------|
| **git (`obsidian-para`)** | ✅ | 이미 GitHub/GHES·karakeep PAT 인프라 재사용, 버전관리·이력, **별도 remote(GitHub vs GHES)로 scope 분리 강제**, `scripts/vault-sync.sh` 로 모드별 자동화 |
| Syncthing | ✗ | 별도 데몬·디바이스 페어링(머신별 비밀) 필요, 버전 이력 없음, git 인프라 중복 |
| Obsidian Sync | ✗ | 유료·외부 클라우드 경유 → `internal` 거버넌스 위험 |
| OneDrive/Dropbox | ✗ | `.git` churn·충돌 위험, 사내 노트 외부 유출 |

> 트레이드오프: git 은 **internal 이 공용(GitHub)에 push 불가(pull-only)**. 따라서 공용
> 노트의 *생성·수정은 external·home 에서* 하고 internal 은 받기만 한다(§4.2). internal 의
> 쓰기는 사내 영역(`80-Company/`, GHES)에만 허용된다.

### 6.2 두 repo 로 scope 분리

| 도메인 | repo | vault 내 위치 | internal | external/home |
|--------|------|---------------|----------|---------------|
| 공용 노트 | `obsidian-para` (GitHub) | vault 최상위 | **pull-only** | push/pull |
| 사내 노트 | `obsidian-para` (GHES) | `80-Company/` | push/pull | 접속 불가 |

- 공용: vault 최상위 자체가 GitHub `obsidian-para`. `80-Company/` 는 여기서 `.gitignore` 로 제외 → 공용 repo 로 사내 콘텐츠가 안 새어나감(§4.3).
- 사내: `80-Company/` 가 GHES `obsidian-para` 클론. **internal PC 끼리만** push/pull, external·home 엔 존재하지 않음.
- 자동화: `scripts/vault-sync.sh` 가 `~/.dotfiles-setup-mode` 를 읽어 clone/pull + internal push 차단을 적용한다 (상세 [scripts/README.md](../scripts/README.md)).

### 6.3 중첩 git(북마크 폴더) 처리

북마크 폴더는 karakeep-sync 가 30분마다 commit/pull 하는 **별도 `.git`** 이라, 노트 repo
안에서 중첩 repo 충돌을 피해야 한다:

- `30-Resource/Bookmarks` (= `bookmarks-common`) → GitHub `obsidian-para` 의 **submodule**.
  cron 이 HEAD 를 올려도 internal 은 pull-only 라 gitlink churn 이 무해하다. external/home 은
  필요 시에만 gitlink 를 갱신(또는 무시).
- `80-Company/Bookmarks` (= `bookmarks-company`, GHES) → GHES `obsidian-para` 안에서
  submodule 또는 gitignore + 별도 클론으로 둔다.

### 6.4 검증 절차

1. external 에서 `20-Area/health/x.md` 생성 → push → internal·home 에서 pull → 보임.
2. internal 에서 공용 노트 push 시도 → **차단(pull-only)** 확인.
3. internal 에서 `80-Company/docs/y.md` 생성 → GHES push → 다른 internal PC 에서 pull → 보임.
   동시에 external·home 에는 **나타나지 않음** 확인.
4. 북마크 무충돌: 30분 cron 1회 후 `30-Resource/Bookmarks` 의 `git status` 가 깨끗한지 확인.
