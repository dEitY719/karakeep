# 요구사항
- 나만의 북마크 관리를 하고 싶고, 집/회사 4개의 PC에서 동기화해서 사용해야함.

## 1단계: 목표 구조 확정

```text
Karakeep = 북마크 원본 저장소
Obsidian = Markdown 백업/검색/지식화
Git = Obsidian Vault 버전관리/PC 간 동기화
```

Karakeep은 Docker 설치가 공식 지원되고, `.env` 변경 후에는 `docker compose up`을 다시 실행해야 한다. ([Karakeep Docs][1])
Obsidian 쪽은 Karakeep Sync 플러그인이 북마크를 지정 폴더에 Markdown 노트로 만들어준다. ([Karakeep Docs][2])

## 2단계: WSL에 Karakeep 설치

Claude/Codex에 줄 프롬프트:

```text
내 WSL Ubuntu 환경에 Karakeep을 Docker Compose로 설치하는 작업을 도와줘.

조건:
- 작업 폴더: ~/apps/karakeep
- docker compose 사용
- .env 파일 분리
- 데이터는 Docker volume 또는 ./data 하위에 영구 저장
- 포트는 기본 3000 사용
- 나중에 Caddy/Nginx reverse proxy 붙일 수 있게 구조화
- 설치 후 실행, 중지, 업데이트 명령을 README.md에 정리

공식 문서를 기준으로 docker-compose.yml과 .env 예시를 만들어줘.
```

실행 후 확인:

```bash
cd ~/apps/karakeep
docker compose up -d
docker compose logs -f
```

브라우저에서:

```text
http://localhost:3000
```

## 3단계: Karakeep 초기 세팅

할 일:

```text
1. 관리자 계정 생성
2. Chrome/Edge Extension 설치
3. 기존 브라우저 북마크 export
4. Karakeep으로 import
5. 기본 태그 체계 만들기
```

추천 태그 체계:

```text
area/work
area/personal
topic/python
topic/ai
topic/infra
topic/finance
status/read-later
status/reference
status/archive
source/company
source/blog
source/docs
```

## 4단계: Obsidian Vault 준비

추천 폴더:

```text
Obsidian Vault/
├── 00_Inbox/
├── 10_Bookmarks/
│   ├── Karakeep/
│   └── Attachments/
├── 20_Notes/
├── 90_Archive/
└── _templates/
```

## 5단계: Obsidian에 Karakeep Sync 설치

Obsidian Community Plugin에서 **Karakeep/Hoarder Sync** 설치.

설정값 추천:

```text
API Endpoint:
http://localhost:3000/api/v1

Sync folder:
10_Bookmarks/Karakeep

Attachments folder:
10_Bookmarks/Attachments

Sync interval:
60

Update existing files:
처음엔 false

Exclude archived:
true

Sync notes to Karakeep:
true

Sync deletions:
처음엔 false
```

플러그인은 API key, API endpoint, Sync folder, Attachments folder, Sync interval 등을 설정할 수 있다. ([Obsidian Community][3])

## 6단계: Git으로 Obsidian Vault 관리

Vault 폴더에서:

```bash
git init
git add .
git commit -m "Initial Obsidian bookmark vault"
```

`.gitignore` 추천:

```gitignore
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.trash/
.DS_Store
Thumbs.db
```

사설 Git 서버, GitHub private repo, Gitea 중 하나를 사용하면 된다.

## 7단계: 4대 PC 사용 방식

각 PC에서:

```bash
git clone <your-private-repo> "Obsidian Vault"
```

운영 규칙:

```text
북마크 저장: Karakeep
북마크 읽기/검색/정리: Obsidian
동기화/백업: Git
```

PC마다 Karakeep 서버에 접속만 되면 된다.

## 8단계: 나중에 자동화할 것

Claude/Codex용 프롬프트:

```text
Karakeep API와 Obsidian Markdown 파일을 이용해서 북마크 정리 자동화 스크립트를 만들고 싶다.

요구사항:
- Python 사용
- Karakeep API에서 북마크 목록 조회
- URL, title, tags, createdAt 기준으로 Markdown 생성
- 중복 URL 감지
- 태그 없는 북마크를 CSV로 리포트
- Obsidian frontmatter 형식 유지
- dry-run 옵션 제공
- 실행 결과를 logs/에 저장

프로젝트 구조와 코드를 작성해줘.
```

## 최종 추천 작업 순서

```text
1. Karakeep Docker 설치
2. 브라우저 북마크 import
3. Karakeep Extension으로 저장 습관 만들기
4. Obsidian Sync 연결
5. Git으로 Vault 백업
6. 1~2주 사용 후 태그 체계 정리
7. Python 자동화 추가
```

처음부터 완벽한 분류체계를 만들려고 하지 말고, **Karakeep에 다 넣고 → Obsidian에서 검색/정리 → Git으로 백업** 흐름을 먼저 안정화하는 게 좋다.

[1]: https://docs.karakeep.app/installation/docker/?utm_source=chatgpt.com "Docker | Karakeep Docs"
[2]: https://docs.karakeep.app/community/community-projects/?utm_source=chatgpt.com "Community Projects | Karakeep Docs"
[3]: https://community.obsidian.md/plugins/hoarder-sync?utm_source=chatgpt.com "Karakeep Sync - Obsidian Plugin"
