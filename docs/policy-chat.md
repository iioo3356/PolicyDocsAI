# 승인 정책 질의와 소스 안내

[문서 목록](README.md) · [소스 업데이트](source-updates.md)

## 사용자 흐름

- 채팅은 해당 프로젝트에서 승인된 현재 정책의 요약·규칙을 근거로 답한다.
- 정책을 변경해 달라는 요청에는 관련 소스의 업데이트 버튼과 절차를 안내한다.
- 소스에 변경을 반영하고 다시 업로드한 뒤 정책 관리에서 변경안을 검토·승인한다.
- 채팅에서는 변경안 생성, 정책 수정·삭제, 승인 상태 변경을 수행하지 않는다.
- 답변이 하나의 정책에 근거하면 다음 대화의 대상으로 그 정책을 선택한다.
- 소스 연결이 없거나 대상을 찾지 못하면 일반 소스 추가 화면으로 안내한다.

## 요청과 응답

`POST /projects/{project_id}/chat` 요청 필드:

| 필드 | 의미 |
| --- | --- |
| question | 질문 또는 소스 업데이트가 필요한 요청, 2~2000자 |
| policy_id | 대상 승인 정책 ID, 없으면 null |
| history | user/assistant 대화 최대 8개 메시지 |
| top_k | 답변 근거 정책 수, 기본 5, 최대 10 |

응답에는 answer, grounded, related_policies, citations, action, source_suggestions가 있다.
action은 answer, clarify, update_source 중 하나다. proposal/change는 반환하지 않는다.
source_suggestions는 정책 ID·제목과 업데이트할 소스 ID·이름을 제공한다.
버튼은 소스 패널의 replace_source_id 쿼리로 연결된다.

## 근거와 실패 처리

- 다른 프로젝트 또는 미승인 대상 정책은 404로 거부한다.
- 선택한 정책 또는 토큰 일치도로 선별한 최대 40개 정책을 모델에 제공한다.
- 컨텍스트가 100,000자를 넘으면 처리 범위를 줄이도록 안내한다.
- 외부 모델 호출 중 DB 트랜잭션을 유지하지 않는다.
- 답변이 참조한 정책 ID를 검증하며 답변 생성 중 정책 내용이 바뀌면 재질의를 안내한다.
- 소스 갱신으로 수정된 정책은 최신 수정의 소스 chunk만 답변 근거로 제공한다.
- 과거 채팅 수정 이력이 있는 정책은 이전 수정 이력으로 표시한다.
- 명시적 수정 요청은 로컬에서 소스 안내로 처리하므로 AI 키가 없어도 안내할 수 있다.
- 그 외 요청은 모델이 answer/clarify/update_source로 분류한다. update_source 안내 문구는 서버가 만든다.
- AI 키가 없거나 호출·응답 검증이 실패하면 관련 승인 정책 원문을 안내한다.
- 어떤 분류 결과도 DB 정책 변경을 허용하지 않는다. 모델은 사용자 권한을 판정하지 않는다.
- 구조·ID 검증은 자연어 답변의 모든 문장이 사실임을 보장하지 않는다.

## 이전 수정 기능과의 호환성

기존 chat_proposals 테이블과 과거 policy_revisions는 보존한다.
기존 `/projects/{project_id}/chat/proposals/{proposal_id}/confirm`과 cancel API는 410을 반환한다.
과거의 미확정 제안으로 정책을 변경할 수 없다.
일반 대화는 브라우저 패널 상태에만 보관하며 DB에 저장하지 않는다.
현재 인증·조직 권한 기능은 별도 구현되어 있지 않다.

## 구현과 검증

- `apps/api/app/application/chat.py`: 읽기 전용 답변 및 소스 안내 분기
- `apps/api/app/application/chat_source_guidance.py`: 최신 관련 소스 조회
- `apps/api/app/infrastructure/chat_llm.py`: 읽기 전용 구조화 출력 계약
- `apps/web/features/workspace/Chat.tsx`: 대화와 소스 업데이트 링크
- `apps/api/tests/test_chat.py`: 범위·근거·fallback·변경 중 재질의
- `apps/api/tests/test_chat_llm.py`: 모델 출력에서 update 액션 거부
- `apps/api/tests/test_api_workflow.py`: 소스 안내와 이전 수정 API 차단

자동 테스트는 가짜 모델 응답을 사용하며 실제 운영 정책을 외부 모델로 전송하지 않는다.

<!-- doc-check: {"kind": "review", "path": "apps/api/app/application/chat.py", "symbol": "chat", "sha256": "a9734af6d5c9a621e7acf8d4648f017118ee9bb0bf87462f898280fb772a87cd"} -->
<!-- doc-check: {"kind": "review", "path": "apps/api/app/application/chat_source_guidance.py", "symbol": "source_guidance", "sha256": "9c702df649dca9c057dcc267561e7d6210d77794c4d78963167c4a2a400a38f9"} -->
<!-- doc-check: {"kind": "review", "path": "apps/api/app/presentation/routes/chat.py", "symbol": "retired_chat_edit", "sha256": "edf64088868a0cc03088b925bc6c866349c9fb8070f38242b731fd44fbdeb2d1"} -->
<!-- doc-check: {"kind": "review", "path": "apps/api/app/infrastructure/chat_llm.py", "symbol": "", "sha256": "14f68b89bfc6182e5f003655ec6b03ab8171eb9a40e125c46c8836f31e66042f"} -->

## 실시간 응답

- 웹 채팅은 `POST /projects/{project_id}/chat/stream`의 NDJSON 스트림을 읽는다.
- `delta` 이벤트의 text는 모델이 생성 중인 답변 조각이다. 화면에 즉시 이어 붙인다.
- `done` 이벤트의 response는 기존 ChatResponse와 같으며 최종 검증 답변으로 교체한다.
- 근거와 관련 정책·소스 링크는 완료 후 표시한다. 생성 중 텍스트는 아직 검증 전이다.
- 모델 출력은 JSON 구조를 유지하며 answer 문자열만 점진적으로 표시한다.
- 모델 실패·잘못된 출력·근거 불일치 시 임시 답변을 최종 fallback 또는 안내로 교체한다.
- 연결이 완료 이벤트 없이 끊기면 실패로 표시하고 질문을 보존해 재시도할 수 있다.
- 패널을 닫으면 브라우저 요청을 취소한다. 서버 모델 스트림도 닫고 DB 세션을 정리한다.
- API 키가 없거나 로컬 안내인 경우 생성 과정 없이 done 이벤트로 바로 전달한다.
- 일반 JSON 응답 API는 호환성을 위해 유지한다.
- 스트림 시작 전 프로젝트·대상 정책·요청을 검증하고 404·422 상태 코드를 유지한다.
- 스트리밍 회귀 테스트: `apps/api/tests/test_chat_stream.py`.
