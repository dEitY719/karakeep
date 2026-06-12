# 디지털 정보 조직 표준 (SSOT)

> 작성일: 2026-06-12
> 상태: **SSOT (Single Source of Truth)**
> 대상 시스템: WSL 디렉토리 · Windows 디렉토리 · Obsidian · Bookmark(Karakeep)
> 통합 출처: `personal-taxonomy-standard`, `unified-category-system`, `digital-organization-strategy-with-para`

---

## 0. 이 문서의 목적

WSL, Windows, Obsidian, Bookmark(Karakeep) — 성격이 다른 네 저장소를 **하나의 사고 체계**로 운영하기 위한 공통 표준이다.

목표는 네 저장소를 **똑같은 폴더 구조로 맞추는 것이 아니라**, **같은 판단 기준으로 운영**되게 만드는 것이다. 시스템마다 성격이 다르므로 실제 구조는 최소한으로 현지화하되, **분류 판단 기준 · 도메인 이름 · 이름 규칙**은 전 시스템에서 통일한다.

**한 줄 요약**

> `Project / Area / Resource / Archive`(PARA)를 공통 의사결정 프레임으로 유지하고, 각 저장소는 그 성격에 맞게 얕은 구조와 메타데이터를 조합한다.

이 문제의 핵심은 *카테고리 설계 자체*보다 *서로 다른 저장소를 같은 원칙으로 운영하는 일*이다. 이 방식이 가장 덜 이상적이면서 가장 오래 유지된다.

---

## 1. PARA 원칙의 재해석: 모든 것을 꿰뚫는 하나의 질문

> **이 섹션이 모든 시스템을 관통하는 핵심 기준이며, 모든 동료가 공감하는 단일 판단 원칙이다.**

어떤 정보(파일, 폴더, 노트, 북마크)를 마주했을 때, 스스로에게 이 질문을 던진다.

> **"이것이 '명확한 목표와 끝'이 있는 일과 관련이 있는가?"**

- **YES (네):** **`Projects`** 로 갑니다. (예: 'karakeep 기능 개발', '여름 휴가 계획', '자격증 시험 준비')
- **NO (아니오):** 그렇다면 이것이 **"내가 책임감을 갖고 지속적으로 관리해야 할 영역인가?"**
    - **YES:** **`Areas`** 로 갑니다. (예: '건강', '재정', '커리어 개발', '팀 관리')
    - **NO:** 그렇다면 이것이 **"미래에 유용할 수 있는, 관심 있는 주제인가?"**
        - **YES:** **`Resources`** 로 갑니다. (예: 'AI 에이전트', '파이썬', '요리법', '가드닝')
        - **NO:** 그렇다면 이것은 **"지금 당장은 필요 없는, 완료되거나 보관할 자료인가?"**
            - **YES:** **`Archive`** 로 갑니다. (예: '완료된 프로젝트', '더 이상 관리하지 않는 영역의 자료')

이 질문의 흐름이 모든 시스템을 관통하는 통일된 기준이다.

핵심 단순화: **PARA 판단은 "지금 활성 상태인가?"만으로 한다.** 주제(Domain)와 분리해서 생각하면 분류 혼란의 90%가 사라진다. (`P/A` = 활성, `R/Z` = 비활성/수동)

---

## 2. 3-축 모델: Scope(WHERE) × PARA(WHY) × Domain(WHAT)

분류는 항상 **독립된 축**으로 한다. 한 축에 두 가지 의미를 섞지 않는다. 세 축은 직교(orthogonal)하며, 한 항목은 세 축의 값을 동시에 가질 수 있다.

| 축 | 질문 | 값 예시 | 정체 |
| ---- | ---- | ---- | ---- |
| Scope (경계) | 누구 것 / 어디 소속인가? | `common` / `company` | WHERE/WHO |
| PARA (Layer 1) | 지금 활성인가? | P / A / R / Z | WHY |
| Domain (Layer 2) | 무슨 주제인가? | dev, finance, work… | WHAT |

예: `company` + `R`(Resource) + `dev` → 회사 내부 개발 참고 문서 / `common` + `A`(Area) + `work` → 회사 기밀은 아닌 내 커리어 관리 자료

### Layer 0 — Scope (WHERE: 누구 것 / 어디 소속인가)

소유·접근 **경계**를 나누는 최상위 축이다. *주제*가 아니라 *경계*이므로 도메인 `work`와 혼동하지 않는다.

