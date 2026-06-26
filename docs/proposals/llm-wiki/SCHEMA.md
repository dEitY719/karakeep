<!--
  배포 대상: ObsidianVault-PARA 의 `30_Resources/llm-wiki/SCHEMA.md`
  (이 파일은 repo 내 초안. vault 로 복사해 사용한다.)

  근거: 동료가 만든 llm-wiki 스킬
  (claude-plugin-llm-wiki/plugins/llm-wiki/skills/llm-wiki/SKILL.md)은
  "SCHEMA.md overrides everything below" 로 프로젝트별 SCHEMA.md 커스터마이즈를
  명시적으로 요구한다. 이 파일은 그 SCHEMA.md 이며, 스킬의
  references/SCHEMA.template.md 구조를 그대로 따른다(섹션 추가/삭제 없음).
  SCHEMA.md 가 오버라이드하는 것은 *관례*(domain/buckets/topic/lint 임계치)일 뿐,
  연산 어휘나 page type 목록 같은 스킬 *동작*은 바꾸지 않는다.
-->

# Wiki Schema

Per-project conventions. LLM proposes changes; user approves. Co-evolves
with the wiki.

## Domain

KARAKEEP + ObsidianVault-PARA 생태계의 **개인 공용(common) 지식 베이스**다.
범위 안: 개인 도메인(dev·ai·infra·work·productivity…) 전반의 *증류된 durable
지식*. 소스는 Karakeep 북마크(읽은 뒤 ingest)·AI 세션 export·웹 클리핑·각
프로젝트 SKILL.md 에서 유입된다. 범위 **밖**: ① 회사 기밀(항상 `80-Company/`
로 가며 이 위키에 절대 들어오지 않음), ② 북마크 원본 미러 자체(그건
`30-Resource/Bookmarks` 서브모듈 = Karakeep 의 SSOT). 위치는 vault 의
`30_Resources/llm-wiki/`, 동기화는 `scripts/vault-sync.sh` 가 담당한다.

## Source buckets

By kind of source. 스킬 기본값에서 이 프로젝트에 쓰는 것만 둔다(나머지는 첫
사용 시 user 승인 후 추가):

- `articles/` — 웹 클리핑·블로그. 주로 **Karakeep 북마크를 읽은 뒤 ingest** 하는 경로
- `conversations/` — Claude Code / AI 세션 export
- `notes/` — 붙여넣기·ad-hoc 메모
- `confluence/` — auth-walled/mutable 스냅샷(복사 보관)
- `skills/` — 프로젝트 SKILL.md 스냅샷. **⚠ Deviation**: 스킬은 stable in-repo
  경로를 *참조만* 하라고 하지만, 여기선 **복사**한다(`skills/<plugin>__<skill>.md`).
  사유는 Notes §4.
- `papers/`, `transcripts/` — 스킬 기본값. 첫 소스 ingest 시 생성.

## Topic taxonomy

By subject. **권위 목록 = SSOT §2 Layer 2 의 10개**:
`dev · infra · ai · work · finance · health · learn · writing · productivity ·
personal`. New topics need user approval.

- 시작 디렉터리는 `dev/ ai/ infra/ work/ productivity/` 5개. 나머지 5개
  (finance·health·learn·writing·personal)는 해당 도메인 첫 소스 ingest 시 생성
  (빈 폴더 난립 방지).
- `linux`·`windows`·`obsidian` 같은 *도구* 단위는 새 topic 으로 만들지 말고
  도메인 하위(`dev-linux`, `productivity-obsidian`)로 둔다. (SSOT §2 규칙)

## Page types

스킬의 canonical 8종을 **그대로** 쓴다:
`concept · decision · bug · open-question · source · reference · synthesis ·
stub` (+ `synthesis-and-archive.md` 의 `archive`). 프로젝트 전용 type 추가
없음 — 특히 `entity`/`moc` 를 **만들지 않는다**(스킬 lint 이 canonical 목록에
없는 type 을 reject 한다). 도메인 진입 네비게이션은 별도 type 이 아니라 스킬의
`index.md` + `## See also` 패턴으로 한다.

## Lint rules

