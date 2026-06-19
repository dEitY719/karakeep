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
  80-Company/             # 사내 전용 (internal 모드에서만)
    Bookmarks/            # bookmarks-company 클론
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

## 5. 신규 PC 부트스트랩 (목표: 1-스크립트)

`scripts/bootstrap.sh` (repo 에 포함 → karakeep clone 하면 어디서나 실행 가능).
동작 순서:

1. Windows 사용자/홈 탐지 → `/mnt/c/Users/<winuser>/Documents/ObsidianVault-PARA` 확정.
2. `~/.dotfiles-setup-mode` 읽어 모드 결정 (internal/external/home).
3. **Windows vault 자동 생성**: PARA 골격 폴더 + `.obsidian/`(Dataview 플러그인
   다운로드·활성화) + `Bookmarks Dashboard.md`. ← 사용자 #2 필수 요구.
4. Python venv + `pip install -e sync[dev]`.
5. `config.yaml` 을 템플릿에서 생성 (탐지한 vault 경로 + 모드별 repos).
6. `.env` 를 `.env.example` 에서 만들고 비밀값(API key/PAT) 입력 안내.
7. 모드별 `docker-compose.override.yml` 생성:
   - `external` → Ollama(`host.docker.internal`) + 사내 CA(해당 시).
   - `internal`(LLM PC) → 사내 LLM URL + 사내 CA.
   - `home` → AI 없음, CA 없음.
8. `docker compose up -d` → `karakeep-sync init` (모드별 repo 클론).

### 경계(스코프)

- 부트스트랩은 **북마크 파이프라인 + vault 골격**만 만든다.
- vault 의 실제 **노트 본문** 동기화(전 PC 공유)는 별도 메커니즘 → **§6** 참조.
  북마크 폴더 안의 `.git` 과 충돌하지 않도록 전체-vault 동기화에서 북마크 폴더는 제외한다.

## 6. 전체 vault 노트 동기화 (북마크 폴더 제외)

북마크는 karakeep-sync 의 git(`bookmarks-common`/`bookmarks-company`)으로 이미
PC 간 공유되지만, 그 외 일반 노트(`10-Project`/`20-Area`/`30-Resource` 등)는
공유 메커니즘이 없었다. 5-PC 가 동일 정보를 공유하려면 전체 vault 동기화가 필요하다.

### 6.1 선정: Syncthing (P2P, 무료, 클라우드 불필요)

| 옵션 | 채택 | 이유 |
|------|------|------|
| **Syncthing** | ✅ | 무료·P2P, 외부 클라우드 불필요(사내 데이터가 device↔device 메시 밖으로 안 나감), `.stignore` 로 폴더 제외, 디바이스별 공유 분리로 거버넌스 경계 강제 가능 |
| Obsidian Sync | △ | 쉽지만 유료, 외부 클라우드 경유 → `internal` 접속 제한·사내 노트 거버넌스 위험 |
| Git(전체 vault) | ✗ | 북마크 폴더의 중첩 `.git` → 서브모듈화 복잡, `internal` 은 GitHub push 불가(GHES 필요) |
| OneDrive/Dropbox | ✗ | `.git` churn·충돌 위험, 사내 노트 외부 유출 |

> 핵심 제약: 북마크 폴더(`30-Resource/Bookmarks`, `80-Company/Bookmarks`)는
> karakeep-sync 가 30분마다 commit/pull 하는 `.git` repo 다. 전체-vault 동기화가
> 이들을 함께 옮기면 **중첩 `.git` 충돌 + 지속 churn** 이 난다 → 반드시 제외한다.

### 6.2 두 개의 Syncthing 공유 (거버넌스 경계)

사내 노트(`80-Company`)가 외부로 새지 않도록 **공유를 둘로 분리**한다:

| 공유 | 루트 | 연결 대상 | `.stignore` 템플릿 | 제외 항목 |
|------|------|-----------|--------------------|-----------|
| **vault-notes** | vault 최상위 | **5-PC 전부** | `sync/stignore/vault-notes.stignore` | `30-Resource/Bookmarks`(공용 북마크 git), **`80-Company` 통째**, `.obsidian/workspace*`·cache |
| **vault-company** | `80-Company` | **internal PC 끼리만** | `sync/stignore/vault-company.stignore` | `Bookmarks`(사내 북마크 GHES git) |

- `vault-notes` 가 `80-Company` 를 통째로 제외하므로, 사내 노트는 전-PC 공유에
  **절대 올라가지 않는다**. external/home PC 에는 `vault-company` 공유를 **추가하지 않는다**
  → 사내 노트가 사내망 밖으로 나가지 않음을 물리적으로 보장.
- `80-Company` 는 `vault-notes` 안에 중첩되지만 위 제외 규칙으로 두 공유는 충돌하지 않는다
  (Syncthing 중첩 폴더는 외부 공유에서 ignore 되어 있으면 허용된다).

모드별 정리:

| 모드 | vault-notes | vault-company |
|------|-------------|---------------|
| `internal` | 참여 | **참여 (internal 끼리만)** |
| `external` | 참여 | **불참 (사내 노트 수신 금지)** |
| `home` | 참여 | **불참** |

### 6.3 부트스트랩 연동

`scripts/bootstrap.sh` 가 vault 골격 생성 단계에서 위 `.stignore` 템플릿을 배치한다:

- 전 모드: `sync/stignore/vault-notes.stignore` → `<vault>/.stignore`
- `internal` 모드만: `sync/stignore/vault-company.stignore` → `<vault>/80-Company/.stignore`

기존 `.stignore` 는 덮어쓰지 않는다(멱등). Syncthing **설치·디바이스 페어링·폴더
공유 추가**는 디바이스 ID 가 머신별 비밀이므로 스크립트가 자동화하지 않고
수동 단계로 안내한다(이 repo 는 토폴로지만 담는다 — 상단 주의 참고).

### 6.4 검증 절차 (최소 2-PC)

1. 두 PC 에 Syncthing 설치 → 서로 디바이스 추가.
2. 양쪽 `vault-notes` 공유 연결(루트=vault). `.stignore` 가 배치됐는지 확인.
3. 한 PC 에서 `10-Project` 에 노트 생성 → 다른 PC 로 전파 확인.
4. 북마크 무충돌 확인: 30분 cron 1회 경과 후 `30-Resource/Bookmarks` 의
   `git status` 가 깨끗하고, Syncthing 이 그 폴더를 건드리지 않았는지 확인
   (`.stignore` 매칭 → Out of Sync 항목 없음).
5. (internal 2대 한정) `vault-company` 공유 연결 → `80-Company` 노트 전파 확인,
   동시에 external/home PC 에는 사내 노트가 **나타나지 않음** 확인.
