# Policy Docs Agent

Policy Docs Agent는 서비스 코드와 운영 문서에 흩어진 업무 규칙을 찾아 **검토 가능한 한글 정책 문서**로 만드는 에이전트입니다.

코드에서 발견한 내용을 바로 공식 정책으로 확정하지 않습니다. AI가 정책 후보와 근거를 만들고, 사람이 내용을 수정하거나 승인한 결과만 Policy Docs와 근거 기반 Chat에 사용합니다.

예를 들어 다음 코드가 있다면:

```ts
if (order.status === "SHIPPED") {
  return false;
}
```

다음과 같은 정책 후보를 생성합니다.

```text
제목: 배송 주문 취소 제한
요약: 배송이 시작된 주문은 취소할 수 없습니다.
규칙: 주문 상태가 SHIPPED이면 취소 요청을 거부합니다.
근거: src/orders/cancel.ts:21-23
```

## 무엇을 할 수 있나요?

- 프로젝트별 Source와 Policy 관리
- TypeScript, JavaScript, Kotlin 코드 ZIP 업로드
- Markdown, CSV, XLSX 운영 문서 업로드
- 코드 의미를 LiteLLM 모델로 해석해 한글 정책 후보 생성
- 정책 후보의 제목, 요약, 카테고리, 규칙 편집
- 후보 승인, 거절 및 기존 정책 병합
- 승인된 정책과 원본 파일·라인·코드 근거 보존
- 승인된 정책 근거 Chat과 소스 업데이트 안내·승인 후 수정 이력
- 등록 Source와 미승인 분석 결과 삭제
- AI 호출, fallback 및 분석 범위 로그 확인

## 코드 분석 방식

React와 Next.js 프로젝트는 ZIP 안의 모든 파일을 분석하지 않습니다. 실제 화면에서 사용하는 코드만 보기 위해 route entry에서 import 관계를 따라갑니다. TypeScript, TSX, JavaScript, JSX 문법은 `tree-sitter` AST로 파싱하며 일반 import뿐 아니라 재수출(`export ... from`), 동적 `import()`, `require()`도 추적합니다.

```text
Route entry
  → 화면 Component
  → 사용 중인 Component와 Hook
  → 연결된 업무 규칙
  → Policy Candidate
```

route entry로 인식하는 대표 파일은 다음과 같습니다.

- `src/app/**/page.tsx`
- `src/pages/**`
- `src/App.tsx`
- `src/main.tsx`
- `src/routes.tsx`
- `src/router.tsx`

`api.ts`, `client.ts`, `config.ts`, `env.ts`, `constants.ts`, 생성 코드와 route에서 도달할 수 없는 미사용 코드는 분석에서 제외합니다. React route를 찾지 못하는 Kotlin 또는 일반 코드 ZIP은 기존 키워드 기반 전체 코드 탐색으로 전환합니다.

선별된 코드에서는 AST로 실제 조건문·상태 분기·검증 호출을 분리한 뒤, 업무 결과·제한과 실제 분기·검증이 함께 있는 구간만 찾습니다.
취소·환불·신청·승인·결제·금액·기간·자격·상태 전이·파일 제한 등을 업무 신호로 사용하고, 모달 열기·뒤로가기·렌더링·스타일 같은 화면 구현만 있는 구간은 AI 호출 전에 제외합니다.
이 사전 필터를 통과한 구간을 LiteLLM에 전달하고 JSON Schema로 다음 결과를 생성합니다.

- 한글 정책 제목과 요약
- 카테고리
- 조건과 처리 결과
- 신뢰도
- 불확실한 해석에 대한 경고

AI API 키가 없거나 호출이 실패하면 업로드 작업 전체를 실패시키지 않고 로컬 휴리스틱 추출기로 전환합니다.

## 처리 흐름

```text
Source 업로드
  → 안전성 검사 및 파일 선별
  → route/import 도달성 분석
  → 정책 가능성이 있는 코드 Chunk 추출
  → LiteLLM 한글 의미 해석
  → Policy Candidate 생성
  → 사람의 검토·수정
  → 승인된 Policy + Rule + Evidence
  → Policy Docs와 근거 기반 Chat
```

## 기술 구성

| 영역 | 기술 |
| --- | --- |
| Web | Next.js 15, React 19, TypeScript, TanStack Query |
| API | FastAPI, Python 3.11+, SQLAlchemy, Pydantic, tree-sitter |
| AI | LiteLLM, 기본 모델 `gemini/gemini-3.1-flash-lite` |
| DB | PostgreSQL 16, pgvector; 로컬 SQLite fallback |
| 실행 | Docker Compose |

```text
apps/web     Next.js 사용자 화면
apps/api     FastAPI와 코드 분석 파이프라인
storage      로컬 실행 시 업로드 파일 저장소
```

## 빠른 시작: Docker

### 1. 요구 사항

- Docker Desktop
- Gemini API key 또는 LiteLLM이 지원하는 다른 모델의 API key

먼저 Docker Desktop을 실행하고 daemon이 준비됐는지 확인합니다.

```bash
docker info
```

### 2. 환경변수 설정

저장소 루트에서 예제 파일을 복사합니다.

```bash
cp .env.example .env
```

`.env`에 Gemini API key를 입력합니다.

```env
LLM_API_KEY=your_gemini_api_key
LLM_MODEL=gemini/gemini-3.1-flash-lite
LLM_TIMEOUT_SECONDS=45
LLM_MIN_INTERVAL_SECONDS=13
```

