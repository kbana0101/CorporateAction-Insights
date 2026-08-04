"""Stage 3.5: Parse PDFs with Docling and chunk them for the ingest stage.

Given a ``corporate_actions`` row with ``local_pdf_path`` set and
``parsed_at`` NULL, this stage:

1. Loads the PDF into a DoclingDocument (OCR off by default).
2. If the extracted text is near-empty, retries with OCR enabled.
3. Runs the chunker to produce a list of {text, metadata} dicts.
4. Writes ``<stem>.chunks.json`` (and optionally ``<stem>.docling.json``)
   under ``PARSED_DIR``.
5. Stamps ``parsed_at`` + ``chunk_count`` on the DB row on success, or
   ``parse_error`` on failure (with ``parse_attempts`` incremented).
"""
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .chunker import chunk_document
from .config import (
    PARSE_BATCH_SIZE,
    PARSED_DIR,
    PARSED_KEEP_FULL,
    SKIP_SUBJECT_SUBSTRINGS,
    get_supabase_client,
)
from .paths import (
    docling_json_path_for,
    parsed_chunks_path_for,
    resolve_pdf_path,
)

logger = logging.getLogger(__name__)

# --- Error kinds ------------------------------------------------------------

PARSE_ERROR_CORRUPT = "corrupt_pdf"
PARSE_ERROR_ENCRYPTED = "encrypted"
PARSE_ERROR_NO_TEXT = "no_text_layer"
PARSE_ERROR_EMPTY_CHUNKS = "empty_chunks"
PARSE_ERROR_TIMEOUT = "docling_timeout"
PARSE_ERROR_UNKNOWN = "unknown_error"

_NON_RETRYABLE_ERRORS = {
    PARSE_ERROR_CORRUPT,
    PARSE_ERROR_ENCRYPTED,
    PARSE_ERROR_NO_TEXT,
    PARSE_ERROR_EMPTY_CHUNKS,
}

# --- Docling converter singletons ------------------------------------------

# We build two converters (OCR off, OCR on) and reuse them across the batch —
# model load is the expensive part, so amortising is important. A lock guards
# lazy init in case someone calls parse_pdf from multiple threads.
_converter_lock = threading.Lock()
_converter_no_ocr = None
_converter_with_ocr = None

# Rough threshold for "did we actually extract text?" — below this we retry
# with OCR. Averages a couple of sentences per page, which is a reasonable
# floor for any real filing.
MIN_CHARS_PER_PAGE = 50


def _make_converter(do_ocr):
    # type: (bool) -> Any
    """Build a Docling DocumentConverter tuned for our workload.

    Kept internal so the import graph stays lazy — nothing pulls torch until
    the first parse call.
    """
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        AcceleratorOptions,
        PdfPipelineOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = do_ocr
    pipeline_options.do_table_structure = True
    # Deterministic on the cron host — no GPU probing surprises.
    pipeline_options.accelerator_options = AcceleratorOptions(device="cpu")

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )


def _get_converter(do_ocr):
    # type: (bool) -> Any
    global _converter_no_ocr, _converter_with_ocr
    with _converter_lock:
        if do_ocr:
            if _converter_with_ocr is None:
                logger.info("parser: initialising Docling converter (OCR=on)")
                _converter_with_ocr = _make_converter(do_ocr=True)
            return _converter_with_ocr
        if _converter_no_ocr is None:
            logger.info("parser: initialising Docling converter (OCR=off)")
            _converter_no_ocr = _make_converter(do_ocr=False)
        return _converter_no_ocr


# --- PDF text-content probing ------------------------------------------------

def _extracted_text_stats(docling_doc):
    # type: (Any) -> Tuple[int, int]
    """Return (total_chars, page_count) for a parsed DoclingDocument."""
    total_chars = 0

    if hasattr(docling_doc, "iterate_items"):
        for entry in docling_doc.iterate_items():
            item = entry[0] if isinstance(entry, tuple) else entry
            text = getattr(item, "text", None)
            if text:
                total_chars += len(str(text))
    else:
        for attr in ("texts", "lists"):
            for item in getattr(docling_doc, attr, None) or []:
                text = getattr(item, "text", None)
                if text:
                    total_chars += len(str(text))

    pages = getattr(docling_doc, "pages", None)
    if isinstance(pages, dict):
        page_count = len(pages)
    elif isinstance(pages, list):
        page_count = len(pages)
    else:
        page_count = 1

    return total_chars, max(1, page_count)


