# 다음 세션 작업 목록

## 현재 상태

- Karakeep Docker 실행 중 → http://localhost:3001
- karakeep-sync Python 패키지 구현 완료 (25개 테스트 통과)
- GitHub repo: https://github.com/dEitY719/karakeep (push 완료)
- Obsidian vault 폴더 구조 생성 완료 → `~/obsidian-vault/`

## 남은 작업

### 1. Karakeep 초기 설정 (수동)

브라우저에서 http://localhost:3001 열기:

1. 관리자 계정 생성
2. Settings → API Keys → API key 발급
3. `.env` 파일에 입력:
   ```
   KARAKEEP_API_KEY=발급받은키
   ```
4. 브라우저 Extension 설치 (Chrome/Edge)

### 2. .env 파일 완성 (수동)

`~/apps/karakeep/.env` 파일에 아래 값 입력:

```bash
GITHUB_PAT=ghp_xxxx          # GitHub → Settings → Developer settings → Personal access tokens (repo 권한)
GHES_PAT=ghes_xxxx           # 사내 GHES에서 발급 (회사 PC에서만 필요)
GHES_HOST=ghes.실제호스트명    # 실제 사내 GHES 호스트명으로 변경
```

### 3. GitHub bookmarks-common repo 생성 (수동)

```bash
gh repo create dEitY719/bookmarks-common --private
```

### 4. karakeep-sync 초기화

```bash
cd ~/apps/karakeep/sync
cp config.yaml.example config.yaml
# config.yaml 편집 (vault_root, PAT 환경변수 확인)

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

karakeep-sync init    # git clone + cron 등록
karakeep-sync status  # 동기화 대기 북마크 수 확인
karakeep-sync auto    # 첫 번째 전체 sync
```

### 5. 브라우저 북마크 import (선택)

Karakeep 웹 UI → Import → 브라우저 북마크 HTML 파일 업로드

### 6. 회사 PC 설정 (나중에)

`~/.dotfiles-setup-mode` 값이 `internal`인 PC에서:
- `GHES_PAT`, `GHES_HOST` 추가 설정
- `karakeep-sync init` 실행 시 Company(GHES) repo 자동 클론

## 파일 위치 참고

| 파일 | 설명 |
|------|------|
| `~/apps/karakeep/.env` | API key, PAT 보관 (gitignore) |
| `~/apps/karakeep/sync/config.yaml` | sync 설정 (gitignore) |
| `~/apps/karakeep/sync/sync-state.json` | sync 상태 추적 (자동 생성) |
| `~/apps/karakeep/logs/cron.log` | cron 실행 로그 |
| `~/obsidian-vault/10_Bookmarks/Common/` | 공통 북마크 git repo |
| `~/obsidian-vault/10_Bookmarks/Company/` | 사내 북마크 git repo (회사 PC만) |

## 설계 문서

- 설계: `docs/superpowers/specs/2026-06-12-karakeep-sync-design.md`
- 구현 계획: `docs/superpowers/plans/2026-06-12-karakeep-sync.md`