- Stale-claim threshold: 30 days (스킬 기본값).
- Relative path verification: 모든 `](*.md)` 링크는 파일 위치 기준으로 resolve.
- Bidirectional links: A→B See Also 면 B→A 도.
- Tag presence: `tags:` 누락 경고 — 100줄 초과 페이지.
- **프로젝트 규칙**: Karakeep 출처 페이지의 `sources:` 항목은 `karakeep_id` 와
  `url` 을 **함께** 갖는다(Notes §3). `id` 만 있고 `url` 이 없으면 경고.

## Notes

1. **위치·경로.** Canonical:
   `C:\Users\<USERNAME>\Documents\ObsidianVault-PARA\30_Resources\llm-wiki\`
   (WSL: `/mnt/c/Users/<USERNAME>/Documents/ObsidianVault-PARA/30_Resources/llm-wiki/`).
   PC별로 `<USERNAME>` 만 다르다. **경로는 정확한 대소문자로 생성**한다 —
   `/mnt/c` 는 case-insensitive 지만 git/WSL 은 case-sensitive 라, 잘못된
   대소문자는 Windows phantom 중복 디렉터리 또는 case-only git rename 을 만든다.

2. **명명 reconciliation (3중 표기 존재).** 이 위키 경로는 항상 underscore
   `30_Resources`. 하이픈/단수 `30-Resource/Bookmarks` 는 **별개** — Karakeep
   북마크 서브모듈(`vault-sync.sh` L37)이며 Karakeep 의 SSOT, 이 위키와 무관.
   `30_resources`(소문자, SSOT prose L133)는 `30_Resources` 로 supersede 됨.

3. **Karakeep provenance.** 북마크 출처는 `{karakeep_id, url}` 를 **함께** 적는다
   (id 단독 금지). `id` 는 `30-Resource/Bookmarks/<id>.md` 로 해소된다(그 .md 의
   frontmatter `id`, `sync/karakeep_sync/markdown.py`). external/home PC 에서는
   Bookmarks 서브모듈이 미populate 일 수 있어(vault-sync 가 거기선 submodule
   update 를 생략, #37) 북마크 .md 가 없을 수 있다 → `url` 이 안정 fallback
   provenance 키다. **북마크 .md 가 없어도 ingest 를 실패시키지 않는다.**

4. **`skills/` = 스냅샷 복사 (deviation).** SKILL.md 는 stable in-repo 경로를
   복사 없이 참조하라고 한다. 여기선 override: 프로젝트 SKILL.md 는 Linux
   `$HOME` 의 플러그인 repo 에 살지만 internal vault 는 Windows `/mnt/c` +
   pull-only 라, Linux 절대경로는 **다른 PC 에서 resolve 불가** → 해시/멱등성이
   깨진다. 그래서 SKILL.md 본문을 `skills/<plugin>__<skill>.md` 로 복사하고,
   원본 repo-상대경로는 메타로만 남긴다(절대경로 하드코딩 금지).

5. **쓰기 경계 — internal PC (중요).** `vault-sync.sh` L176–187 은 internal
   모드에서 `80-Company/`·`30-Resource/Bookmarks`·`.obsidian` **밖**의 모든
   변경/신규 파일을 `die` 시킨다. `30_Resources/llm-wiki/` 는 그 밖이므로
   **모든 쓰기**(ingest·lint **auto-fix**·synthesis file-back·`log.md` append)가
   동기화를 깨뜨린다. ⚠ 스킬의 lint 은 deterministic auto-fix = **쓰기**라
   internal 에서도 안전하지 않다. → **쓰기 op(ingest/lint/synthesis)는
   external·home PC 에서만** 실행한다. internal PC 는 read/query 전용이며
   file-back 하지 않는다. vault-sync 의 `--allow-outside` 로 우회하지 않는다
   (company-leak 가드를 전역 무력화함). [통합 결정 트랙 — 재작성 제안서 참조]

6. **시간대.** 날짜는 KST(UTC+9). `log.md` 는 스킬 형식
   `## [YYYY-MM-DD] <op> | <title>` 을 쓰는 **단일 파일**이다(per-day 디렉터리 아님).

7. **회사 콘텐츠.** 기밀은 이 위키에 들어오지 않는다. `80-Company/` 로
   라우팅하고 internal PC 에서 그 경계 안으로만 ingest — llm-wiki 범위 밖.