| 값 | 범위 | 기준 |
| ---- | ---- | ---- |
| `common` | 개인 공용 — 어디서든 접근 가능한 일반 자료 | 회사 기밀·사내 전용이 아님 |
| `company` | 회사 전용 — 사내 기밀/사내 시스템/소속 조직 한정 | 회사 밖으로 나가면 안 되는 경계 |

> `company`는 "업무라는 주제"가 아니라 "회사 전용이라는 경계"를 뜻한다. 업무 주제 자체는 Domain `work`로 표기하며, 둘은 공존할 수 있다(`common` + `work` 가능). Karakeep 북마크의 `common`/`company` 구분이 바로 이 축이다.

### Layer 1 — PARA (WHY: 지금 이게 무엇인가)

| 코드 | Full name | 기준 | 활성 여부 |
| ---- | --------- | ---- | --------- |
| `P` | **P**rojects | 마감/목표가 있고 지금 진행 중인 작업 | 활성 |
| `A` | **A**reas | 끝없이 계속 관리해야 할 책임 영역 | 활성 |
| `R` | **R**esources | 언젠가 참고할 자료 (수동적 보관) | 비활성/수동 |
| `Z` | Archi**ve** | 완료·중단·만료된 비활성 자료 | 비활성/수동 |

> Archive의 정식 머리글자는 `A`지만 Area와 충돌하므로, "마지막/끝"을 떠올리게 하는 `Z`를 태그 코드로 쓴다.

### Layer 2 — Domain (WHAT: 주제)

처음부터 도메인을 많이 만들면 실패한다. **8~10개 수준에서 시작**하고, 같은 개념의 별칭(`linux / WSL / ubuntu / server`)을 혼용하지 않는다. 도메인 이름은 모든 시스템에서 **동일하게** 유지하며, 3개월 운영 후 합치거나 쪼갠다.

| 태그 | 범위 |
|------|------|
| `dev` | 개발/프로그래밍 |
| `infra` | 인프라/DevOps/Cloud/홈랩 |
| `ai` | AI/ML |
| `work` | 직장/업무/커리어 |
| `finance` | 재테크/가계 |
| `health` | 건강 |
| `learn` | 학습/자기계발 |
| `writing` | 글쓰기 |
| `productivity` | 생산성/도구/워크플로우 |
| `personal` | 개인/일상/홈 |

> `linux`, `windows`, `obsidian` 같은 *도구* 단위는 별도 도메인으로 만들지 말고 도메인 하위 토픽(예: `dev-linux`, `productivity-obsidian`)으로 둔다.

### 보조 축 — Type (선택)

PARA × Domain만으로 정보 밀도가 부족할 때 형태를 함께 표기한다.
`doc` · `note` · `code` · `config` · `asset` · `link`

예: `P / bookmark-taxonomy-redesign / doc` · `A / home-lab / config` · `R / obsidian / note`

---

## 3. 공통 운영 원칙

1. **얕은 구조 우선** — 물리 폴더 깊이는 2~3단 이내. 세부 분류는 검색·파일명·태그·속성으로 해결한다. (깊이 4단 이상 금지)
2. **행동 단위와 보관 단위 분리** — `Project`는 행동 중심, `Area/Resource/Archive`는 유지·보관 중심.
3. **물리 구조와 메타데이터 구분** — 디렉토리는 물리 저장 위치, 태그·frontmatter·이름 규칙은 논리 분류.
4. **원본은 한 곳만** — 동일 파일/책임 개체를 여러 저장소에 중복 보관하지 않는다. 다른 저장소에는 링크·바로가기·요약 노트·인덱스만 둔다.
5. **분류보다 검색 가능성 우선** — 정확한 카테고리보다 일관된 이름 규칙과 검색 가능성이 중요하다. 경계가 애매하면 `Resource`에 두고 이름·태그를 강화한다.
6. **Inbox 우선** — 분류가 애매하면 일단 Inbox. 완벽한 분류를 위해 저장을 미루지 않는다.
7. **Obsidian을 지식 SSOT로** — 지식/노트의 원본은 Obsidian. 나머지 시스템은 여기서 파생(링크/참조).

**원본 위치 기준**
- 문서 원본 → **Windows**
- 개발 코드/설정 원본 → **WSL**
- 지식/노트 원본 → **Obsidian**
- 소비용 링크 → **Bookmark(Karakeep)**

---

## 4. 공통 최상위 구조 & 이름 규칙

### 디렉토리 기반 저장소의 기본 루트

