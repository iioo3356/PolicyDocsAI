import uuid
from datetime import datetime
from app.domain.clock import utc_now_naive

def uid() -> str:
    return str(uuid.uuid4())

def now() -> datetime:
    return utc_now_naive()
