# 개발 개선 과제

[문서 목록](README.md)

코드 검토에서 확인한 후속 작업이다. 아래 항목은 **미구현**이며,
완료한 항목은 아래 완료 내역으로 이동한다.
우선순위는 사용자 데이터 일관성과 운영 확장 시의 영향을 기준으로 정했다.

## 우선 확인: 데이터와 입력 처리

<!-- doc-check: {"kind":"review","path":"apps/api/app/analysis/pipeline.py","symbol":"run_analysis","sha256":"292eb7f62c3becab04160974911a73ebc9baae09eb50bc5b282496a110850f14"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/application/candidates.py","symbol":"reject_candidate","sha256":"f4dd79e5f10da01ba9ae93b920ecde3f239cd85b4ba013246028e3ae18257b5c"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/application/candidates.py","symbol":"apply_review","sha256":"3afb3e02f745cfcb66a16062cd23a8dece7714d612ca6d0270b6de47b16e635b"} -->

| 과제 | 현재 근거 | 완료 기준 |
| --- | --- | --- |
| 승인·병합 동시성 | 후보 승인·반려 잠금은 추가했지만 PostgreSQL 동시 요청 검증이 없음 | PostgreSQL에서 동시 요청 시 중복 Policy·Evidence 생성 방지 검증 |
| 파일·DB 불일치 처리 | 업로드는 파일 저장 후 DB commit, 삭제는 DB commit 후 파일 삭제 | 공유 파일을 보존하는 보상·정리 방식과 장애 테스트 |

완료: XLSX의 바이너리 건너뛰기 수정과 실제 업로드 테스트, 승인 후보 반려 방지,
일반 승인·병합의 입력 내 규칙 중복 제거, 소스 업데이트 승인·이력 추가.
검증: `apps/api/tests/test_source_updates.py`, `apps/api/tests/test_api_workflow.py`.

## 운영 확장 전에 처리

- **작업 큐와 복구:** 시작 시 전체 미완료 작업을 실패 처리한다.
  다중 인스턴스를 도입하기 전 작업 소유권, 재시도, 중복 실행 방지, 복구 기준을 구현한다.
- **비동기 업로드 경계:** async 라우터에서 동기 DB·파일 서비스를 직접 호출한다.
  실행 방식을 바꾸고 세션의 생성·종료가 같은 작업 경계에 있는지 검증한다.
- **DB 마이그레이션:** create_all과 개별 Enum 보완만 존재한다.
  기존 데이터가 있는 DB의 버전 전환·실패 복구 절차를 도입한다.
- **오류 메시지 정제:** 분석 예외 문자열을 사용자에게 노출되는 오류 필드에 저장한다.
  사용자 설명과 내부 진단을 분리하고 키·내부 주소·원문이 노출되지 않는지 테스트한다.
- **호출량 제한:** 현재 LLM rate limit은 프로세스 단위다.
  여러 worker를 도입할 때 공유 한도와 재시도 비용을 함께 관리한다.
- **접근 제어:** 현재 인증·조직별 권한이 없다.
  다중 사용자 운영 전 프로젝트 접근 검증과 테스트를 구현한다.

## 개발 품질 개선

- **시간 처리:** deprecated `utcnow()` 호출은 제거했다. 후속 과제는 시간대 없는 UTC 저장을
  시간대 있는 UTC로 전환하는 것이다.
  DB 컬럼·기존 데이터·API 응답 계약을 함께 검토한다.
- **형식·타입 검사:** 반환 타입 누락, 폭넓은 dict/Any, 긴 한 줄 표현을 점진적으로 정리한다.
  formatter와 정적 검사기를 도입하면 기존 코드 정리 범위와 CI 실행 명령을 명시한다.
- **분석 경계:** `analysis/`의 저장소·파서·LLM 결합을 기능 변경 시 분리한다.
- **의존성 재현:** 현재 Python 의존성은 버전 범위만 있다.
  잠금 방식과 최소 지원 Python·배포 Python 검증 기준을 정한다.
- **회귀 테스트 확장:** 병합·거절·LLM 오류 fallback·PostgreSQL 동시성 시나리오를 보완한다.
- **상태 검사:** 정적 `/health`와 별도로 DB·저장소 준비 상태를 확인할 필요를 검토한다.

작업을 완료하면 구현·테스트 링크를 기록하고 현재 동작 문서를 갱신한다.
