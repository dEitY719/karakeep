# 통합 카테고리 체계 제안

> 작성일: 2026-06-12
> 상태: 리뷰 중
> 대상: WSL 디렉토리 / Obsidian / Bookmarks(Karakeep) / Windows 디렉토리

---

## 배경 및 문제

- PARA 원칙을 대전제로 4개 시스템을 통일하려 할 때 억지스러운 부분이 발생
- 각 시스템이 서로 다른 성격을 가지고 있어 완전한 1:1 매핑이 현실적이지 않음

| 시스템 | 실제 성격 |
|--------|-----------|
| WSL `~/` | 주로 **Projects** (실행 중인 코드/서비스) |
| Obsidian | **Areas + Resources** (지식 축적/노트) |
| Bookmarks | **거의 Resources** (참고 링크 모음) |
| Windows | **Archive + Areas** (문서, 미디어) |

---

## 제안: PARA × Domain 2-레이어 시스템

### Layer 1 — PARA (WHY: 지금 이게 무엇인가)

| 코드 | 이름 | 기준 |
|------|------|------|
| P | Projects | 마감/목표 있는 현재 진행 중인 작업 |
| A | Areas | 계속 유지해야 할 책임 영역 (끝이 없음) |
| R | Resources | 언젠가 참고할 자료 (수동적 보관) |
| Z | Archive | 비활성 (완료, 중단, 만료) |

> 판단 기준: "지금 이게 활성 상태인가?" → P/A vs R/Z

### Layer 2 — Domain (WHAT: 주제)

| 태그 | 범위 |
|------|------|
| `dev` | 개발/프로그래밍 |
| `infra` | 인프라/DevOps/Cloud |
| `ai` | AI/ML |
| `work` | 직장/업무 |
| `finance` | 재테크/가계 |
| `learn` | 학습/자기계발 |
| `personal` | 개인/일상 |

---

## 시스템별 적용 방안

### WSL `~/`

```
~/apps/          서비스로 실행 중인 것 (karakeep, homelab 등)
~/dev/
  work/          회사 프로젝트
  personal/      개인 프로젝트
~/learn/         학습용 실습/클론
~/dotfiles/      설정 파일
```

- Projects는 `~/dev/{work,personal}/` 아래에 모음
- 완료된 프로젝트는 삭제하거나 별도 Archive 드라이브로 이동

### Obsidian

```
00_Inbox/
10_Projects/
  work/
  personal/
20_Areas/
  dev/
  infra/
  ai/
  finance/
  personal/
30_Resources/
  dev/
  infra/
  ai/
  finance/
90_Archive/
```

- `00_Inbox/` → 분류 애매하면 일단 여기. 주 1회 정리
- Obsidian을 **기준점(SSOT)** 으로 사용. 나머지 시스템은 여기서 파생

### Bookmarks (Karakeep 태그)

폴더 구조 없이 **태그 조합**으로 운영:

```
# PARA 태그 (Layer 1)
area/dev        area/infra      area/ai
area/work       area/finance    area/personal
resource/dev    resource/infra  resource/ai

# 프로젝트 연결 태그 (필요 시)
project/karakeep-sync
project/homelab

# 상태 태그
status/read-later
status/archive
```

> Bookmark는 95%가 Resources. Projects/Areas 태그는 "이 프로젝트와 직접 연관된 링크"일 때만 사용.

### Windows 디렉토리

```
Documents/
  Areas/
    work/
    finance/
    personal/
  Archive/
    {year}/
Downloads/    임시 (주 1회 정리)
```

- Windows는 Archive + Areas만 관리. Projects는 WSL에 있음
- `Downloads/`는 임시 폴더로 취급, 정기 정리

---

## 실용 원칙

1. **PARA 판단은 "지금 쓰냐"만으로** — 주제(domain)와 분리해서 생각하면 헷갈림 90% 제거
2. **Inbox 우선** — 분류가 애매하면 일단 Inbox. 완벽한 분류를 위해 저장을 미루지 않는다
3. **Obsidian을 SSOT로** — 지식/노트의 원본은 Obsidian. 나머지는 링크/참조
4. **Bookmark는 태그만** — 폴더 계층 없이 태그 2개 조합으로 충분
5. **Archive는 연도별** — `Archive/2026/` 형태로 보관, 삭제하지 않음

---

## 마이그레이션 순서 (제안)

1. Obsidian 폴더 구조 확정 및 적용
2. Karakeep 태그 체계 정리 (기존 224개 북마크 일괄 정리)
3. WSL `~/` 디렉토리 재구성
4. Windows Documents 정리

---

## 미결 논의 포인트

- [ ] Domain 목록이 현재 업무/관심사를 충분히 커버하는지 확인
- [ ] `work` 와 `personal` 의 경계가 애매한 경우 처리 방식
- [ ] 회사 PC에서 `work` 카테고리를 별도 GHES repo로 분리하는 방식과의 정합성
- [ ] Windows OneDrive/iCloud 등 클라우드 동기화 범위
