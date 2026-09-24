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
