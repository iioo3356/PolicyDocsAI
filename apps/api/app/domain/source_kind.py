import enum


class SourceKind(str, enum.Enum):
    CODE_ZIP = "CODE_ZIP"
    MARKDOWN = "MARKDOWN"
    CSV = "CSV"
    XLSX = "XLSX"
