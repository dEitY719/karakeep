# 개인 정보 분류 표준안

## 목적

WSL 디렉토리, Windows 디렉토리, Obsidian, Bookmark를 하나의 사고 체계로 정리하기 위한 공통 분류 원칙을 정의한다.

이 문서의 목표는 네 저장소를 완전히 같은 폴더 구조로 맞추는 것이 아니라, 같은 판단 기준으로 운영되게 만드는 것이다.

## 핵심 결론

- `PARA`는 공통 상위 원칙으로 사용한다.
- 저장소마다 성격이 다르므로 실제 구조는 최소한으로 현지화한다.
- 공통으로 통일할 것은 `폴더명`보다 `분류 판단 기준`과 `이름 규칙`이다.

한 줄 요약:

> `Project / Area / Resource / Archive`는 공통으로 유지하고, 각 저장소는 그 성격에 맞게 얕은 구조와 메타데이터를 조합한다.

## 공통 분류 프레임

모든 항목은 먼저 아래 네 가지 중 하나로 판정한다.

### 1. Project

- 결과물이나 종료 조건이 명확하다.
- 현재 진행 중이거나 가까운 시점에 처리해야 한다.
- 예: 북마크 체계 개편, 문서 마이그레이션, 특정 리포지토리 정리

### 2. Area

- 끝나는 일이 아니라 계속 관리해야 하는 책임 영역이다.
- 예: career, finance, health, home-lab, writing

### 3. Resource

- 참고, 학습, 재사용, 아이디어 축적이 목적이다.
- 예: linux 팁, obsidian 템플릿, productivity 자료, bookmark taxonomy 사례

### 4. Archive

- 완료되었거나 비활성화되었지만 보존 가치는 있다.
- 예: 종료된 프로젝트, 더 이상 활성 관리하지 않는 참고자료

## 보조 축: 형태(Type)

PARA만으로는 실제 정리 시 정보 밀도가 부족하다. 따라서 보조 축으로 형태를 함께 사용한다.

권장 값:

- `doc`
- `note`
- `code`
- `config`
- `asset`
- `link`

예시:

- `P / bookmark-taxonomy-redesign / doc`
- `A / home-lab / config`
- `R / obsidian / note`
- `R / linux / link`

이 구조의 장점은 저장 위치가 달라도 같은 언어로 분류할 수 있다는 점이다.

## 공통 운영 원칙

### 원칙 1. 깊은 트리보다 얕은 구조를 우선한다

- 물리 폴더 깊이는 가능한 2~3단 이내로 제한한다.
- 세부 분류는 검색, 파일명, 태그, 속성으로 해결한다.

### 원칙 2. 행동 단위와 보관 단위를 분리한다

- `Project`는 행동 중심이다.
- `Area`, `Resource`, `Archive`는 유지와 보관 중심이다.

### 원칙 3. 물리 구조와 메타데이터를 구분한다

- 디렉토리는 물리 저장 위치를 나타낸다.
- 태그, frontmatter, 이름 규칙은 논리 분류를 담당한다.

### 원칙 4. 한 항목의 원본은 한 곳만 둔다

- WSL, Windows, Obsidian, Bookmark에 동일 파일 또는 동일 책임 개체를 중복 보관하지 않는다.
- 다른 저장소에는 링크, 바로가기, 요약 노트, 인덱스만 둔다.

### 원칙 5. 분류보다 검색 가능성을 우선한다

- 정확한 카테고리보다 일관된 이름 규칙과 검색 가능성이 더 중요하다.
- 카테고리 경계가 애매하면 `Resource`에 두고 이름과 태그를 강화한다.

## 공통 최상위 구조 제안

디렉토리 기반 저장소에서는 아래 구조를 기본값으로 사용한다.

```text
00_inbox
10_projects
20_areas
30_resources
90_archive
```

의미:

- `00_inbox`: 미분류 임시 수집
- `10_projects`: 진행 중 결과물
- `20_areas`: 장기 책임 영역
- `30_resources`: 참고자료
- `90_archive`: 종료/비활성 보관

숫자 prefix를 두는 이유는 정렬 안정성과 시각적 우선순위 때문이다.

## 공통 도메인 집합 제안

처음부터 도메인을 많이 만들면 실패한다. 아래 8~12개 수준에서 시작하는 것이 적절하다.

- `career`
- `writing`
- `finance`
- `health`
- `home`
- `home-lab`
- `dev`
- `linux`
- `windows`
- `obsidian`
- `productivity`
- `learning`

운영 원칙:

- 도메인 이름은 모든 시스템에서 동일하게 유지한다.
- `linux / WSL / ubuntu / server`처럼 같은 개념의 별칭을 혼용하지 않는다.
- 3개월 정도 운영 후 합치거나 쪼갠다.

## 이름 규칙 제안

### Project

형식:

```text
YYYY-MM topic
```

예:

- `2026-06 bookmark-taxonomy-redesign`
- `2026-06 home-lab-cleanup`

### Area

형식:

```text
domain
```

예:

- `home-lab`
- `finance`
- `writing`

### Resource

형식:

```text
domain-topic
```

예:

- `linux-filesystem`
- `obsidian-dataview`
- `productivity-capture-patterns`

### Archive

형식:

```text
YYYY
```

