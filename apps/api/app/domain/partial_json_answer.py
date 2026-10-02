"""Read only a complete prefix of the answer string in a streamed JSON object."""
import json
import re


def partial_answer(content: str) -> str:
    match = re.search(r'"answer"\s*:\s*"', content)
    if not match:
        return ''
    value = content[match.end():]
    index = 0
    while index < len(value):
        char = value[index]
        if char == '"':
            return json.loads('"' + value[:index] + '"')
        if char == '\\':
            if index + 1 >= len(value):
                break
            length = 6 if value[index + 1] == 'u' else 2
            if index + length > len(value):
                break
            # A high surrogate needs its low surrogate before displaying Unicode.
            if length == 6 and 0xD800 <= int(value[index + 2:index + 6], 16) <= 0xDBFF:
                if index + 12 > len(value):
                    break
                length = 12
            index += length
        else:
            index += 1
    return json.loads('"' + value[:index] + '"')
