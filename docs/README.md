# 문서 관리 정책 (Documentation Policy)

> **모든 문서는 "어떤 종류의 문서인가"로 분류한다. 어떤 기능을 다루는지는 파일 이름에 담는다.**

폴더는 문서의 *종류(성격)* 로만 나눈다. 기능명은 파일 이름에 담는다
(예: `architecture/features/auth-sso-integration.md`). 이렇게 하면 기능이
늘어나도 디렉터리 복잡도가 거의 일정하게 유지된다 (SRP/SSOT).

## 폴더 구조

| 폴더 | 규칙 |
|------|------|
| `adr/` | 프로젝트 전체 아키텍처 의사결정 (불변 로그) |
| `product/` | 제품 관리 산출물: PRD·수용기준·유즈케이스·기능 목록 |
| `design/` | 기능 설계 스펙·UX 설계·디자인 시스템·UI 표준 |
| `architecture/system/` | 시스템 전체 아키텍처·데이터 모델·배포 파이프라인 (현재 상태 SSOT) |
| `architecture/features/` | 개별 기능 단위 TRD·마이그레이션 계획 (완료 시 system 으로 병합/아카이브) |
| `testing/` | 품질 보증 산출물: 테스트 전략·E2E 시나리오·검증 기준 |
| `guides/` | 내부 운영 방법론: 개발 프로세스·테스트 가이드·온보딩 |
| `public/` | 외부 공개 문서 (별도 네임스페이스) |

## Docs-as-Code 규칙

1. **상태 메타데이터** — `product/`·`architecture/` 문서는 상단 front-matter 에
   `status: [draft | review | approved | deprecated]` 를 명시해 어떤 문서가
   현재 유효한 SSOT 인지 판별한다.
2. **ADR 연동** — `architecture/features/` 에서 중대한 기술 전환이 일어나면
   관련 `adr/` 번호를 본문에 링크한다 (예: `Ref: [ADR-0015](../../adr/0015-...)`).
3. **파일명 린터** — 파일 이름은 `kebab-case` 로 통일하고, CI 단계에서 간단한
   파일명 린터로 강제하는 것을 권장한다.

---

이 구조는 `/devx:docs-bootstrap` 로 생성되었습니다. 빈 디렉터리는 `.gitkeep`
으로 git 에 추적됩니다 — 실제 문서를 추가하면 `.gitkeep` 은 삭제해도 됩니다.
