import re


def requests_policy_edit(question: str) -> bool:
    """Recognize explicit requests for routing to source upload; never authorize writes."""
    text = re.sub(r'"[^"\n]*"|\'[^\'\n]*\'|“[^”]*”|`[^`]*`', '', question)
    if re.search(r'하지\s*마|하지\s*말|바꾸지|수정하지|변경하지|예를\s*들|가정|방법|어떻게|무슨\s*뜻|바꿔도|수정해도|변경해도|바꿔야|수정해야|변경해야|\b(?:how|can|could|would|should|example|if)\b', text, re.I):
        return False
    return bool(re.search(
        r'바꿔|고쳐|없애\s*줘|(?:수정|변경|추가|삭제|정정|적용|반영)(?:해|해주세요|해\s*줘|해\s*주세요|하라|하세요)|'
        r'\b(?:change|update|replace|modify)\b', text, re.I,
    ))