또는 기존 이름 유지 후 연도 기준으로 상위 폴더만 정리한다.

## 저장소별 적용 원칙

### 1. WSL 디렉토리

역할:

- 개발 코드
- 스크립트
- 설정
- 자동화 자산

권장 구조:

```text
00_inbox/
10_projects/
20_areas/
30_resources/
90_archive/
```

예:

```text
10_projects/2026-06-bookmark-taxonomy-redesign
20_areas/home-lab
20_areas/dev-env
30_resources/linux
30_resources/obsidian
```

주의:

- 실행 코드와 설정은 WSL을 원본으로 삼는다.
- Windows와 같은 책임 단위를 중복 생성하지 않는다.

### 2. Windows 디렉토리

역할:

- 실사용 문서
- 다운로드
- 미디어
- 일반 사용자 작업물

권장 원칙:

- WSL과 같은 PARA 상위 구조를 유지할 수 있으면 유지한다.
- 다만 Windows 기본 사용자 폴더와 충돌하는 경우, 완전한 재배치보다 운영 규칙 통일을 우선한다.

실무적으로는 다음 둘 중 하나가 적절하다.

1. `Documents` 아래에 PARA 루트를 둔다.
2. 기존 사용자 폴더는 유지하고, 실제 분류 규칙만 PARA로 통일한다.

권장 판단:

- 문서 원본은 Windows
- 개발 원본은 WSL

### 3. Obsidian

Obsidian은 폴더만으로 정리하려 들면 금방 경직된다. 폴더는 얕게 두고 속성으로 보강하는 편이 낫다.

권장 구조:

```text
0 Inbox
1 Projects
2 Areas
3 Resources
9 Archive
```

권장 frontmatter 예시:

```yaml
type: note
para: resource
domain: linux
status: active
source: bookmark
```

운영 원칙:

- 폴더는 PARA 1차 분류만 담당한다.
- 주제, 출처, 상태는 frontmatter로 관리한다.
- 특정 시스템의 실제 파일을 Obsidian에 복제하지 말고, 링크나 인덱스 노트로 연결한다.

### 4. Bookmark

북마크는 대부분 `Resource`이므로 PARA만으로는 잘 정리되지 않는다. Bookmark는 예외적으로 `행동 중심` 분류를 우선하는 것이 현실적이다.

권장 1차 분류:

- `read`
- `reference`
- `tool`
- `watch`
- `buy`

권장 2차 분류:

- `linux`
- `windows`
- `obsidian`
- `productivity`
- `dev`
- `career`

예:

- `reference/linux`
- `tool/obsidian`
- `read/productivity`

정리 원칙:

- 북마크의 상위 철학은 PARA를 따르되 실제 구조는 행동 중심으로 운영한다.
- 장기적으로 재사용할 지식은 Obsidian note 또는 Resource 문서로 승격한다.
- 단순 소비 대상은 bookmark에만 남기고 다른 저장소로 복제하지 않는다.

## 분류 판단표

새 항목이 들어올 때는 아래 순서로 판단한다.

1. 이 항목은 결과물이나 마감이 있는가?
2. 그렇다면 `Project`
3. 아니라면 지속 관리 책임이 있는가?
4. 그렇다면 `Area`
5. 아니라면 참고/학습/수집 목적의 자료인가?
6. 그렇다면 `Resource`
7. 이미 끝났거나 비활성인가?
8. 그렇다면 `Archive`

애매할 때의 기본 규칙:

- 판단이 어려우면 `Resource`
- 당장 처리 전이면 `Inbox`
- 완료 후 재사용 가치가 있으면 `Archive`

## 금지 규칙

- 폴더 깊이 4단 이상
- 시스템마다 다른 이름으로 같은 개념을 부르는 것
- 북마크만의 별도 대분류 체계를 계속 확장하는 것
- Obsidian 폴더만으로 모든 지식 구조를 해결하려는 것
- 언젠가 쓸 수 있을 것 같다는 이유만으로 `Project`에 보관하는 것

## 도입 순서 제안

### 1단계

- 공통 PARA 구조 확정
- 공통 도메인 집합 8~12개 확정
- 이름 규칙 확정

### 2단계

- WSL 루트 정리
- Windows 문서 루트 정리
- Obsidian 폴더 및 frontmatter 기본값 정리
- Bookmark 1차 분류를 행동 기준으로 재정리

### 3단계

- 중복 저장 위치 제거
- 원본 위치 기준 확정
- Obsidian을 인덱스와 연결 허브로 사용

### 4단계

- 1~3개월 운영
- 실제 사용 패턴 기준으로 도메인 축소/통합

## 최종 제안

이 문제의 핵심은 `카테고리 설계` 자체보다 `서로 다른 저장소를 같은 원칙으로 운영하는 일`이다.

따라서 최종 원칙은 다음과 같다.

- `PARA`는 전 저장소 공통의 의사결정 프레임으로 사용한다.
- 실제 구조는 저장소 특성에 맞게 최소한으로 조정한다.
- 디렉토리는 얕게 유지한다.
- Obsidian은 속성 중심으로 운영한다.
- Bookmark는 행동 중심으로 운영한다.
- 도메인 이름과 판단 기준은 전 시스템에서 통일한다.

이 방식이 가장 덜 이상적이면서 가장 오래 유지되는 운영안이다.
