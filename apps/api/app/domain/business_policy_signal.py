import re


DECISION = re.compile(
    r"\b(if|else\s+if|switch|case|when|throw|require|check|validate|assert)\b|"
    r"===|!==|==|!=|>=|<=|(?<![-=])>(?!=)|(?<![-=])<(?!=)", re.IGNORECASE,
)
ENFORCEMENT = re.compile(
    r"\b(throw|require|check|validate|assert|deny|forbid|reject|eligible|permission|allowed)\b|"
    r"\bcan[A-Z_]\w*|\breturn\s+false\b|"
    r"(거부|금지|허용|검증|필수|자격|권한|불가|가능)", re.IGNORECASE,
)
BUSINESS_OUTCOME = re.compile(
    r"\b(cancel|refund|return|exchange|apply|approve|reject|payment|purchase|order|buyer|seller|"
    r"point|reward|benefit|coupon|discount|settlement|withdraw|eligib|quota|deadline|"
    r"amount|price|limit|maximum|minimum|max|min|file.?size|image.?ratio)\w*\b|"
    r"(취소|환불|반품|교환|신청|승인|반려|결제|구매|주문|구매자|판매자|포인트|리워드|혜택|"
    r"쿠폰|할인|정산|출금|캠페인|자격|한도|마감|금액|가격|최대|최소|파일.?크기|이미지.?비율)",
    re.IGNORECASE,
)
CONSTRAINT = re.compile(
    r"\b(limit|max|min|amount|price|count|quota|deadline|period|duration|age|size|ratio)\w*\b|"
    r"\b\d+(?:\.\d+)?\s*(?:ms|sec|second|minute|hour|day|kb|mb|gb|%|px)\b|"
    r"(제한|한도|마감|기간|이내|이상|이하|초과|미만|최대|최소|금액|수량|횟수|나이|크기|비율)",
    re.IGNORECASE,
)
DOMAIN_STATE = re.compile(
    r"\b(status|state|phase)\b[\s\S]{0,80}(?:===|!==|==|!=|\b(?:is|in)\b)[\s\S]{0,40}"
    r"(?:['\"]?[A-Z][A-Z0-9_]{2,}|취소|승인|반려|완료|진행|모집|종료)", re.IGNORECASE,
)
UI_MECHANICS = re.compile(
    r"\b(modal|dialog|drawer|button|tooltip|render|visible|isOpen|setOpen|onClick|navigate|history|"
    r"router|back|scroll|focus|hover|style|className|tabIndex)\b|"
    r"(모달|다이얼로그|버튼|렌더|노출|뒤로가기|스크롤|포커스|스타일)", re.IGNORECASE,
)


def business_policy_score(text: str) -> int:
    """Score code that makes a business decision, excluding presentation mechanics."""
    if not DECISION.search(text):
        return 0
    has_outcome = bool(BUSINESS_OUTCOME.search(text))
    enforcement = bool(ENFORCEMENT.search(text))
    constraint = bool(CONSTRAINT.search(text))
    state_rule = bool(DOMAIN_STATE.search(text))
    score = int(has_outcome) * 2 + int(enforcement) * 2 + int(constraint) * 2 + int(state_rule) * 2
    if UI_MECHANICS.search(text) and not (has_outcome or constraint or state_rule):
        score -= 3
    return max(score, 0)


def is_business_policy_code(text: str) -> bool:
    return business_policy_score(text) >= 3
