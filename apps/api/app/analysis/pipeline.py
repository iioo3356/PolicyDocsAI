import hashlib
import logging
import zipfile
from app.domain.clock import utc_now_naive
from pathlib import Path, PurePosixPath

from sqlalchemy.orm import Session

from ..config import settings
from ..models import AnalysisJob, JobStatus, PolicyCandidate, Source, SourceChunk, SourceFile
from app.application.source_versions import suggest_policy
from .extractor import extract_candidate_with_metadata
from .parsers import parse_code, parse_csv, parse_markdown, parse_xlsx
from .reachability import select_reachable_react_files

logger = logging.getLogger("uvicorn.error")

LANGUAGES = {".ts": "typescript", ".tsx": "typescript", ".js": "javascript", ".jsx": "javascript", ".kt": "kotlin"}
IGNORED_PARTS = {"node_modules", "dist", "build", ".git", "vendor", "coverage"}


def _safe_zip_files(archive: zipfile.ZipFile):
    total = 0
    files = [item for item in archive.infolist() if not item.is_dir()]
    if len(files) > settings.max_zip_files:
        raise ValueError("ZIP 파일 수 제한을 초과했습니다.")
    for item in files:
        path = PurePosixPath(item.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("안전하지 않은 ZIP 경로가 포함되어 있습니다.")
        total += item.file_size
        if total > settings.max_extracted_bytes:
            raise ValueError("ZIP 압축 해제 크기 제한을 초과했습니다.")
        if not IGNORED_PARTS.intersection(path.parts):
            yield item


def _documents(source: Source):
    original = settings.storage_path / source.storage_key
    if source.kind.value != "CODE_ZIP":
        yield source.name, original.read_bytes()
        return
    with zipfile.ZipFile(original) as archive:
        for item in _safe_zip_files(archive):
            suffix = Path(item.filename).suffix.lower()
            if suffix in LANGUAGES:
                yield item.filename, archive.read(item)


def run_analysis(db: Session, source: Source, job: AnalysisJob) -> None:
    logger.info(
        "Source analysis started source_id=%s name=%s kind=%s ai_enabled=%s model=%s",
        source.id, source.name, source.kind.value, bool(settings.llm_api_key), settings.llm_model,
    )
    source.status = job.status = JobStatus.PROCESSING
    job.stage, job.progress = "parse", 10
    db.commit()
    try:
        candidate_count = chunk_count = file_count = ai_count = fallback_count = 0
        documents = list(_documents(source))
        selection = {"mode": "document", "entries": 1, "selected": len(documents), "ignored": 0}
        if source.kind.value == "CODE_ZIP":
            documents, selection = select_reachable_react_files(documents)
            logger.info(
                "Code scope selected source_id=%s mode=%s route_entries=%s selected_files=%s ignored_files=%s",
                source.id, selection["mode"], selection["entries"], selection["selected"], selection["ignored"],
            )
        for path, raw in documents:
            if Path(path).suffix.lower() != ".xlsx" and b"\x00" in raw[:4096]:
                continue
            text = raw.decode("utf-8", errors="replace")
            suffix = Path(path).suffix.lower()
            language = LANGUAGES.get(suffix, "markdown" if suffix in {".md", ".markdown"} else "xlsx" if suffix == ".xlsx" else "csv")
            source_file = SourceFile(source_id=source.id, project_id=source.project_id, path=path, language=language,
                                     content_hash=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
            db.add(source_file)
            db.flush()
            file_count += 1
            parsed = (parse_code(text) if suffix in LANGUAGES else parse_csv(text) if suffix == ".csv"
                      else parse_xlsx(raw) if suffix == ".xlsx" else parse_markdown(text))
            logger.info("Source file parsed source_id=%s path=%s chunks=%s", source.id, path, len(parsed))
            for item in parsed:
                chunk = SourceChunk(source_file_id=source_file.id, project_id=source.project_id, chunk_type=item.kind,
                                    symbol_name=item.symbol_name, document_path=item.document_path, start_line=item.start_line,
                                    end_line=item.end_line, content=item.content, candidate_score=item.score,
                                    chunk_metadata=item.metadata)
                db.add(chunk)
                db.flush()
                chunk_count += 1
                extracted, extraction_metadata = extract_candidate_with_metadata(item, path)
                if extracted:
                    if extraction_metadata.get("extractor") == "litellm-structured-output":
                        ai_count += 1
                    else:
                        fallback_count += 1
                    db.add(PolicyCandidate(project_id=source.project_id, source_id=source.id, source_chunk_id=chunk.id,
                                           proposed_policy_id=suggest_policy(db, source, chunk),
                                           extraction_data={**extraction_metadata, **extracted}, **extracted))
                    candidate_count += 1
        source.discovered_policy_count = candidate_count
        source.status = job.status = JobStatus.COMPLETED
        job.stage, job.progress = "completed", 100
        job.stats = {"files": file_count, "chunks": chunk_count, "candidates": candidate_count,
                     "ai_candidates": ai_count, "fallback_candidates": fallback_count,
                     "scope": selection}
        job.completed_at = utc_now_naive()
        db.commit()
        logger.info(
            "Source analysis completed source_id=%s files=%s chunks=%s candidates=%s ai_candidates=%s fallback_candidates=%s",
            source.id, file_count, chunk_count, candidate_count, ai_count, fallback_count,
        )
    except Exception as exc:
        logger.exception("Source analysis failed source_id=%s error_type=%s", source.id, type(exc).__name__)
        db.rollback()
        source = db.get(Source, source.id)
        job = db.get(AnalysisJob, job.id)
        source.status = job.status = JobStatus.FAILED
        source.error_message = job.error_message = str(exc)
        job.stage = "failed"
        job.completed_at = utc_now_naive()
        db.commit()
