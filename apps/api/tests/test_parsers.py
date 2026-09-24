from app.analysis import extractor
from app.analysis.extractor import PolicyInterpretation, extract_candidate, extract_candidate_with_metadata
from io import BytesIO

from openpyxl import Workbook

from app.analysis.parsers import parse_code, parse_csv, parse_markdown, parse_xlsx


def test_markdown_preserves_heading_and_lines():
    chunks = parse_markdown("# 캠페인\n\n## 지원\n모집 중인 캠페인만 지원할 수 있다.")
    assert chunks[-1].document_path == "캠페인 > 지원"
    assert "모집 중" in chunks[-1].content
    assert chunks[-1].start_line == 3


def test_csv_turns_rows_into_traceable_chunks():
    chunks = parse_csv("정책,시간\n취소,72시간\n신청,24시간")
    assert len(chunks) == 2
    assert chunks[0].start_line == 2
    assert "시간: 72시간" in chunks[0].content


def test_code_only_keeps_policy_like_windows():
    chunks = parse_code("const label = 'x'\nif (campaign.status !== 'RECRUITING') {\n throw Error()\n}")
    assert len(chunks) == 1
    assert chunks[0].score >= 0.55
    assert extract_candidate(chunks[0], "apply.ts") is not None


def test_code_rejects_presentation_and_transport_mechanics():
    source = """if (isModalOpen) {
 history.back()
}
if (!response.ok) {
 throw Error('request failed')
}"""
    assert parse_code(source) == []


def test_code_does_not_mix_adjacent_policy_text_into_ui_condition():
    source = """const help = '구매 금액 제한은 10만원입니다'
if (isModalOpen) {
 history.back()
}"""
    assert parse_code(source, ".tsx") == []


def test_code_keeps_enforced_business_constraints():
    source = """if (order.status === 'SHIPPED') {
 throw Error('배송 후 취소 불가')
}
if (image.fileSize > 10 * MB) {
    throw Error('이미지 파일 크기는 10MB 이하여야 합니다')
}"""
    chunks = parse_code(source)
    assert len(chunks) == 2
    assert all(chunk.metadata["business_signal_score"] >= 3 for chunk in chunks)


def test_code_keeps_standalone_business_validation_call():
    chunks = parse_code("require(order.amount <= 100000, '주문 금액 한도 초과')")
    assert len(chunks) == 1


def test_llm_interpretation_becomes_korean_policy(monkeypatch):
    chunk = parse_code("if (order.status === 'SHIPPED') {\n throw Error('취소 불가')\n}")[0]
    monkeypatch.setattr(extractor.settings, "llm_api_key", "test-key")
    monkeypatch.setattr(extractor, "_llm_candidate", lambda *_: PolicyInterpretation(
        title="주문 취소 정책",
        summary="배송이 시작된 주문은 취소할 수 없습니다.",
        category="주문 > 취소",
        rules=["주문 상태가 배송 완료이면 취소를 거부합니다."],
        confidence=0.93,
        warnings=["배송 시작과 완료 상태의 구분은 추가 확인이 필요합니다."],
    ))

    candidate, metadata = extract_candidate_with_metadata(chunk, "orders/cancel.ts")

    assert candidate["title"] == "주문 취소 정책"
    assert candidate["rules"] == ["주문 상태가 배송 완료이면 취소를 거부합니다."]
    assert metadata["extractor"] == "litellm-structured-output"
    assert metadata["warnings"]


def test_llm_failure_falls_back_without_losing_candidate(monkeypatch):
    chunk = parse_code("if (campaign.status !== 'RECRUITING') {\n throw Error()\n}")[0]
    monkeypatch.setattr(extractor.settings, "llm_api_key", "test-key")

    def fail(*_):
        raise TimeoutError("timed out")

    monkeypatch.setattr(extractor, "_llm_candidate", fail)
    candidate, metadata = extract_candidate_with_metadata(chunk, "apply.ts")

    assert candidate is not None
    assert metadata == {"extractor": "deterministic-mvp", "fallback_reason": "TimeoutError"}


def test_xlsx_preserves_sheet_and_row():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "취소 정책"
    sheet.append(["항목", "시간"])
    sheet.append(["선정 취소", "72시간"])
    output = BytesIO()
    workbook.save(output)
    workbook.close()

    chunks = parse_xlsx(output.getvalue())
    assert len(chunks) == 1
    assert chunks[0].document_path == "취소 정책 > row 2"
    assert chunks[0].start_line == 2
    assert "시간: 72시간" in chunks[0].content
