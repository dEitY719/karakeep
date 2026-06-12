# Karakeep Sync System Design

## Overview

개인 북마크 관리 시스템. Karakeep(로컬 캡처) → Obsidian Markdown(SSOT) → Git(PC 간 동기화) 파이프라인.

- 집 PC 2대 + 회사 PC 2대, 총 4대 운영
- 공통 북마크(GitHub) / 사내 북마크(GHES) 2개 repo 분리
- `~/.dotfiles-setup-mode` 값으로 PC 타입 자동 감지 (`internal` = 회사, 그 외 = 집)

---

## Architecture

```
집 PC (2대)
├── Karakeep (Docker, localhost:3000)
├── karakeep-sync [mode: home]
│     ├── push → 10_Bookmarks/Common/ → GitHub
│     └── pull ← GitHub
└── Obsidian Vault/10_Bookmarks/Common/  (git root → GitHub)

회사 PC (2대)
├── Karakeep (Docker, localhost:3000)
├── karakeep-sync [mode: work]
│     ├── push → 10_Bookmarks/Company/ → GHES
│     ├── pull ← GHES
│     └── pull ← GitHub (read-only)
└── Obsidian Vault/
      ├── 10_Bookmarks/Common/   (git root → GitHub, pull only)
      └── 10_Bookmarks/Company/  (git root → GHES)
```

**PC 타입 감지:**
```python
mode_raw = Path("~/.dotfiles-setup-mode").expanduser().read_text().strip()
is_work = (mode_raw == "internal")
```

**새 북마크 라우팅:**
- 집 PC: 새 북마크 → Common(GitHub)
- 회사 PC: 새 북마크 → Company(GHES)
- 회사 PC에서 GitHub pull로 온 북마크 → `imported: true` 표시 → push 제외

---

## Data Model: Markdown 포맷

파일명: `{karakeep-id}.md`

```markdown
---
id: abc123
url: https://example.com/some-article
title: "Some Article Title"
tags: [topic/python, area/work]
created: 2024-01-15T10:30:00+09:00
updated: 2024-01-15T12:00:00+09:00
source: karakeep
---

유저 노트 내용
```

**`sync-state.json` 구조:**
```json
{
  "abc123": {
    "updated": "2024-01-15T12:00:00+09:00",
    "repo": "common",
    "imported": true
  },
  "xyz789": {
    "updated": "2024-01-15T09:00:00+09:00",
    "repo": "company",
    "imported": false
  }
}
```

---

## karakeep-sync CLI

**위치:** `~/apps/karakeep/sync/`

**프로젝트 구조:**
```
sync/
├── pyproject.toml
├── config.yaml
├── sync-state.json          # 자동 생성/관리
├── logs/
└── karakeep_sync/
    ├── cli.py               # Click CLI 진입점
    ├── config.py            # config.yaml 로드 + mode 감지
    ├── karakeep.py          # Karakeep REST API 클라이언트
    ├── markdown.py          # bookmark ↔ Markdown 변환
    ├── git_ops.py           # git pull/commit/push (HTTPS + PAT)
    └── state.py             # sync-state.json 읽기/쓰기
```

**명령어:**
```bash
karakeep-sync init     # git clone, cron 등록
karakeep-sync push     # 새 북마크 → MD → git push
karakeep-sync pull     # git pull → MD → Karakeep import
karakeep-sync auto     # pull 후 push (cron 전용)
karakeep-sync status   # 미동기 북마크 수 출력
```

**`config.yaml`:**
```yaml
karakeep:
  url: http://localhost:3000
  api_key: ${KARAKEEP_API_KEY}

vault_root: ~/obsidian-vault/10_Bookmarks

repos:
  common:
    path: Common
    remote: https://${GITHUB_PAT}@github.com/dEitY719/bookmarks-common.git
  company:
    path: Company
    remote: https://${GHES_PAT}@${GHES_HOST}/dEitY719/bookmarks-company.git  # GHES_HOST: 실제 사내 GHES 호스트명

logs:
  dir: ~/apps/karakeep/logs
  retention_days: 30
```

**`.env`:**
```bash
KARAKEEP_API_KEY=...
GITHUB_PAT=ghp_xxxx
GHES_PAT=ghes_xxxx    # internal mode일 때만 사용
```

**cron:**
```
*/30 * * * * /path/to/karakeep-sync auto >> ~/apps/karakeep/logs/cron.log 2>&1
```

---

## Push/Pull 알고리즘

**`push` 흐름:**
1. Karakeep API → 전체 북마크 목록
2. 각 북마크:
   - sync-state에 없음 → MD 파일 생성
   - sync-state의 `updated` < Karakeep의 `updated` → MD 파일 갱신
   - sync-state의 `updated` == Karakeep의 `updated` → skip
3. 회사 PC: `imported: true` 항목 제외
4. 변경 파일만 git add → commit → push
5. sync-state.json 업데이트

**`pull` 흐름:**
1. git pull (common 항상 / company는 internal mode만)
2. `git diff HEAD~1..HEAD`로 변경된 MD 파일 목록 추출
3. 각 MD:
   - Karakeep에 해당 URL 없음 → API로 생성
   - MD의 `updated` > Karakeep의 `updated` → API로 업데이트 (last write wins)
   - MD의 `updated` ≤ Karakeep의 `updated` → skip
4. sync-state.json에 `imported: true` 표시

**`auto` 흐름:** `pull` → `push` (외부 변경 먼저 받고, 로컬 변경 내보냄)

**충돌 전략:** Last write wins (`updated` timestamp 기준)

---

## Docker Compose

**`~/apps/karakeep/` 구조:**
```
~/apps/karakeep/
├── docker-compose.yml
├── .env                     # gitignore
├── data/                    # Karakeep 데이터
├── logs/                    # sync 로그
├── sync/                    # karakeep-sync 패키지
└── README.md
```

**`docker-compose.yml`:**
```yaml
services:
  karakeep:
    image: ghcr.io/karakeep-app/karakeep:release
    ports:
      - "3000:3000"
    volumes:
      - ./data:/data
    env_file: .env
    restart: unless-stopped
```

---

## Obsidian Vault 구조

```
~/obsidian-vault/
├── .obsidian/
├── 00_Inbox/
├── 10_Bookmarks/
│   ├── Common/              # git repo → GitHub
│   └── Company/             # git repo → GHES (회사 PC만)
├── 20_Notes/
└── 90_Archive/
```

Vault 루트 `.gitignore`:
```
10_Bookmarks/Common/
10_Bookmarks/Company/
.obsidian/workspace.json
.obsidian/workspace-mobile.json
```

---

## PC 추가 시 체크리스트

```
1. docker compose up -d
2. Karakeep 웹 → 계정 생성 + API key 발급
3. .env 파일 작성 (API key + PAT)
4. karakeep-sync init   → git clone + cron 등록
5. karakeep-sync pull   → 기존 북마크 Karakeep import
```

---

## 일상 운영

| 행동 | 방법 |
|------|------|
| 북마크 저장 | Karakeep 브라우저 Extension |
| 북마크 검색 | Obsidian (30분마다 자동 sync) |
| 긴급 sync | `karakeep-sync auto` |
| 상태 확인 | `karakeep-sync status` |
| 로그 확인 | `~/apps/karakeep/logs/cron.log` |

---

## 태그 체계 (권장)

```
area/work        area/personal
topic/python     topic/ai       topic/infra    topic/finance
status/read-later  status/reference  status/archive
source/blog      source/docs    source/company
```