def parse_pdf(pdf_path):
    # type: (Path) -> Any
    """Parse a PDF and return a DoclingDocument.

    OCR is attempted only when the initial (OCR-off) pass yields near-empty
    text — this is the fallback path from the design doc. Raises on hard
    failures (corrupt/encrypted PDFs) so the caller can flag them.
    """
    logger.info("parser: parsing %s (OCR off)", pdf_path.name)
    converter = _get_converter(do_ocr=False)
    try:
        result = converter.convert(str(pdf_path))
    except Exception as exc:
        # Docling wraps most PDF errors — classify the ones we know.
        msg = str(exc).lower()
        if "encrypt" in msg or "password" in msg:
            raise _ParseError(PARSE_ERROR_ENCRYPTED, str(exc))
        if "not a pdf" in msg or "invalid pdf" in msg or "eof" in msg:
            raise _ParseError(PARSE_ERROR_CORRUPT, str(exc))
        if "timeout" in msg or "timed out" in msg:
            raise _ParseError(PARSE_ERROR_TIMEOUT, str(exc))
        raise _ParseError(PARSE_ERROR_UNKNOWN, str(exc))

    doc = result.document
    total_chars, page_count = _extracted_text_stats(doc)
    logger.info(
        "parser: %s extracted chars=%d pages=%d avg=%d/page",
        pdf_path.name, total_chars, page_count, total_chars // page_count,
    )

    if total_chars // page_count < MIN_CHARS_PER_PAGE:
        logger.info(
            "parser: %s below text threshold — retrying with OCR fallback",
            pdf_path.name,
        )
        ocr_converter = _get_converter(do_ocr=True)
        try:
            result = ocr_converter.convert(str(pdf_path))
        except Exception as exc:
            raise _ParseError(PARSE_ERROR_TIMEOUT, "OCR fallback failed: {0}".format(exc))
        doc = result.document
        total_chars, page_count = _extracted_text_stats(doc)
        logger.info(
            "parser: %s OCR result chars=%d pages=%d avg=%d/page",
            pdf_path.name, total_chars, page_count, total_chars // page_count,
        )
        if total_chars // page_count < MIN_CHARS_PER_PAGE:
            raise _ParseError(
                PARSE_ERROR_NO_TEXT,
                "text density {0}/page below threshold {1} even after OCR".format(
                    total_chars // page_count, MIN_CHARS_PER_PAGE,
                ),
            )

    return doc


# --- Persistence helpers -----------------------------------------------------

def _atomic_write_json(payload, out_path):
    # type: (Any, Path) -> None
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    os.replace(str(tmp), str(out_path))


def serialize_parsed(docling_doc, out_path):
    # type: (Any, Path) -> None
    payload = docling_doc.export_to_dict()
    _atomic_write_json(payload, out_path)


def serialize_chunks(chunks, out_path):
    # type: (List[Dict[str, Any]], Path) -> None
    _atomic_write_json(chunks, out_path)


# --- Supabase helpers --------------------------------------------------------

def fetch_pending_parse(limit=None):
    # type: (Optional[int]) -> List[Dict[str, Any]]
    supabase = get_supabase_client()
    query = (
        supabase.table("corporate_actions")
        .select(
            "id, scrip_code, company, subject, category, "
            "attachment_url, local_pdf_path, trading_date, "
            "announcement_datetime, source"
        )
        .not_.is_("local_pdf_path", None)
        .is_("parsed_at", None)
        .lt("parse_attempts", 3)
    )
    for sub in SKIP_SUBJECT_SUBSTRINGS:
        query = query.not_.ilike("subject", "%{0}%".format(sub))
    response = query.limit(limit or PARSE_BATCH_SIZE).execute()
    return response.data or []


def mark_parsed(record_id, chunk_count):
    # type: (str, int) -> None
    supabase = get_supabase_client()
    supabase.table("corporate_actions").update(
        {
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "chunk_count": chunk_count,
            "parse_error": None,
        }
    ).eq("id", record_id).execute()


