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

<!-- doc-check: {"kind":"review","path":"apps/api/app/application/chat.py","symbol":"chat","sha256":"29d48f6a8ccce607fcc4c6d21293f5999bd53fcb566c82a33c225130a7e3be30"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/application/chat_source_guidance.py","symbol":"source_guidance","sha256":"9c702df649dca9c057dcc267561e7d6210d77794c4d78963167c4a2a400a38f9"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/presentation/routes/chat.py","symbol":"retired_chat_edit","sha256":"edf64088868a0cc03088b925bc6c866349c9fb8070f38242b731fd44fbdeb2d1"} -->
<!-- doc-check: {"kind":"review","path":"apps/api/app/infrastructure/chat_llm.py","symbol":"","sha256":"da8865c8b6d78e40b76dabd8776d6d747480d2599ba6aa763c78e068ad51c3ee"} -->
