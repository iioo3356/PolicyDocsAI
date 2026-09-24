# 문서 자동 검증

[문서 목록](README.md)

문서 전체를 매번 읽는 대신 먼저 검사하고, 실패한 문서와 근거 코드만 확인한다.
Python 3.11+ 표준 라이브러리만 사용하며 앱 import, DB 연결, 네트워크 요청을 하지 않는다.
문서 안의 명령을 실행하거나 파일을 자동 수정하지 않는다.

## 실행과 결과

<!-- doc-check: {"kind":"symbol","path":"scripts/check_docs.py","symbol":"validate"} -->

저장소 루트에서 실행한다.

```sh
make check-docs
python3 scripts/check_docs.py --json
make test-docs
```

- `make check-docs`: 성공 시 요약, 실패 시 파일·줄 번호·이유를 최대 20건 출력한다.
- `--json`: 전체 오류와 검사·제외 건수를 한 줄 JSON으로 출력한다.
- 종료 코드 0은 검사 통과, 1은 문서 오류다. CLI 사용 오류는 2다.
- `make check-rules`와 `make test`에도 문서 검사가 포함된다.
- `make test`는 검사기 회귀 테스트도 실행한다.
- `make test-docs`는 임시 저장소로 검사기 자체를 테스트하며 API 의존성이 필요 없다.

## 자동 검사 범위

| 항목 | 확인하는 것 |
| --- | --- |
| 문서 길이 | `docs/` 아래 Markdown 파일당 최대 300줄 |
| 로컬 링크 | 대상 파일·디렉터리 존재, 저장소 밖 경로 차단 |
| Markdown 앵커 | ATX 제목의 앵커, 중복 제목의 숫자 접미사 |
| 참조형 링크 | `[label][id]`와 `[label][]`의 정의와 대상 |
| 인라인 코드 경로 | 알려진 경로 기준에서 파일·디렉터리·glob 존재 |
| shell 예제 | cd 대상, make target, npm script, Python 파일 대상 |
| 명시적 코드 근거 | Python 심볼 존재, Enum 값, TOML 값, AST fingerprint |

경로는 저장소 루트, 문서 디렉터리, API app·tests, web에서 찾는다.
여러 파일에 해당하면 전체 저장소 상대 경로로 명확하게 적는다.
인라인 경로 검사는 공백 없는 `.py`, `.ts`, `.tsx`, `.toml`, `.json`, `.md`, 슬래시로 끝나는 값에 적용한다.
일반 함수명, API URL, 환경변수명을 경로로 추측하지 않는다.
존재하지 않는 예시 경로는 코드 블록 안에 두어 실제 참조와 구분한다.

## 명령 예제의 작업 디렉터리

각 shell 코드 블록은 저장소 루트에서 시작한다.
블록 안에서 `cd`하면 이후 명령에 반영하며 `&&` 연결도 처리한다.
다른 디렉터리에서 시작하는 예제에는 바로 앞에 다음 주석을 적는다.

```md
<!-- doc-cwd: apps/web -->
```

이 주석은 다음 코드 블록에 한 번 적용된다.
인식하지 못한 명령은 실행하지 않고 `commands_skipped`로 집계한다.
명령의 옵션·실행 성공·모듈 설치 여부를 확인하는 검사가 아니다.

## 문서와 코드 근거 연결

설명 가까이에 한 줄 JSON 주석을 추가한다. path는 저장소 루트 기준이다.

```md
<!-- doc-check: {"kind":"symbol","path":"apps/api/app/main.py","symbol":"health"} -->
<!-- doc-check: {"kind":"toml","path":"apps/api/pyproject.toml","key":"project.requires-python","expected":">=3.11"} -->
```

- `symbol`: 클래스·함수·메서드가 실제로 정의되어 있는지 확인한다. 재노출 import는 따라가지 않는다.
- `toml`: 점으로 구분한 키의 값과 `expected`가 일치하는지 확인한다.
- `enum`: 클래스의 공개 상수 이름·값 전체를 `expected` 객체와 비교한다.
- `review`: 지정 Python 심볼의 AST fingerprint를 `sha256`과 비교한다.
  `symbol`이 빈 문자열이면 파일 전체를 대상으로 한다.
- 잘못된 JSON, 알 수 없는 종류·필드, 누락된 경로·심볼은 실패한다.

## 코드가 변경되어 REVIEW가 나오는 경우

1. 오류가 가리키는 설명과 근거 코드만 읽는다.
2. 현재 동작과 설명이 일치하도록 문서를 수정한다. 동작 검증은 관련 테스트로 확인한다.
3. 검토가 끝난 뒤 아래 명령으로 새 fingerprint를 얻어 해당 주석의 값만 갱신한다.
4. 문서 검사를 다시 실행한다.

```sh
python3 scripts/check_docs.py --fingerprint apps/api/app/analysis/pipeline.py --symbol run_analysis
```

주석 형식은 다음과 같다. 아래 값은 실행용이 아닌 형식 예시다.

```md
<!-- doc-check: {"kind":"review","path":"apps/api/app/analysis/pipeline.py","symbol":"run_analysis","sha256":"검토 후 얻은 SHA-256"} -->
```

fingerprint는 줄 번호·공백·Python 주석 변경은 무시하고 AST 변경을 감지한다.
설명 검토 없이 일괄 재생성하여 통과시키지 않는다.
새로운 동작 설명을 추가할 때는 관련 함수나 파일의 review 근거도 추가한다.

## 자동으로 증명하지 못하는 것

- 자연어 설명의 진실성, 설계 적절성, 테스트 커버리지와 실제 실행 결과.
- 참조한 함수가 호출하는 다른 함수의 변경. 필요하면 그 함수에도 근거를 연결한다.
- 외부 URL의 가용성·내용. 외부 링크는 `external_links_skipped`로 집계한다.
- CommonMark 전체 문법. 링크 제목, 중첩 괄호 URL, shortcut 참조, Setext 제목,
  HTML 앵커 등은 지원 범위 밖이므로 검증 대상 문서에서는 단순 링크와 `#` 제목을 사용한다.
- `docs/` 밖 문서의 본문. 단, 로컬 링크 대상과 대상 Markdown 앵커는 확인한다.

검사 통과는 **등록된 정적 근거와 문서 구조가 맞는다**는 뜻이다.
기능이 동작하거나 모든 문장이 사실임을 보증하지 않는다.