`LLM_MIN_INTERVAL_SECONDS=13`은 Gemini 무료 티어의 분당 요청 제한을 피하기 위한 기본 간격입니다. API key는 API 컨테이너에만 전달되며 브라우저 번들에는 포함되지 않습니다.

기존 환경의 다음 변수도 호환됩니다.

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.1-flash-lite
```

### 3. 서비스 실행

```bash
docker compose up -d --build
docker compose ps
```

정상적으로 실행되면 다음 주소를 사용할 수 있습니다.

- Web: http://localhost:3000
- API와 Swagger: http://localhost:8000/docs
- API 상태 확인: http://localhost:8000/health
- PostgreSQL: `localhost:5432`

### 4. 사용 방법

1. Web에서 Project를 생성합니다.
2. `Sources`에서 코드 ZIP 또는 운영 문서를 업로드합니다.
3. 분석 완료 후 `Policy Review`에서 AI가 생성한 후보와 원본 근거를 확인합니다.
4. 내용을 수정한 다음 승인하거나 필요 없는 후보를 거절합니다.
5. `Policy Docs`에서 승인된 정책을 확인합니다.
6. `AI Chat`에서 승인된 정책에 관해 질문합니다.

정책을 바꾸려면 소스 추가에서 기존 Source를 선택해 최신 파일을 업로드하고 정책 관리에서 변경 전후를 검토·승인하세요. 승인 후 같은 정책에 수정 이력이 남습니다. 기존 소스와 근거는 보존합니다. [소스 업데이트](docs/source-updates.md)

## 로그 확인

API와 AI 분석 로그를 실시간으로 확인합니다.

```bash
docker compose logs -f api
```

주요 로그 예시는 다음과 같습니다.

```text
Policy Docs API configuration ai_enabled=True model=gemini/gemini-3.1-flash-lite
Code scope selected mode=route-reachable route_entries=3 selected_files=14 ignored_files=82
AI policy interpretation started ...
AI policy interpretation completed ... confidence=0.91
Source analysis completed ... ai_candidates=4 fallback_candidates=0
```

`fallback_candidates`가 증가하면 API key, 모델명, quota 또는 네트워크 오류를 로그에서 확인합니다.

## 종료와 데이터 초기화

서비스만 종료하면 DB와 업로드 데이터는 Docker named volume에 보존됩니다.

```bash
docker compose down
```

DB와 업로드 데이터를 모두 삭제할 때만 `-v`를 사용합니다. 이 작업은 복구하기 어렵습니다.

```bash
docker compose down -v
```

## 로컬 개발

요구 사항은 Python 3.11+, Node.js 20+, Docker입니다. PostgreSQL만 Docker로 실행합니다.

```bash
cp .env.example .env
docker compose up -d db
```

API 실행:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

다른 터미널에서 Web을 실행합니다.

```bash
cd apps/web
npm install
npm run dev
```

DB 없이 API를 빠르게 확인하려면 `.env`를 다음과 같이 변경합니다.

```env
DATABASE_URL=sqlite:///./policy_docs.db
```

## 다른 LLM 사용

LiteLLM provider/model 형식에 맞춰 환경변수만 변경하면 됩니다.

```env
LLM_API_KEY=provider_api_key
LLM_MODEL=provider/model-name
```

자체 LiteLLM Proxy를 사용하는 경우:

```env
LLM_API_KEY=proxy_virtual_key
LLM_MODEL=policy-model
LLM_API_BASE=http://litellm-proxy:4000
```

모델을 변경한 뒤에는 API 컨테이너를 다시 생성합니다.

```bash
docker compose up -d --build api
```

## 테스트

백엔드 테스트:

```bash
cd apps/api
pytest
```

프런트엔드 production build:

```bash
cd apps/web
npm run build
```

저장소 루트에서는 다음 명령도 사용할 수 있습니다.

```bash
make test
```

## 안전장치

- ZIP 경로 탈출(zip-slip) 차단
- 최대 업로드 크기 제한
- ZIP 내부 파일 수와 압축 해제 크기 제한
- `node_modules`, `dist`, `build`, `.git`, `vendor`, `coverage` 제외
- AI 출력의 Pydantic/JSON Schema 검증
- 업로드된 코드 안의 지시문을 실행하지 않고 분석 데이터로만 처리
- AI 결과와 사람이 승인한 공식 Policy 분리
- 승인 시 원본 경로, 라인과 excerpt를 Evidence로 보존
- Chat은 승인된 Policy에서 근거를 찾은 경우에만 응답

## 현재 제한

- TypeScript/JavaScript import 관계는 tree-sitter AST로 분석하지만 타입과 런타임 값까지 해석하는 의미 분석은 아닙니다.
- 런타임에 계산되는 import 경로와 복잡한 alias 설정은 놓칠 수 있습니다.
- Kotlin은 호출 그래프가 아니라 정책 키워드 주변 구간을 분석합니다.
- 자동 정책 병합과 자연어 conflict 판정은 제공하지 않습니다.
- 사용자 인증과 조직별 권한 관리는 포함하지 않습니다.
- 분석 작업은 현재 FastAPI process의 background task로 실행됩니다. 운영 환경에서는 별도 worker가 필요합니다.
- Chat은 승인 정책으로 답하며 변경 요청에는 관련 소스 업데이트를 안내합니다. [상세](docs/policy-chat.md)

개발 문서: [문서 목록](docs/README.md) · [개발 규칙](docs/development-rules.md)
