# Python 작성 기준

[문서 목록](README.md) · [공통 개발 규칙](development-rules.md)

## 실행 환경과 의존성

<!-- doc-check: {"kind":"toml","path":"apps/api/pyproject.toml","key":"project.requires-python","expected":">=3.11"} -->

- 지원 하한은 `apps/api/pyproject.toml`의 Python 3.11이다.
  더 높은 버전 전용 문법·표준 라이브러리를 도입할 때는 지원 버전과 Dockerfile을 함께 검토한다.
- 가상환경에서 설치·실행하고 `python -m pip`, `python -m pytest`로 인터프리터를 명시한다.
- 런타임 의존성은 `dependencies`, 테스트 도구는 `optional-dependencies.dev`에 추가한다.
- 현재 Python 잠금 파일, formatter, 정적 타입 검사기는 없다. 설치되었다고 가정하는 명령을 문서화하지 않는다.
- 새 의존성은 표준 라이브러리로 해결하기 어려운 이유와 사용 계층을 설명한다.

## 이름, 함수와 타입

- 함수·변수·모듈은 `snake_case`, 클래스는 `PascalCase`, 상수는 `UPPER_SNAKE_CASE`로 쓴다.
- 공개 함수와 서비스에는 인자·반환 타입을 작성한다. `None` 반환도 명시한다.
- `list[str]`, `str | None`처럼 지원 버전에 맞는 표기를 사용한다.
- 고정 구조의 데이터를 `dict`나 `Any`로 계속 전달하지 않는다. 의미가 드러나는 별도 데이터 타입을 사용한다.
- JSON metadata처럼 확장 가능한 구조는 허용하되 필수 키와 생성 주체를 명확히 한다.
- 함수 이름은 수행하는 일을 설명한다. 주석과 docstring은 제약, 부작용, 이유를 설명한다.
- 여러 작업을 한 줄에 압축하거나 복잡한 삼항식을 중첩하여 줄 수를 줄이지 않는다.

## 데이터 모델 선택

| 목적 | 기준과 현재 예 |
| --- | --- |
| 프레임워크 독립 내부 데이터 | 표준 `dataclass`, `domain/parsed_chunk.py` |
| 입력 검증과 응답 직렬화 | Pydantic 모델, `application/dto/` |
| DB 매핑 | SQLAlchemy 모델, `infrastructure/models/` |
| 상태 값 | Enum, `domain/*_status.py` 등 |

- 목록·사전 기본값은 dataclass의 `field(default_factory=...)` 등 인스턴스별 생성 방식을 쓴다.
- 변경 가능한 객체를 함수 기본 인자로 사용하지 않는다.
- 요청의 형식 검증은 DTO, DB 상태에 의존하는 검증은 서비스에서 수행한다.
- 부분 수정 API는 누락, 명시적 `null`, 빈 값의 의미를 정한다.
  현재 `PolicyUpdate` 서비스는 `None`을 변경 없음으로 취급하고 `rules=[]`는 규칙 전체 삭제로 처리한다.

## 예외와 자원 정리

<!-- doc-check: {"kind":"review","path":"apps/api/app/domain/application_error.py","symbol":"ApplicationError","sha256":"2dfbddeeeb9a5836e62ef6b41be699dd12c2ce9fe030caf2bac4be48fdbb9129"} -->

- 예상되는 서비스 실패는 `ApplicationError`로 전달한다. 서비스에서 `HTTPException`을 발생시키지 않는다.
- 현재 `ApplicationError`는 `status_code`, `detail`을 가지며 `main.py`가 JSON 오류로 변환한다.
  완전히 HTTP 독립적인 오류 코드 체계는 아직 적용하지 않았다.
- 예외를 빈 `except`로 무시하지 않는다. 복구 가능한 경우만 fallback하고 이유를 남긴다.
- `except Exception`은 분석 작업 실패 기록이나 LLM fallback 같은 최외곽 복구 경계에 한정한다.
- 파일·DB 세션·압축 파일은 context manager를 사용하고, 별도 종료가 필요한 자원은 `finally`에서 정리한다.
- 낮은 계층에서 예외를 바꿀 때는 `raise ... from exc`로 원인을 보존한다.

## 동기·비동기 경계

<!-- doc-check: {"kind":"review","path":"apps/api/app/presentation/routes/sources.py","symbol":"upload_source","sha256":"4dae15fa7b5148858743312b69b9b047fac18cc01d07381fc42a245fbcb02b76"} -->

- 현재 DB는 동기 SQLAlchemy `Session`, LLM 호출도 동기 방식이다.
- `async def` 자체는 내부의 동기 DB·파일·네트워크 호출을 비동기로 바꾸지 않는다.
  비동기 함수에 블로킹 I/O를 추가할 때 실행 위치를 검토한다.
  [Python asyncio 문서](https://docs.python.org/3/library/asyncio-task.html#running-in-threads)
- 스레드로 옮길 때는 작업 내부에서 세션을 생성·종료하고 기존 요청 세션을 공유하지 않는다.
  [SQLAlchemy 세션 동시성](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#is-the-session-thread-safe-is-asyncsession-safe-to-share-in-concurrent-tasks)
- 현재 업로드 라우터는 `await file.read(...)` 후 동기 서비스를 직접 호출한다.
  이를 이미 비동기화된 구현으로 간주하지 않는다. 개선 항목은 별도 문서에 기록한다.

## 시간과 설정

<!-- doc-check: {"kind":"review","path":"apps/api/app/domain/clock.py","symbol":"utc_now_naive","sha256":"2335bdb8361dba4d7b86aeccbe59bb61be01851e8bbef3b1892a658c8ea7a187"} -->

<!-- doc-check: {"kind":"review","path":"apps/api/app/config.py","symbol":"","sha256":"923a1e80d390479c3e6c1c1cee877ec874adcd30839df38b6d8ab5f07568bb13"} -->

- 현재 DB 시각은 `domain/clock.py`의 `utc_now_naive()`와 시간대 없는 `DateTime`으로 UTC를 표현한다.
  내부에서 `datetime.now(UTC)`를 사용한 뒤 기존 DB·API 계약에 맞춰 시간대 정보를 제거한다.
- 새 시간 처리의 목표는 시간대 있는 UTC다. `datetime.now(UTC)`를 사용할 수 있지만,
  기존 DB 타입·저장값·응답 계약을 함께 검토한 뒤 일관되게 전환한다.
  [Python datetime 문서](https://docs.python.org/3/library/datetime.html#datetime.datetime.utcnow)
- 타임스탬프 표현과 사용자 화면의 지역 시간 변환을 분리한다.
- 경과 시간과 요청 간격은 시스템 시각 변경의 영향을 줄이도록 `time.monotonic()`을 사용한다.
- 설정은 `config.py`를 통해 읽는다. 함수마다 환경변수를 직접 읽지 않는다.
- `settings`와 DB engine은 import 시 생성된다. 테스트는 import 이후 변경이 필요한 대상을 명시적으로 대체한다.

## 로깅

- 로그에는 `source_id`, `job_id`, 처리 단계와 오류 종류처럼 추적에 필요한 값을 남긴다.
- 비밀 키, 인증 헤더, 전체 업로드 내용, 전체 프롬프트를 기본 로그에 넣지 않는다.
- 사용자에게 보여줄 오류 설명과 내부 traceback을 구분한다.
- 현재 분석 실패는 `str(exc)`를 DB 오류 필드에 저장한다. 민감 정보 제거는 후속 개선 항목이다.
