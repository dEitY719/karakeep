# scripts

운영 스크립트 모음.

| 스크립트 | 용도 |
|----------|------|
| `bootstrap.sh` | 신규 PC 부트스트랩 (karakeep 파이프라인 + vault 골격 생성) |
| `check.sh` | 환경/설치 상태 점검 |
| `vault-sync.sh` | **ObsidianVault-PARA 전체 git 동기화** (모드 인지 · 경로 자동탐지) |

---

## vault-sync.sh — Obsidian PARA vault 동기화

karakeep-sync 가 *북마크 폴더*를 다루는 것과 별개로, **vault 전체**(일반 노트 +
`.obsidian` 설정 + `30-Resource/Bookmarks` 서브모듈)를 `obsidian-para` git repo 로
PC 간 동기화한다.

### 원칙 ([docs/pc-environment.md](../docs/pc-environment.md) SSOT)

| 모드 | obsidian-para (common, GitHub) | 80-Company (company, GHES) |
|------|--------------------------------|----------------------------|
| `internal` | **pull-only** (push 차단) | clone/pull **read/write** |
| `external` | push / pull | 비활성 |
| `home` | push / pull | 비활성 |

> 사내 PC는 bookmarks 와 **동일 원칙**: GitHub(common)에서 **pull 만**, 쓰기는
> `80-Company`(GHES)에만. 스크립트가 internal 모드에서 obsidian-para 와 Bookmarks
> 서브모듈의 push URL 을 더미(`no-push://…`)로 바꿔 실수 push 를 물리적으로 막는다.

### 동작 (멱등)

1. 모드 결정 — `~/.dotfiles-setup-mode` (`internal` / `external` / `home`).
2. **Windows vault 경로 자동 탐지** — `cmd.exe %USERPROFILE%` →
   `/mnt/c/Users/<winuser>/Documents/ObsidianVault-PARA`.
   사용자명을 하드코딩하지 않으므로 PC(`bwyoon` / `byoungwoo.yoon` / `msi-labtop`)마다
   그대로 동작. 필요하면 `VAULT_ROOT` 로 직접 지정.
3. 시크릿 로드 (`~/.config/obsidian-para/secrets.env`) — 없으면 템플릿 생성 후 종료.
4. (있으면) 사내 CA 등록 → obsidian-para clone(최초) 또는 `pull --ff-only`(이후).
5. 모드별 push 정책 적용 (internal = 차단).
6. Bookmarks 서브모듈 init/update — 토큰은 **로컬 `.git/config`** 에만,
   `.gitmodules` 는 토큰 없는 clean URL 유지.
7. internal 전용 — `80-Company/` 를 GHES `obsidian-para` 에서 clone/pull (**사내 문서
   read/write**). 80-Company/ 자체가 GHES 클론이고 그 안의 `Bookmarks/` 는 별도 클론(8).
8. internal 전용 — `80-Company/Bookmarks` 를 GHES `bookmarks-company` 에서 clone/pull
   (read/write).

### 사전 준비

- WSL + Windows, `git`.
- private repo: `github.com/dEitY719/obsidian-para`, 서브모듈 `bookmarks-common`.
- **호스트당 PAT 1개**면 충분 (repo 마다 따로 만들 필요 없음). GitHub PAT 1개로
  obsidian-para + bookmarks-common 둘 다, GHES PAT 1개로 두 사내 repo 를 커버.
  fine-grained 면 해당 repo 들을 모두 선택하고 **Contents** 권한을 켠다 — internal 은
  `Read` 면 충분, external/home 은 `Read and write`.
  - ⚠️ **404 함정**: PAT 에 `Contents` 권한이 없으면 git 이 `403` 이 아니라
    `404 (repository not found)` 를 던진다. 반드시 `Contents` 를 켤 것.
- **(internal 전용 전제)** GHES `obsidian-para` 레포에 `Bookmarks/` 가 든 `.gitignore`
  를 **먼저 커밋**해 둘 것. 사내 북마크(`80-Company/Bookmarks`)가 중첩 클론으로 들어가는데,
  GHES obsidian-para 가 이를 ignore 하지 않으면 `vault-sync.sh` 가 §6.3 가드에서 **거부**한다
  (최초 셋업이 7단계에서 멈춤 → 8단계 사내 북마크까지 진행 안 됨). 유출/churn 방지.

### 시크릿 설정 (최초 1회)

처음 실행하면 `~/.config/obsidian-para/secrets.env`(권한 600) 템플릿이 생성된다.
값을 채운다:

```bash
# GitHub(공용) — PAT 한 개로 obsidian-para + bookmarks-common 둘 다 접근.
# fine-grained 면 두 repo 를 모두 선택 (Contents: internal=Read, external/home=Read/Write).
GITHUB_PAT="github_pat_…"

# internal 모드에서만 (셋 다 필수 — 없으면 실행 거부):
# 사내 GHES 자격증명 — PAT 한 개로 obsidian-para + bookmarks-company 둘 다.
# 스크립트가 아래 3개로 두 GHES remote URL 을 자동 조립한다 (karakeep-sync .env 의 GHES_* 와 동일 값).
GHES_PAT="…"
GHES_HOST="ghes.example.com"
GHES_OWNER="my-org"
CORP_CA="/path/to/corp-root-ca.pem"   # 사내 TLS 재서명 환경이면 (아니면 비움)
```

