# 데이터와 작업 처리

[문서 목록](README.md)

아래는 현재 코드 기준의 동작과 변경 시 지켜야 할 기준이다.
일반적인 시스템 설계와 현재 구현의 보장 범위를 혼동하지 않는다.

## 데이터 연결

- `Project`에 `Source`와 `Policy`가 속한다.
- `Source`는 업로드 메타데이터, `SourceFile`은 파일 경로, `SourceChunk`는 원본 구간을 보관한다.
- `AnalysisJob`은 분석 상태와 통계, `PolicyCandidate`는 검토 전 추출 결과를 보관한다.
- `PolicyRule`은 승인된 규칙, `PolicyEvidence`는 원본 근거의 경로·라인·발췌를 보관한다.
- `SourceVersion`은 소스 버전 연결과 업로드 시점 정책을, `PolicyRevision`은 승인된 변경 전후와 소스 정보를 보관한다.
- `PolicyConflict` 모델은 존재하지만 자동 충돌 판정은 구현되지 않았다.

모델 정의는 `apps/api/app/infrastructure/models/`에 있다.
DB 스키마를 바꿀 때는 외래 키와 삭제 순서, 응답 DTO를 함께 확인한다.

## 세션과 트랜잭션

<!-- doc-check: {"kind":"review","path":"apps/api/app/db.py","symbol":"get_db","sha256":"b1a158eed305aae37e2ae8ac82785ba0c90bac5ef721135e7b28f759b080b1a1"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/infrastructure/jobs.py","symbol":"_process_job","sha256":"4bf86b67f72c34a75b03c4e31ddaf630a2833ead77c4bde5de575c87b0597622"} -->

- HTTP 요청은 `db.get_db()`가 생성한 세션을 사용하며 종료 시 닫는다.
- 백그라운드 작업은 `infrastructure/jobs.py`에서 별도 세션을 생성한다.
  요청 세션이나 세션에 연결된 ORM 객체를 작업 인자로 넘기지 않고 ID를 넘긴다.
- `flush()`는 현재 트랜잭션에 변경을 반영하고 생성된 ID를 얻는 데 사용한다.
  저장 확정은 `commit()`이며 flush만으로 확정되지 않는다.
- 실패한 세션으로 작업을 계속하려면 rollback이 필요하다.
  세션은 동시 작업 간 공유하지 않는다.
  [SQLAlchemy 세션과 트랜잭션](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- 현재 서비스가 commit 경계를 소유한다. 새 보조 함수가 임의로 commit하지 않도록 한다.
- 승인 시 Policy, Rule, Evidence와 후보의 검토 상태를 같은 트랜잭션에서 저장한다.

## 업로드와 저장 파일

<!-- doc-check: {"kind":"review","path":"apps/api/app/application/sources.py","symbol":"upload_source","sha256":"215fb5cc084e060d84aea71f947aee526620f3c0eec067fc6430c3287a83e93d"} -->

구현: `application/sources.py`, `infrastructure/storage.py`.

1. 라우터가 최대 업로드 크기보다 1바이트 더 읽어 초과 여부를 검증할 수 있게 한다.
2. 서비스가 프로젝트·확장자·역할·크기를 검증한다. 업데이트는 같은 프로젝트의 완료된 동일 형식 소스를 요구한다.
3. 프로젝트 ID, SHA-256, 파일명으로 저장 키를 만들고 파일을 저장한다.
4. Source와 AnalysisJob을 생성한다. replaces_source_id가 있으면 이전 소스와 정책 스냅샷을 SourceVersion에 연결하고 commit한다.
5. 라우터가 분석 작업을 등록한다.

같은 파일을 다시 업로드하면 같은 저장 파일을 공유할 수 있지만 Source와 Job은 새로 생성된다.
파일 저장과 DB commit은 원자적이지 않으므로 DB 실패 시 고아 파일이 남을 수 있다.
향후 보상 처리나 정리 작업을 추가할 때는 공유 파일을 삭제하지 않도록 참조를 확인한다.

## 분석 상태와 재시작

<!-- doc-check: {"kind":"enum","path":"apps/api/app/domain/job_status.py","symbol":"JobStatus","expected":{"PENDING":"PENDING","PROCESSING":"PROCESSING","COMPLETED":"COMPLETED","FAILED":"FAILED"}} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/analysis/pipeline.py","symbol":"run_analysis","sha256":"636ef5572128b29cee930eb2d987d701869195f8f9b6ec0b772274670d8b1c58"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/analysis/parsers.py","symbol":"parse_code","sha256":"361a7ef7446f90c5116285ae15383e1079beeadedfca3bb430d0da24bc086100"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/domain/business_policy_signal.py","symbol":"business_policy_score","sha256":"5fdc893af875767567a751824191ff57f27169764b8b7425f63ca688110582a7"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/main.py","symbol":"_recover_interrupted_analysis_jobs","sha256":"f05ba3d0a351ad8934d6c4d7975aa2f45a4868cf7ab207701880825d44c76177"} -->

- 새 Source와 Job은 `PENDING`, 실행을 시작하면 `PROCESSING`으로 바꾸고 commit한다.
- AST에서 실제 조건문·상태 분기·삼항식·검증 호출을 각각 분리한다.
- 분리된 코드 구간은 분기·검증과 업무 결과·제한 신호가 함께 있어야 후보가 된다.
  화면 표시·탐색·스타일만 제어하는 구간은 LLM 호출 전에 제외한다.
- 컴포넌트 경로 자체를 제외하지 않으므로 UI 코드 안의 취소·결제·자격·파일 제한은 분석할 수 있다.
- 파일을 처리하는 동안 현재 파일, 처리 파일 수, 전체 파일 수와 진행률을 갱신한다.
- 후보를 찾을 때마다 제목과 누적 후보를 commit하여 소스 화면의 1초 polling에서 조회할 수 있다.
- 분석 중 후보는 정책 관리 목록에서 제외하며 승인·병합·반려 API도 409로 거부한다.
- 파일·chunk·후보 처리가 끝나면 두 상태를 `COMPLETED`로 저장한다.
- 처리 중 예외가 나면 실시간 표시를 위해 먼저 commit한 후보·chunk·파일을 삭제하고
  Source의 발견 수를 0으로 되돌린 뒤 `FAILED`와 오류를 저장한다.
- 진행률은 파일 수를 기준으로 10~90 사이를 계산하고 완료 시 100으로 기록한다.
- FastAPI lifespan에서 초기화를 실행하고, 모든 `PENDING`·`PROCESSING` Source와 Job을 `FAILED`로 바꾼다.
- 현재 작업 큐는 프로세스 내부 BackgroundTasks다. 재시도·작업 재개·실행 보장을 제공하지 않는다.
- 다중 API 인스턴스에서 다른 인스턴스의 실행 중 작업까지 실패로 바꿀 수 있다.
  다중 worker 전환 전에 작업 소유권과 복구 기준을 설계해야 한다.

구현: `analysis/pipeline.py`, `main.py`의 `lifespan()`과 `_recover_interrupted_analysis_jobs()`.
시작 시 초기화는 [FastAPI lifespan 방식](https://fastapi.tiangolo.com/advanced/events/)을 사용한다.
진행 조회 API는 `GET /sources/{source_id}/analysis`이며 현재 파일·최근 발견 정책과
누적 후보 목록을 반환한다.

## 검토와 정책 변경

<!-- doc-check: {"kind":"review","path":"apps/api/app/application/candidates.py","symbol":"","sha256":"20b93970838984c5286d9d9c7f05531712ea3c5776bbdca1a36904cc80578439"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/application/policies.py","symbol":"update_policy","sha256":"af895c26044cedc82d5c6e72d8a81df29cac96e7eeacda00b5eee56ce91b51cc"} -->

| 작업 | 현재 동작 |
| --- | --- |
| 승인 | PENDING 후보로 새 APPROVED Policy를 만들고 Rule·Evidence를 연결 |
| 병합 | PENDING 후보를 같은 프로젝트의 지정 Policy에 병합하고 Evidence 추가 |
| 재승인·재병합 | 이미 검토한 후보이면 409 |
| 거절 | PENDING만 REJECTED로 변경, 이미 검토되었으면 409 |
| 소스 업데이트 승인 | 연결된 기존 정책을 전체 교체하고 search_text·근거·수정 이력을 함께 갱신 |
| 직접 정책 PATCH | 409로 소스 업데이트 안내 |

병합은 기존 Policy의 제목·요약·상태를 자동 교체하지 않는다.
일반 승인·병합은 기존 규칙과 입력 내 중복 문장을 건너뛴다.
후보 승인·반려에 행 잠금을 사용한다. PostgreSQL 동시 요청 검증은 후속 과제다.

정책 변경 시 검색용 `search_text`와 원본 근거의 연결도 확인한다.
소스 업데이트의 비교·승인·이력 계약은 [소스 업데이트](source-updates.md)를 따른다.

## Source 삭제

<!-- doc-check: {"kind":"review","path":"apps/api/app/application/sources.py","symbol":"delete_source","sha256":"af6a9d64748f6848efaf9bee578cc01241e56e9579ccb706af2290def76f5ff8"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/infrastructure/storage.py","symbol":"remove_file","sha256":"fab78465853c0cfd79054a1bb499dd5c33d069f4152718fa3b8c0fa97d46b0ad"} -->

- 분석 대기·처리 중인 Source는 409로 거부한다.
- 후속 SourceVersion이 참조하는 소스와 연결된 PolicyEvidence가 있는 소스는 409로 거부한다.
  실제 조건은 Policy의 승인 상태가 아니라 Evidence 참조 여부다.
- 후보, chunk, 파일 메타데이터, job, 해당 SourceVersion, source를 삭제하고 commit한다.
- 같은 저장 키의 Source가 남아 있지 않을 때만 실제 파일 삭제를 시도한다.
- 저장소 밖으로 해석되는 경로는 삭제하지 않는다.
- commit 뒤 파일 삭제가 실패하면 로그를 남긴다. 이미 삭제된 DB 레코드를 복원하지 않는다.

## Chat과 LLM

- Chat은 해당 프로젝트의 APPROVED 정책만 읽기 전용 질의 컨텍스트로 사용한다.
- AI가 현재 정책의 요약·규칙으로 답변하며 근거가 부족하면 필요한 정보를 되묻는다.
- 변경 요청은 관련 소스 업데이트 버튼과 안내로 연결한다. 채팅에서 정책을 수정하지 않는다.
- AI 연결 실패 시 관련 승인 정책 원문을 안내한다.
- 컨텍스트 범위, 최신 소스 근거와 실패 처리는 [정책 채팅](policy-chat.md)을 따른다.
- 소스 후보 추출 역시 LLM을 사용하며 실패 시 로컬 추출로 전환한다.
- LLM 간격 제한은 프로세스 단위다. 여러 프로세스의 총 호출량은 제어하지 않는다.

## 스키마 변경과 운영 확인

<!-- doc-check: {"kind":"review","path":"apps/api/app/main.py","symbol":"startup","sha256":"41f645cf31b9a95a78dc272e0e040feebb7bd94facc968b7f71155206612fc4c"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/main.py","symbol":"health","sha256":"d572cf4981264ef325ed57ddc10ee028325bac484ac12e2d21ef8960ed6d1f8e"} -->

- 현재 시작 시 `Base.metadata.create_all()`을 실행하고 PostgreSQL SourceKind의 XLSX 값을 보완한다.
- 버전별 마이그레이션 체계는 없다. 기존 DB의 컬럼 변경이 자동 반영된다고 가정하지 않는다.
- 스키마 변경 전 기존 데이터 변환, 배포 순서, 복구 방법을 정한다.
- `/health`는 정적 응답이며 DB·스토리지·LLM 가용성을 검사하지 않는다.
- DB와 업로드 파일은 함께 복구할 수 있어야 근거 추적이 유지된다.
