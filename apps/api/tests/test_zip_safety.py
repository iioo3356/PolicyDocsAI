import zipfile
from io import BytesIO

import pytest

from app.analysis.pipeline import _safe_zip_files


def archive(name: str) -> zipfile.ZipFile:
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as target:
        target.writestr(name, "hello")
    stream.seek(0)
    return zipfile.ZipFile(stream)


def test_zip_slip_is_rejected():
    with archive("../secret.ts") as zipped:
        with pytest.raises(ValueError, match="안전하지 않은"):
            list(_safe_zip_files(zipped))


def test_vendor_directories_are_ignored():
    with archive("node_modules/pkg/index.js") as zipped:
        assert list(_safe_zip_files(zipped)) == []

