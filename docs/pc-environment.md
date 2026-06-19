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
- vault 의 실제 **노트 본문** 동기화(전 PC 공유)는 별도 메커니즘
  (Obsidian Sync / Syncthing 등). 북마크 폴더 안의 `.git` 과 충돌하지 않도록
  전체-vault 동기화에서 북마크 폴더는 제외할 것.
