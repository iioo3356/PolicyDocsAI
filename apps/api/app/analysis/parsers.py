import csv
import io
import re
from dataclasses import dataclass, field


@dataclass
class ParsedChunk:
    kind: str
    content: str
    start_line: int
    end_line: int
    document_path: str | None = None
    symbol_name: str | None = None
    score: float = 0.5
    metadata: dict = field(default_factory=dict)


POLICY_MARKERS = re.compile(
    r"\b(if|else if|switch|when|throw|require|check|validate|permission|disabled|"
    r"can[A-Z_]|isVisible|status|limit|max|min|amount|point|cancel|apply|approve)\b|"
    r"(권한|상태|취소|지원|신청|승인|포인트|금액|기간|가능|불가)",
    re.IGNORECASE,
)


def parse_markdown(text: str) -> list[ParsedChunk]:
    lines = text.splitlines()
    chunks: list[ParsedChunk] = []
    headings: list[str] = []
    start = 1
    buffer: list[str] = []

    def flush(end: int) -> None:
        nonlocal buffer, start
        content = "\n".join(buffer).strip()
        if content:
            chunks.append(ParsedChunk("heading", content, start, end, " > ".join(headings), score=0.75))
        buffer = []

    for number, line in enumerate(lines, 1):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            flush(number - 1)
            level = len(match.group(1))
            headings[:] = headings[: level - 1]
            headings.append(match.group(2).strip())
            start = number
        buffer.append(line)
        if len(buffer) >= 80:
            flush(number)
            start = number + 1
    flush(len(lines))
    return chunks


def parse_csv(text: str) -> list[ParsedChunk]:
    rows = list(csv.DictReader(io.StringIO(text)))
    result = []
    for index, row in enumerate(rows, 2):
        cleaned = {key: value for key, value in row.items() if key and value and value.strip()}
        if cleaned:
            content = "\n".join(f"{key}: {value}" for key, value in cleaned.items())
            result.append(ParsedChunk("csv_row", content, index, index, f"row {index}", score=0.7, metadata=cleaned))
    return result


def parse_xlsx(raw: bytes) -> list[ParsedChunk]:
    from openpyxl import load_workbook

    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    result: list[ParsedChunk] = []
    try:
        for sheet in workbook.worksheets:
            rows = sheet.iter_rows(values_only=True)
            first = next(rows, None)
            if first is None:
                continue
            headers = [str(value).strip() if value is not None else f"column_{index + 1}" for index, value in enumerate(first)]
            for row_number, row in enumerate(rows, 2):
                values = []
                metadata = {}
                for index, value in enumerate(row):
                    if value is None or str(value).strip() == "":
                        continue
                    header = headers[index] if index < len(headers) else f"column_{index + 1}"
                    rendered = str(value).strip()
                    values.append(f"{header}: {rendered}")
                    metadata[header] = rendered
                if values:
                    result.append(ParsedChunk(
                        "xlsx_row", "\n".join(values), row_number, row_number,
                        f"{sheet.title} > row {row_number}", score=0.7, metadata=metadata,
                    ))
    finally:
        workbook.close()
    return result


def parse_code(text: str) -> list[ParsedChunk]:
    lines = text.splitlines()
    interesting = [i for i, line in enumerate(lines) if POLICY_MARKERS.search(line)]
    windows: list[tuple[int, int]] = []
    for index in interesting:
        start, end = max(0, index - 4), min(len(lines), index + 8)
        if windows and start <= windows[-1][1]:
            windows[-1] = (windows[-1][0], max(windows[-1][1], end))
        else:
            windows.append((start, end))
    chunks = []
    for start, end in windows:
        content = "\n".join(lines[start:end]).strip()
        marker_count = len(POLICY_MARKERS.findall(content))
        score = min(0.95, 0.45 + marker_count * 0.08)
        chunks.append(ParsedChunk("code", content, start + 1, end, score=score))
    return chunks
