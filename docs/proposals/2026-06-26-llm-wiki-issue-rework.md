# llm-wiki 이슈 재작성·분할 제안 (#41 · #42)

> 작성일: 2026-06-26
> 상태: **제안 (Proposal)** — #41/#42 구현 착수 전 검토 결과
> 대상: GitHub Issue #41, #42 · `docs/proposals/llm-wiki/SCHEMA.md`
> 관련: 동료 스킬 `claude-plugin-llm-wiki/plugins/llm-wiki/skills/llm-wiki`

---

## 0. 한 줄 요약

> 동료의 llm-wiki 스킬은 잘 만들어졌고 **프로젝트별 `SCHEMA.md` 커스터마이즈를
> 전제로 설계**됐다. 그러나 **#42 는 이 스킬이 아니라 다른 참고 구현
> (lewislulu·wasplinguist)의 기능을 이 스킬의 계약처럼 적었다.** 따라서 스킬은
> 그대로 채택하고, #42 의 ~60%(스킬에 없는 동작)는 버리며, 남는 것을 얇은
> `SCHEMA.md` 하나 + 통합 결정 이슈 하나로 줄인다.

---

## 1. 배경 — 무엇이 확인됐나

지난 검토에서 #41/#42 가 인용한 인프라 사실(`vault-sync.sh` L37/L176–187/L211–215,
`markdown.py` L7–8/L26–27, SSOT §2 10개 도메인, 3중 명명)은 **line 단위로 정확**함을
확인했다. 그러나 두 이슈가 참조하는 `/llm-wiki` 스킬은 당시 repo 에 없었다.

이후 동료의 실제 스킬을 입수해 전문(SKILL.md + reference 7종)을 #42 와 대조한 결과:

- 스킬은 SKILL.md L30 에서 **"`SCHEMA.md` overrides everything below"** 로
  프로젝트별 SCHEMA.md 를 명시적으로 요구한다 → KARAKEEP/Obsidian 통합은 스킬의
  결을 거스르는 게 아니라 **스킬이 기대하는 사용법**이다.
- 그러나 #42 가 설계한 상당 부분이 **스킬에 존재하지 않는 동작**이다(아래 §2).

---

## 2. 핵심 발견 — #42 는 다른 스킬을 설계했다

| 항목 | 동료 **실제 스킬** | #42 설계 | 처리 |
|---|---|---|---|
| 연산 | Ingest(register+compile+log) / Query / Lint / Schema | 6-op `ingest/compile/query/lint/audit/daily` | **DROP** (6-op 어휘) |
| `audit` (anchor 피드백) | **없음** | audit/·resolved/·anchor 4단 ladder·단일파서 (lewislulu) | **DROP** |
| `daily` (일일 다이제스트) | **없음** | synthesis/daily/YYYYMMDD.md (wasplinguist) | **DROP** |
| log | 단일 `log.md` | `log/YYYYMMDD.md` 디렉터리 | **DROP** (스킬 형식 사용) |
| page types | concept·decision·bug·open-question·source·reference·synthesis·stub(+archive) | concept·**entity**·source·synthesis·**moc** | **DROP** (스킬 lint 이 미지 type reject) |
| lint | deterministic **auto-fix(쓰기)** + heuristic 보고 | "read-only, 자동수정 X" | **FIX** (보안모델 오류, §3) |
| `overview.md` | 없음 (index.md + 선택 README.md) | 발명 | **DROP** |
| raw-sources/skills | stable 소스는 참조만 | 항상 스냅샷 복사 | **KEEP** (SCHEMA deviation, 사유 타당) |
| Navigation(TOC·survey lede·See-also) | 풍부 | 언급 없음 | 스킬에 이미 있음 — 추가 작업 불필요 |

**왜 DROP 인가:** `audit`·`daily`·`entity`/`moc`·`log/` 는 SCHEMA.md 가
오버라이드하는 "관례"가 아니라 **스킬 코드를 포크해야 하는 동작 변경**이다.
사용자는 동료 스킬을 그대로 쓰기로 했고(스킬 개선 제안 안 함) → 이들은 채택하지
않는다. 향후 정말 필요하면 별도 스킬-개선 트랙으로 분리한다.

