# 테스트 가이드

[문서 목록](README.md)

## 실행

Python 가상환경을 활성화하고 API 개발 의존성을 설치한 상태에서 실행한다.
다음 명령은 저장소 루트 기준이다.

```sh
make check-rules
make test
```

`make test`는 문서·규칙 검사와 검사기 회귀 테스트 후 `apps/api`에서 pytest를 실행한다.
다른 Python의 pytest를 실행하지 않으려면 활성화된 가상환경에서 아래 명령을 사용한다.

```sh
cd apps/api
python -m pytest
python -m pytest tests/test_api_workflow.py -q
```

프런트엔드 의존성을 설치한 뒤 `apps/web`에서 실행한다.

<!-- doc-cwd: apps/web -->
```sh
npx tsc --noEmit --incremental false
npm run build
```

타입 검사와 production build는 브라우저 동작 테스트를 대신하지 않는다.
현재 웹 자동 UI 테스트는 없다.

## 현재 테스트와 확인 범위

| 테스트 | 주요 확인 내용 |
| --- | --- |
| `test_parsers.py` | 문서·코드 파싱과 후보 추출 관련 동작 |
| `test_reachability.py` | route/import 기반 코드 선별 |
| `test_zip_safety.py` | ZIP 경로 탈출 거부와 vendor 제외 |
| `test_lifecycle.py` | 실제 ASGI lifespan 초기화·중단 작업 복구와 UTC 저장 형식 |
| `test_source_delete.py` | 소스 삭제, 근거 보호, 시작 시 중단 작업 복구 |
| `test_api_workflow.py` | HTTP 업로드·분석·승인·검색·정책 수정·삭제와 오류 응답 |

정확한 시나리오는 각 테스트를 기준으로 한다.
파서 단위 테스트 통과만으로 실제 업로드 경로까지 검증되었다고 보지 않는다.

## 테스트 격리

<!-- doc-check: {"kind":"review","path":"apps/api/tests/test_api_workflow.py","symbol":"client","sha256":"e6654c03321ad015551bd728030f4cbcd5ea086ee7e66ad85bb687e2fd2d7cb0"} -->

- 테스트별 임시 SQLite DB와 `tmp_path` 저장소를 사용한다.
- 삭제·외래 키 동작을 검사할 때 SQLite의 foreign key 검사를 명시적으로 활성화한다.
- HTTP 테스트는 `app.dependency_overrides[get_db]`로 요청 DB를 대체한다.
- 분석 작업은 별도 engine을 사용하므로 `infrastructure.jobs.engine`도 대체한다.
- 실제 키가 설정되어 있어도 호출하지 않도록 LLM 키를 비우거나 외부 호출을 fake로 교체한다.
- 테스트 종료 시 dependency override, 클라이언트, engine을 정리한다.
- 현재 HTTP fixture는 운영 DB 초기화를 피하기 위해 startup을 실행하지 않는다.
  시작 시 동작은 별도 테스트에서 격리된 engine으로 확인한다.
- PostgreSQL 전용 Enum·잠금·동시성·마이그레이션은 별도 PostgreSQL 환경에서 검증한다.
  SQLite 결과로 동일한 동작을 보장하지 않는다.

## 변경별 검증 기준

| 변경 | 추가하거나 실행할 검증 |
| --- | --- |
| 순수 도메인 규칙 | 정상·경계·거부 조건을 작은 단위 테스트로 검증 |
| DTO 또는 라우터 | 상태 코드, 검증 오류, 직렬화된 JSON 계약 |
| 승인·병합·거절 | 상태 전이, 다른 프로젝트 접근, 중복 요청, 근거 연결 |
| 업로드·분석 | 실제 multipart 업로드부터 chunk·후보 생성까지 |
| 삭제·트랜잭션 | 참조 보호, 공유 파일, rollback 뒤 데이터 보존 |
| LLM 연동 | 성공·빈 응답·형식 오류·timeout의 fake 응답과 fallback metadata |
| React 화면 | 타입 검사와 영향 화면의 로딩·오류·성공 상태 수동 확인 |

모든 변경에 큰 통합 테스트를 추가할 필요는 없다.
단순 문서 수정은 문서 링크와 개발 규칙 검사를 확인한다.
구현 내부의 호출 횟수보다 외부에서 관찰할 수 있는 결과와 데이터 일관성을 검증한다.

## 자동 검사 범위

`make check-rules`는 길이·클래스 수·일부 import 경계를 확인한다.
Python 타입 정확성, formatting, 모든 계층 의존성, 보안, 테스트 누락을 보장하지 않는다.
현재 Ruff·mypy/Pyright·CI 파이프라인을 설치하거나 구성한 상태는 아니다.
검사를 추가하면 의존성과 설정을 함께 커밋하고 이 문서의 실행 명령도 갱신한다.

문서 검사 범위와 근거 갱신 절차는 [문서 자동 검증](documentation-checks.md)을 따른다.

## 경고 회귀 방지

pytest 설정의 `filterwarnings = ["error"]`로 경고가 발생하면 테스트를 실패시킨다.
경고 필터로 숨기지 말고 호출 방식·의존성·자원 정리를 수정한다.
현재 Starlette TestClient용 `httpx2`를 개발 의존성에 포함한다.
이전 FastAPI 버전의 TestClient 호환을 위해 `httpx`도 유지한다.
가상환경의 의존성은 API 디렉터리에서 다음 명령으로 갱신한다.

<!-- doc-cwd: apps/api -->
```sh
python -m pip install -e ".[dev]"
```