```text
10_projects   # 진행 중 결과물
20_areas      # 장기 책임 영역
30_resources  # 참고자료
40_archive    # 종료/비활성 보관
99_inbox      # 미분류 임시 수집
```

숫자 prefix는 정렬 안정성과 시각적 우선순위를 위한 것이다. Inbox는 `99_`로 두어 활성 분류(10~40) 아래 맨 끝에 모이게 한다. (Obsidian은 `10_Projects / 20_Areas / … / 99_Inbox` 동일 패턴)

### 이름 규칙

| 분류 | 형식 | 예 |
|------|------|----|
| Project | `YYYY-MM topic` | `2026-06 bookmark-taxonomy-redesign` |
| Area | `domain` | `home-lab`, `finance`, `writing` |
| Resource | `domain-topic` | `linux-filesystem`, `obsidian-dataview` |
| Archive | `YYYY` (또는 기존 이름 유지 + 연도 상위 폴더) | `2025`, `Archive/2026/` |

---

## 5. 시스템별 적용 가이드

### 5.1 WSL `~/` — 주로 Projects (실행 코드/서비스/설정)

```text
~/apps/          서비스로 실행 중인 것 (karakeep, homelab 등)
~/dev/
  work/          회사 프로젝트
  personal/      개인 프로젝트
~/learn/         학습용 실습/클론
~/dotfiles/      설정 파일
```

- 실행 코드와 설정은 **WSL을 원본**으로 삼는다. Windows와 같은 책임 단위를 중복 생성하지 않는다.
- 완료된 프로젝트는 삭제하거나 별도 Archive 위치로 이동한다.

### 5.2 Windows 디렉토리 — Areas + Archive (문서/미디어)

```text
Documents/
  Areas/
    work/   finance/   personal/
  Archive/
    {year}/
Downloads/    # 임시 — 주 1회 정리
```

- Windows는 **Areas + Archive 중심**. Projects는 WSL에 있다.
- 기본 사용자 폴더와 충돌하면 완전한 재배치보다 **운영 규칙 통일**을 우선한다.
- 문서 **원본은 Windows**. `Downloads/`는 임시 폴더로 취급해 정기 정리한다.

### 5.3 Obsidian — Areas + Resources (지식·노트, 폴더 + 태그)

```text
10_Projects/
  work/  personal/
20_Areas/
  dev/ infra/ ai/ finance/ personal/
30_Resources/
  dev/ infra/ ai/ finance/
40_Archive/
99_Inbox/        # !! 모든 생각/메모는 일단 여기 (Daily Note)
```

- 폴더는 **PARA 1차 분류만** 담당. 주제·출처·상태는 frontmatter로 관리한다.

```yaml
type: note
para: resource
domain: dev
status: active
source: bookmark
```

- 노트는 한 폴더에만 있지만 태그는 여러 개 가질 수 있다. 예: `30_Resources`의 노트에 `#project/karakeep-feat-auth` 태그로 현재 프로젝트와의 연관성 표시.
- **주간 리뷰**로 Inbox를 비우며 §1의 핵심 질문으로 PARA 폴더에 배치한다.
- 다른 시스템의 실제 파일을 Obsidian에 복제하지 말고 **링크/인덱스(MOC) 노트**로 연결한다.

### 5.4 Bookmark (Karakeep) — 거의 Resources (태그 운영)

북마크는 95%가 Resources다. 폴더 계층 없이 **태그 2개 조합**으로 운영한다.

```text
# Layer 0 (Scope: 경계)
scope/common    scope/company

# Layer 1 (PARA)
area/dev      area/infra    area/ai
resource/dev  resource/infra resource/ai

# 프로젝트 연결 태그 (직접 연관 링크일 때만)
project/karakeep-sync   project/homelab

# 상태 태그
status/read-later   status/archive
```

- **Scope 태그(`scope/common` · `scope/company`)** 는 현재 Karakeep의 `common`/`company` 구분을 그대로 잇는다. 회사 전용 경계를 표시하며, 업무 *주제*는 별도로 `*/work` 도메인 태그로 단다(둘은 공존 가능). 자세한 정의는 §2 Layer 0 참조.
- `Projects/Areas` 태그는 "이 프로젝트/영역과 **직접** 연관된 링크"일 때만 사용한다.
- 장기 재사용할 지식은 Obsidian note / Resource 문서로 **승격**한다. 단순 소비 대상은 북마크에만 남기고 복제하지 않는다.
- '나중에 읽기'는 `status/read-later`로 격리해 `resource/*`가 오염되지 않게 한다.

---

## 6. 분류 판단표