def mark_parse_error(record_id, error_kind, error_detail=None):
    # type: (str, str, Optional[str]) -> None
    supabase = get_supabase_client()
    row = supabase.table("corporate_actions").select("parse_attempts").eq("id", record_id).execute()
    current_attempts = 0
    if row.data:
        current_attempts = int(row.data[0].get("parse_attempts") or 0)
    payload = {
        "parse_error": error_kind,
        "parse_attempts": current_attempts + 1,
    }
    supabase.table("corporate_actions").update(payload).eq("id", record_id).execute()
    if error_detail:
        logger.debug("parser: %s error_detail=%s", record_id, error_detail)


# --- Driver ------------------------------------------------------------------

class _ParseError(Exception):
    def __init__(self, kind, detail=""):
        super(_ParseError, self).__init__(detail)
        self.kind = kind
        self.detail = detail


def _build_doc_metadata(record):
    # type: (Dict[str, Any]) -> Dict[str, Any]
    return {
        "doc_id": record["id"],
        "company": record.get("company"),
        "scrip_code": record.get("scrip_code"),
        "subject": record.get("subject"),
        "announcement_date": record.get("trading_date"),
        "source": record.get("source"),
    }


def parse_one(record):
    # type: (Dict[str, Any]) -> int
    """Parse + chunk a single row. Returns chunk_count on success.

    Raises _ParseError on classified failures so the caller can update the DB.
    """
    pdf_path = resolve_pdf_path(record.get("local_pdf_path"))
    if pdf_path is None:
        raise _ParseError(PARSE_ERROR_CORRUPT, "local_pdf_path does not resolve to an existing file")

    doc = parse_pdf(pdf_path)

    doc_metadata = _build_doc_metadata(record)
    chunks = chunk_document(doc, doc_metadata)

    if not chunks:
        raise _ParseError(PARSE_ERROR_EMPTY_CHUNKS, "chunker produced 0 chunks")

    chunks_path = parsed_chunks_path_for(pdf_path)
    serialize_chunks(chunks, chunks_path)
    logger.info(
        "parser: wrote %d chunks to %s (%d KB)",
        len(chunks), chunks_path,
        max(1, chunks_path.stat().st_size // 1024),
    )

    if PARSED_KEEP_FULL:
        try:
            docling_path = docling_json_path_for(pdf_path)
            serialize_parsed(doc, docling_path)
            logger.debug("parser: wrote raw DoclingDocument to %s", docling_path)
        except Exception as exc:
            logger.warning("parser: failed to serialise raw DoclingDocument: %s", exc)

    return len(chunks)


def run(limit=None):
    # type: (Optional[int]) -> int
    """Drain all pending parse rows, fetching in batches of ``limit`` at a time.

    ``seen_ids`` prevents an infinite loop on rows that keep failing with a
    retryable error — their ``parse_attempts`` bumps toward 3 across runs, but
    within a single run they'd otherwise be re-fetched forever.
    """
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    parsed_ok = 0
    seen_ids = set()  # type: set

    while True:
        records = fetch_pending_parse(limit=limit)
        fresh = [r for r in records if r["id"] not in seen_ids]
        logger.info(
            "parser: fetched %d rows (%d new to this run)",
            len(records), len(fresh),
        )
        if not fresh:
            break

        for record in fresh:
            row_id = record["id"]
            seen_ids.add(row_id)
            try:
                chunk_count = parse_one(record)
                mark_parsed(row_id, chunk_count)
                parsed_ok += 1
                logger.info(
                    "parser: OK %s (%s) chunks=%d",
                    row_id, record.get("company"), chunk_count,
                )
            except _ParseError as pe:
                logger.warning(
                    "parser: FAIL %s kind=%s detail=%s",
                    row_id, pe.kind, pe.detail,
                )
                mark_parse_error(row_id, pe.kind, error_detail=pe.detail)
            except Exception as exc:
                logger.exception("parser: unexpected error on %s", row_id)
                mark_parse_error(row_id, PARSE_ERROR_UNKNOWN, error_detail=str(exc))

    return parsed_ok