> **키 발급은 호스트당 1개면 충분** — repo 마다 따로 만들 필요 없다. GitHub PAT 1개
> (두 repo 선택) + GHES PAT 1개(두 repo 권한). GHES 값은 karakeep-sync `.env` 의
> `GHES_PAT`/`GHES_HOST`/`GHES_OWNER` 와 같은 값을 그대로 쓰면 된다.
>
> 컴포넌트 대신 토큰 포함 전체 URL 을 직접 지정하려면 `OBSIDIAN_PARA_COMPANY_REMOTE` /
> `BOOKMARKS_COMPANY_REMOTE` 를 채운다(있으면 우선). 구 변수 `OBSIDIAN_PARA_PAT` /
> `BOOKMARKS_COMMON_PAT` 도 계속 지원되므로 기존 secrets.env 는 그대로 둬도 동작한다.

> 이 파일은 git 에 절대 올리지 않는다(개인 PC 로컬 전용). 토큰은 여기 + 로컬
> `.git/config` 에만 존재하고, 커밋되는 `.gitmodules` 는 항상 clean 하다.

### Internal PC 가이드 (단계별)

```bash
# 1) 모드 지정 (한 번만)
echo internal > ~/.dotfiles-setup-mode

# 2) 최초 실행 → 시크릿 템플릿 생성됨 (여기서 멈춤)
~/para/project/karakeep/scripts/vault-sync.sh
#    → ~/.config/obsidian-para/secrets.env 에 PAT·회사 remote·CA 입력

# 3) 다시 실행 → clone + 서브모듈 + 80-Company(GHES) 셋업
~/para/project/karakeep/scripts/vault-sync.sh

# 4) 이후 일상 동기화 = 같은 명령 (pull-only)
~/para/project/karakeep/scripts/vault-sync.sh
```

실행 후 obsidian-para 의 push 가 막혔는지 확인:

```bash
git -C "$(wslpath "$(cmd.exe /c 'echo %USERPROFILE%' | tr -d '\r')")/Documents/ObsidianVault-PARA" remote -v
# push 줄이 no-push://internal-is-pull-only 이면 정상 (pull-only)
```

### External / Home PC

```bash
echo external > ~/.dotfiles-setup-mode   # 또는 home
~/para/project/karakeep/scripts/vault-sync.sh   # push/pull 모두 허용, company 비활성
```

### Obsidian Git 플러그인과 함께

최초 셋업(clone·서브모듈·토큰·CA)은 이 스크립트로 하고, 이후 단순 동기화는
Obsidian 의 *Obsidian Git* 플러그인 "Pull"/"Push"로 대체해도 된다. 단 internal 에서는
플러그인 Push 도 차단되도록 push URL 을 더미로 둔 상태이므로 Pull 만 사용한다.

### 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-------------|
| `Recv failure: Connection reset by peer` | 사내 방화벽이 인증 없는 요청을 리셋. 스크립트가 토큰을 URL 에 실어 보내고 3회 재시도함 — 단순 재실행으로 대부분 해결. |
| `SSL certificate problem` | 사내 TLS 재서명. `CORP_CA` 에 사내 루트 CA 경로 지정. |
| `404 repository not found` | PAT 에 `Contents` 권한 없음 → 재발급. |
| internal 에서 push 가 실패 | **정상**(pull-only). 쓰기는 `80-Company`(GHES)에만. |
| 서브모듈이 비어 있음 | `BOOKMARKS_COMMON_PAT` 확인 후 재실행. (karakeep-sync 가 따로 관리 중이면 무시 가능) |
| `GHES obsidian-para 의 .gitignore 에 'Bookmarks/' 가 없습니다` | GHES `obsidian-para` repo 가 중첩 북마크 클론(`80-Company/Bookmarks`)을 ignore 하지 않음 → 유출/churn 방지를 위한 가드(§6.3). 해당 repo 의 `.gitignore` 에 `Bookmarks/` 추가·커밋·push 후 재실행. 이미 추적 중이면 `git rm -r --cached Bookmarks` 도 함께. |

### 참고

- 회사 노트(`80-Company`)는 공용 `obsidian-para`(GitHub)에서 `.gitignore` 로 제외되어
  GitHub 로 새지 않는다. 대신 GHES 의 **두 repo** 로 internal PC 끼리만 공유된다:
  `80-Company/` 자체는 GHES `obsidian-para`(사내 문서), 그 안의 `Bookmarks/` 는 GHES
  `bookmarks-company`(사내 북마크). external/home 에는 존재하지 않는다.
- 전체 vault 노트의 PC 간 공유는 git(`obsidian-para`) 기반이며 `vault-sync.sh` 가 자동화한다.
  자세한 내용은 [docs/pc-environment.md](../docs/pc-environment.md) §6 참조.