새 항목이 들어오면 §1의 질문을 다음 순서로 적용한다.

1. 결과물이나 마감이 있는가? → **Project**
2. 아니면 지속 관리 책임이 있는가? → **Area**
3. 아니면 참고/학습/수집 자료인가? → **Resource**
4. 이미 끝났거나 비활성인가? → **Archive**

**애매할 때 기본 규칙**
- 판단이 어려우면 → `Resource`
- 당장 처리 전이면 → `Inbox`
- 완료 후 재사용 가치가 있으면 → `Archive`

---

## 7. 통합 워크플로우 (수집 → 정리 → 실행 → 보관)

1. **수집 (Capture):** 모든 정보는 각 시스템의 **Inbox**로 들어온다.
   - 파일 → `~/99_inbox` / Windows `Downloads/`
   - 아이디어·메모 → Obsidian `99_Inbox` Daily Note
   - 웹 링크 → Karakeep (`status/read-later`)
2. **정리 (Process):** 매일/매주 정해진 시간에 Inbox를 비운다. 각 항목에 §1 질문을 던져 PARA로 옮긴다.
3. **실행 (Execute):** `Projects`와 `Areas`를 보며 오늘 할 일을 결정·실행한다.
4. **보관 (Archive):** 프로젝트가 끝나면 관련 폴더/노트 전체를 `Archive`로 옮긴다. 이것이 시스템을 깨끗하게 유지하는 비결이다.

---

## 8. 금지 규칙

- 폴더 깊이 4단 이상
- 시스템마다 다른 이름으로 같은 개념을 부르는 것
- 북마크만의 별도 대분류 체계를 계속 확장하는 것
- Obsidian 폴더만으로 모든 지식 구조를 해결하려는 것
- "언젠가 쓸 수 있을 것 같다"는 이유만으로 `Project`에 보관하는 것
- 동일 책임 개체를 여러 저장소에 중복 원본으로 두는 것

---

## 9. 도입 / 마이그레이션 순서

### 1단계 — 표준 확정
- 공통 PARA 구조 확정
- 공통 도메인 집합(8~10개) 확정
- 이름 규칙 확정

### 2단계 — 적용
1. **Obsidian** 폴더 구조 + frontmatter 기본값 확정·적용 (지식 SSOT 먼저)
2. **Karakeep** 태그 체계 정리 (기존 북마크 일괄 재태깅)
3. **WSL `~/`** 디렉토리 재구성
4. **Windows Documents** 정리 (Areas/Archive 중심)

### 3단계 — 정합화
- 중복 저장 위치 제거, 원본 위치 기준 확정
- Obsidian을 인덱스·연결 허브로 사용

### 4단계 — 운영·튜닝
- 1~3개월 운영 후 실제 사용 패턴 기준으로 도메인 축소/통합

### 첫 걸음 (오늘)
한 번에 다 바꾸려 하면 지친다. **오늘은 한 저장소에 `10_projects / 20_areas / 30_resources / 40_archive` + `99_inbox`만 만들고**, 다음 일주일간 *새로 생기는 항목만* 이 분류로 넣는 연습을 한다. 기존 항목은 점진적으로 옮긴다.

---

## 10. 미결 논의 포인트

- [ ] Domain 목록(§2 Layer 2)이 현재 업무/관심사를 충분히 커버하는지 확인
- [ ] `work`와 `personal`의 경계가 애매한 경우 처리 방식
- [ ] 회사 전용 경계(`scope/company`, §2 Layer 0)를 별도 GHES repo로 분리하는 방식과의 정합성 — `company` 경계가 곧 분리 지점이 된다. 분리 시 `scope/company` 항목만 GHES로 빠지고, `scope/common`은 개인 저장소에 남는다. (주제 도메인 `work`는 이 분리와 무관하게 양쪽에 모두 존재 가능)
- [ ] Windows OneDrive/iCloud 등 클라우드 동기화 범위
- [ ] WSL↔Windows 공유 지점(`/mnt/c/...`)을 PARA 중심으로 삼을지, 저장소별로 분리 운영할지

---

## 부록: 최종 원칙 요약

- `PARA`는 전 저장소 공통의 의사결정 프레임으로 사용한다.
- 실제 구조는 저장소 특성에 맞게 최소한으로 조정한다.
- 디렉토리는 얕게 유지한다.
- Obsidian은 속성(frontmatter) 중심으로, Bookmark는 태그 중심으로 운영한다.
- 도메인 이름과 판단 기준은 전 시스템에서 통일한다.
