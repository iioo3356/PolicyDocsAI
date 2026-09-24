import logging
from app.config import settings

logger = logging.getLogger(__name__)


def store_bytes(storage_key: str, raw: bytes) -> None:
    destination = settings.storage_path / storage_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        destination.write_bytes(raw)


def remove_file(storage_key: str) -> None:
    storage_root = settings.storage_path.resolve()
    stored_file = (storage_root / storage_key).resolve()
    if stored_file.is_relative_to(storage_root):
        try:
            stored_file.unlink(missing_ok=True)
        except OSError:
            logger.warning("Deleted Source record but could not remove stored file: %s", stored_file)
