import re

def tokens(text: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[\w가-힣]{2,}", text)}