---

## 3. 보안 모델 오류와 수정

#42 의 internal-mode 전략 전체가 **"lint 은 read-only 라 internal 에서 유일하게
허용되는 op"** 라는 전제 위에 있었다. 그러나 실제 스킬의 lint 은 deterministic
auto-fix(index↔파일 동기화, 링크 교정, See-also 양방향 추가)로 **파일을 쓴다.**

→ internal 모드(`vault-sync.sh` L176–187)에서는 lint 도 경계를 위반한다.
**확정 정책**(SCHEMA.md Notes §5): 쓰기 op(ingest/lint/synthesis)는 **external·home
PC 에서만**, internal PC 는 read/query 전용·file-back 금지, `--allow-outside`
사용 금지. 이는 SCHEMA.md 로 못 푸는 통합 설계 항목이라 **별도 결정 이슈**로 둔다.

---

## 4. 제안하는 이슈 구조

### #41 — 축소·유지 (location/operation 기준 문서)
원안의 "중앙 위키 위치 + global CLAUDE.md 포인터 + SCHEMA.md 생성"은 스킬과
정합한다. 다만 **AC 를 docs 범위로 정정**한다:
- `~/.claude/CLAUDE.md` 에 `llm-wiki location:` canonical(`...\30_Resources\llm-wiki\`) 명시
- `30_Resources/llm-wiki/SCHEMA.md` 배치(= 본 제안의 `docs/proposals/llm-wiki/SCHEMA.md` 를 vault 로 복사)
- starter topic 5개 / source bucket / 경로 전략 포함
- **제거**: 런타임 동작을 가정한 AC

### #42 — 재작성 (대폭 축소) 또는 close
원안(300줄, 7개 설계결정)을 **얇은 `SCHEMA.md` 산출 이슈**로 재작성한다. 산출물은
이미 본 제안에 포함된 `docs/proposals/llm-wiki/SCHEMA.md` (스킬 SCHEMA.template.md
구조 준수 + 정당한 deviation: karakeep `{id,url}` provenance, skills 복사 정책,
명명 canonical, KST). §2 의 DROP 항목은 본문에서 모두 제거.

### #NEW-A — internal 쓰기 경계 통합 결정 (신규)
§3 의 정책을 운영 규율로 확정. (선택) 비강제 안전장치 검토: 쓰기 op 진입 시
`$HOME/.dotfiles-setup-mode` 가 internal 이면 경고하는 wrapper. 스킬 본체는 수정
안 함(채택한 "as-is" 원칙 유지).

### 분리/보류 트랙
- `status/reference` 태그 신규 추가는 **SSOT 변경**이므로 llm-wiki 와 분리(미도입
  시 `status/archive` 폴백).
- audit/anchor·daily 등 스킬에 없는 기능은 채택 안 함(필요 시 별도 트랙).

---

## 5. 살린 가치 (스킬과 무관한 진짜 프로젝트 작업)

- ✅ `vault-sync.sh` line 단위 분석 — 통합 제약의 핵심
- ✅ 3중 명명 정리(`30_resources`/`30_Resources`/`30-Resource`) canonical 결정
- ✅ Karakeep `{karakeep_id, url}` provenance + 미populate 내성
- ✅ cross-PC 경로/대소문자 전략
- ✅ internal 경계 문제 인식(모델은 §3 으로 수정)

이상은 모두 `docs/proposals/llm-wiki/SCHEMA.md` 에 인코딩됨.

---

## 6. 다음 단계

1. 본 제안 + `SCHEMA.md` 초안 리뷰·승인
2. #41 AC 정정, #42 재작성(또는 close + 신규), #NEW-A 등록
3. external/home PC 에서 `SCHEMA.md` 를 vault `30_Resources/llm-wiki/` 로 복사 후
   첫 ingest 로 dogfooding
