# 개발 규칙

[문서 목록](README.md) · [Python 작성 기준](python-guide.md) · [테스트 가이드](testing.md)

## 파일 크기

- 직접 관리하는 소스, 테스트, 문서, 설정 파일은 **파일당 최대 300줄**로 유지한다.
- 빈 줄과 주석도 줄 수에 포함한다. 300줄은 허용하고 301줄부터 위반이다.
- 줄을 합치거나 코드를 압축해서 제한을 피하지 않는다. 책임 단위로 분리한다.
- 패키지 잠금 파일, 자동 생성 선언 파일, 빌드 결과, 외부 의존성, 업로드 데이터는 제외한다.
- 긴 문서는 주제별 문서로 나누고 링크로 연결한다.

## 클래스와 데이터 타입

- 클래스는 **파일당 하나만 정의**한다. 데이터 클래스, ORM 모델, DTO, Enum, 예외도 포함한다.
- Python 파일명은 클래스 이름에 대응하는 `snake_case` 형식의 Python 파일명을 사용한다.
- TypeScript의 독립적인 데이터 타입도 타입별 파일로 분리한다.
- 클래스 전용 보조 함수는 같은 파일에 둘 수 있다. 공유 규칙은 별도 모듈로 분리한다.
- `__init__.py`와 호환 모듈은 재노출만 담당하며 클래스 구현을 복제하지 않는다.
- React 화면은 기능별 컴포넌트로 나눈다. 페이지는 화면 구성과 라우팅에 집중한다.

## 아키텍처

Clean Architecture의 책임 분리와 도메인 독립성을 기준으로 한다.
현재 프로젝트는 SQLAlchemy를 사용하는 소규모 서비스이므로 아래 범위로 적용한다.

| 위치 | 책임 |
| --- | --- |
| `apps/api/app/domain/` | 상태 Enum, 파싱 데이터, 역할 검증, 검색 규칙, 애플리케이션 오류 |
| `apps/api/app/application/` | 프로젝트·소스·후보·정책·채팅 유스케이스와 트랜잭션 |
| `apps/api/app/application/dto/` | 유스케이스 및 API 입출력 데이터 구조 |
| `apps/api/app/infrastructure/` | ORM 모델, 파일 저장·삭제, 백그라운드 작업 실행, LLM 응답 구조 |
| `apps/api/app/presentation/routes/` | HTTP 경로, 요청 바인딩, 업로드 읽기, 응답 모델 |
| `apps/api/app/main.py` | 앱 구성, 라우터 연결, 오류 응답 변환, 시작 시 초기화 |
| `apps/api/app/analysis/` | 기존 분석 파이프라인, 문서 파서, 코드 의존성 분석, LLM 어댑터 |
| `apps/web/domain/` | 프런트엔드 데이터 타입 |
| `apps/web/lib/api.ts` | HTTP 클라이언트와 기존 타입 import 호환성 |
| `apps/web/features/workspace/` | 기능별 화면과 React Query 상태 처리 |
| `apps/web/app/` | Next.js 라우팅과 화면 조립 |

### 의존성 규칙

- 도메인은 표준 라이브러리만 사용한다. FastAPI, SQLAlchemy, 설정, 파일·네트워크 I/O에 의존하지 않는다.
- 라우터는 서비스를 호출한다. SQL 쿼리, 정책 승인·병합 규칙, 저장 파일 삭제를 구현하지 않는다.
- 서비스는 HTTP 요청 객체나 `HTTPException`을 사용하지 않는다.
  실패는 `ApplicationError`로 전달하고 HTTP 응답 변환은 앱 경계에서 처리한다.
- 도메인 규칙은 라우터나 ORM 모델에 중복하지 않는다.
- 외부 I/O 구현은 어댑터로 분리한다. 계층 간 순환 import를 만들지 않는다.

### 현재 적용 범위와 확장 기준

- 현재 서비스는 주입된 SQLAlchemy `Session`과 ORM 모델을 직접 사용한다.
  DTO는 Pydantic을 사용한다. 엄격한 의존성 역전까지 적용한 구조는 아니다.
- DB 모델과 별도 도메인 엔티티의 일대일 복제, CRUD별 빈 Repository는 만들지 않는다.
- 저장소 교체나 복잡한 도메인 모델이 필요해지면 application에 저장소 Protocol을 정의하고,
  infrastructure에서 구현하여 구성 지점에서 주입한다.
- 기존 `analysis/`는 분석 전용 모듈로 유지한다. 새로운 외부 연동은 infrastructure에 두고,
  분석 흐름 확장 시 파서·LLM·저장소 경계를 개별적으로 분리한다.
- 웹에서는 서버 업무 규칙을 재구현하지 않는다. 복잡한 상태 처리는 기능별 훅으로 추출한다.

## 변경과 검증

<!-- doc-check: {"kind":"review","path":"scripts/check_rules.py","symbol":"","sha256":"70dfbe27b62947a5fb3d0b7b68f7303fcaa4625952c0dbe1e777505f7a6709dc"} -->

- 리팩토링은 API 경로, 상태 코드, 응답 구조, DB 테이블·컬럼, 기존 동작을 보존한다.
- 공개 import 경로를 옮길 때는 호출부를 함께 수정하거나 얇은 호환 모듈을 제공한다.
- 동작 변경이 필요하면 구조 변경과 구분하고 테스트로 검증한다.
- 오류 응답, 트랜잭션, 삭제 시 참조 보호, 승인·병합·근거 연결은 회귀 테스트로 확인한다.
- 커밋 전 아래 명령을 실행한다.

```sh
make check-rules
make test
cd apps/web && npx tsc --noEmit
```

`check-rules`는 추적 파일과 아직 추적되지 않은 비제외 파일을 검사한다.
Python 클래스 수·도메인 import·서비스의 HTTP 의존성과 라우터의 SQL 의존성을 검사한다.
TypeScript는 클래스 및 최상위 데이터 타입 선언 수를 검사한다.
자동 검사는 보조 수단이며 책임 분리, 동적 import, 실제 의존성 방향은 리뷰에서도 확인한다.

`make check-rules`는 [문서 자동 검증](documentation-checks.md)도 먼저 실행한다.
