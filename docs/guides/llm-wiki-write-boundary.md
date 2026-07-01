# llm-wiki 쓰기 경계 (어느 PC 에서 무엇을)

> 상태: **운영 규칙** · 관련 이슈: #44 (정책) · #41 (배포 스크립트) · #42 (stub)
> 정책 SSOT: `docs/proposals/llm-wiki/SCHEMA.md` §Notes 5

`/llm-wiki` 위키는 Obsidian vault 의 `30_Resources/llm-wiki/` 에 산다. 이 경로는
`scripts/vault-sync.sh` 의 **internal 작성 경계 밖**이라(L176–187), internal 모드
PC 에서 한 줄이라도 쓰면 다음 동기화가 거부(`die`)된다. 따라서 **어느 op 를 어느
PC 에서 도는지**를 규칙으로 고정한다.

## op × 모드

| op | 쓰기? | internal | external · home |
|----|:----:|:--------:|:---------------:|
| `query` / 읽기 | ✗ | ✅ 허용 | ✅ 허용 |
| `ingest` | ✓ | ❌ 금지 | ✅ |
| `lint` | ✓ (deterministic **auto-fix**) | ❌ 금지 | ✅ |
| `synthesis` file-back | ✓ | ❌ 금지 | ✅ |
| `log.md` append | ✓ | ❌ 금지 | ✅ |
| SCHEMA/stub 배포(`llm-wiki-deploy.sh`) | ✓ | ❌ 거부됨 | ✅ |

> ⚠️ 스킬의 `lint` 은 read-only 가 아니다 — index↔파일 동기화·링크 교정·See-also
> 양방향 추가를 **자동 수정**한다(SKILL.md L178–199). 그래서 internal 에서 "lint
> 만 허용" 같은 예외는 두지 않는다. **internal 은 read/query 전용**이다.

## 하드 규칙

1. **쓰기 op 는 external·home PC 에서만.** internal PC 는 위키를 읽기만 한다
   (file-back 하지 않는다).
2. **`vault-sync.sh --allow-outside` 로 우회하지 않는다.** 이 플래그는 사내 콘텐츠
   유출 가드를 전역 무력화하므로, 습관화되면 `30_Resources/` 하위 노트가 공개
   GitHub 로 샐 위험이 있다.
3. **스킬 본체는 수정하지 않는다.** 경계는 운영 규율 + 배포 스크립트의 internal
   거부(이미 구현)로 지킨다. (스킬은 vault-sync 경계를 모르므로 강제는 외부에서.)
4. 회사 기밀은 애초에 위키에 넣지 않는다 — `80-Company/` 로 라우팅(llm-wiki 범위 밖).

## `~/.claude/CLAUDE.md` 운영 메모 (스니펫)

글로벌 설정 파일이라 repo 에 두지 않는다. 아래를 붙여 둔다:

    # llm-wiki: 쓰기 op(ingest/lint/synthesis)는 external·home PC 에서만.
    #           internal PC 는 read/query 전용 (vault-sync 경계 — 자세히: docs/guides/llm-wiki-write-boundary.md)

## 검증 (internal PC 에서, 운영)

internal PC 에서 위키를 한 번 query 한 뒤:

    git -C "$VAULT_ROOT" status --porcelain   # 출력 없음(clean) 이어야 한다 = 쓰기 0건

출력이 있으면 위 규칙 위반(쓰기 op 가 돌았거나 file-back 됨)이다.

## 근거

- `scripts/vault-sync.sh` L176–187 — internal 작성 경계(화이트리스트 밖 변경 거부)
- 스킬 `SKILL.md` L178–199 — lint deterministic auto-fix(쓰기)
- `docs/proposals/llm-wiki/SCHEMA.md` §Notes 5 — 정책 SSOT
- `docs/proposals/2026-06-26-llm-wiki-issue-rework.md` §3 — 분리 근거
