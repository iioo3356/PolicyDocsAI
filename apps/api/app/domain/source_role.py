import re
from .application_error import ApplicationError

def normalize_source_role(role: str) -> str:
    normalized = role.strip()
    if not normalized or len(normalized) > 50 or not re.fullmatch(r"[\w가-힣 ./_-]+", normalized):
        raise ApplicationError(400, "역할은 1~50자의 문자, 숫자, 공백, ., /, _, -만 사용할 수 있습니다.")
    return normalized
