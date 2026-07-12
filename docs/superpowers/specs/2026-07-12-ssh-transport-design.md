---
status: approved
date: 2026-07-12
topic: git remote를 SSH로 전환 (PAT 발급 제거)
---

# SSH transport 전환 설계

## 문제

`scripts/bootstrap.sh`의 8/8 (init) 단계는 git remote가
`https://${GITHUB_PAT}@github.com/...`(공용) / `https://${GHES_PAT}@${GHES_HOST}/...`(사내)
형식이라 `.env`에 **GitHub PAT 발급·입력**을 요구한다. GitHub 웹에서 PAT를 새로 발급받는
과정이 번거롭다. 사용자의 `~/.ssh/config`에는 이미 `github.com`(ssh.github.com:443 우회 포함)과
`github.samsungds.net`(사내 GHES)이 `id_ed25519`로 설정돼 있고, 키에 passphrase가 없어
**cron 무인 push도 안전**하다. 따라서 SSH로 전환하면 PAT가 아예 불필요해진다.

## 접근: auto-detect + PAT fallback (승인됨)

bootstrap이 host별로 SSH 인증을 1회 프로브해 transport를 결정하고, 런타임/cron은
프로브하지 않는다(결정적). SSH가 안 되는 PC는 기존 PAT 경로로 자동 폴백한다.

### 핵심 — remote "재작성" (config.yaml 스키마 불변)

config.yaml의 canonical remote는 HTTPS 형식 그대로 두고, transport가 `ssh`일 때
**로드 시점에 URL을 변환**한다:

```
https://${GITHUB_PAT}@github.com/dEitY719/bookmarks-common.git
  → _to_ssh() →  git@github.com:dEitY719/bookmarks-common.git

https://${GHES_PAT}@${GHES_HOST}/${GHES_OWNER}/bookmarks-company.git
  → _to_ssh() →  git@${GHES_HOST}:${GHES_OWNER}/bookmarks-company.git   (그 뒤 _expand)
```

- config.yaml 스키마 불변 → 이미 존재하는(bootstrap이 유지한) PC의 config.yaml이 수정 없이 SSH 동작
- SSH 형식은 자격증명(`${GITHUB_PAT}@`)을 통째로 버리므로 PAT 미설정 시 `_expand`가
  raise하던 문제도 자동 해소. GHES는 `${GHES_HOST}`/`${GHES_OWNER}`만 남아 정상 확장
- SSOT #38 유지 — 컴포넌트는 계속 `.env`에

### 단일 knob — `.env`의 `GIT_TRANSPORT`

값: `auto`(기본) | `ssh` | `https`.

- **bootstrap이 `auto`를 1회 해소**: repo host별로
  `ssh -T -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new git@<host>`
  프로브 → 어느 하나라도 성공하면 `.env`에 `GIT_TRANSPORT=ssh` 고정, 아니면 `https` 고정.
  이미 `ssh`/`https`로 고정돼 있으면 존중하고 프로브 생략. 기존 `.env`에 줄이 없으면 추가.
- **config.py는 프로브하지 않는다**: `GIT_TRANSPORT`를 읽어 `ssh`면 `_to_ssh` 적용,
  그 외(unset/`auto`/`https`/미지의 값)는 https 그대로 → 완전 하위호환.

## 변경 범위

1. **`sync/karakeep_sync/config.py`**
   - `_to_ssh(remote)` 추가: `https?://(creds@)?host/path(.git)?` → `git@host:path.git`.
     이미 `git@`/`ssh://`면 그대로. 매칭 실패 시 원본 반환.
   - `load_config`: `transport = os.environ.get("GIT_TRANSPORT","https")`; repo remote를
     `transport=="ssh"`일 때 `_expand(_to_ssh(raw))`, 아니면 `_expand(raw)`.
2. **`sync/karakeep_sync/cli.py` (`init`)**
   - 이미 clone된 repo(`repo.path.exists()`) 분기에서 origin을 해소된 transport로
     `git remote set-url origin <repo.remote>` 재조정(멱등) → 기존 clone도 실제 전환.
3. **`scripts/bootstrap.sh`**
   - `.env` 스캐폴드/유지 후 `GIT_TRANSPORT` auto-detect 단계 추가(위 규칙).
   - PAT 안내(`NEED`)는 최종 transport가 `https`일 때만 노출.
4. **`scripts/vault-sync.sh`**
   - 동일 `GIT_TRANSPORT` 존중. `to_ssh_url()` shell 함수로 `PARA_URL`/`SUB_URL` 및
     company remote(`OBSIDIAN_PARA_COMPANY_REMOTE`/`BOOKMARKS_COMPANY_REMOTE`) 변환.
     **churn 방지의 필수 요소** — common repo는 vault의 submodule이라 두 소비자가
     같은 origin을 두고 다투면 매 실행 remote set-url이 번갈아 덮어쓴다.
   - transport=ssh일 때 PAT 미설정을 치명 오류로 죽이지 않도록 `die` 조건 완화.
5. **`sync/.env.example`** — `GIT_TRANSPORT=auto` 추가, PAT 항목에 "SSH면 생략 가능" 주석.
6. **`sync/config.yaml.example`** — remote 위에 "transport=ssh면 자동 git@ 재작성" 한 줄 주석.

## 불변식 — 반드시 보존

- **§4.3 회사 기밀 가드레일**: transport는 URL 형식만 바꾼다. confidential 라우팅
  (`_is_confidential`/`_repo_accepts_bookmark`)·`company_lists`·`is_company`는 무관·불변.
- **모드 규칙**: external/home=common(GitHub), internal=company(GHES) pull-only 등 기존 로직 불변.
- **하위호환**: `GIT_TRANSPORT` unset/https → 기존 PAT 동작 그대로.

## 테스트 (`sync/tests/test_config.py`)

- `_to_ssh`: github.com 형식, GHES `${VAR}` 형식(확장 전 host/owner 변수 보존), `owner:pat@`
  자격증명 제거, 이미 `git@`이면 무변경, `.git` 유무.
- `GIT_TRANSPORT=ssh` + PAT 미설정 → `load_config` 성공, remote가 `git@...` (미해소 `${VAR}` 없음).
- `GIT_TRANSPORT` unset/https → 기존 HTTPS remote 유지(하위호환).
- monkeypatch로 `os.environ`/`GHES_*` 주입, 임시 config.yaml + mode_file 사용.

## 검증

- `cd sync && mise run test` 전체 통과.
- 수동: 이 PC(home)에서 `GIT_TRANSPORT=ssh`로 `uv run karakeep-sync status`가 401/clone 오류 없이 동작.
