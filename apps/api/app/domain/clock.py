"""UTC timestamps compatible with the existing timezone-naive DB columns."""
from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """Preserve the existing DB/API representation until a timezone migration."""
    return datetime.now(UTC).replace(tzinfo=None)
