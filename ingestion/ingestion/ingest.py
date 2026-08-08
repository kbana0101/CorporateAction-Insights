"""Stage 4: POST parsed chunks to the chatbot ingest API and stamp ingested_at.

Reads rows where the parse stage has produced a ``<stem>.chunks.json`` on
disk (``parsed_at IS NOT NULL AND ingested_at IS NULL``) and forwards the
chunks as JSON. The old multipart PDF upload path has been removed — see
``parser.py`` for the new upstream stage.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .config import (
    INGEST_API_URL,
    INGEST_BATCH_SIZE,
    SKIP_SUBJECT_SUBSTRINGS,
    get_supabase_client,
)
from .paths import parsed_chunks_path_for, resolve_pdf_path

logger = logging.getLogger(__name__)


def fetch_pending_ingest(limit=None):
    # type: (Optional[int]) -> List[Dict[str, Any]]
    supabase = get_supabase_client()
    query = (
        supabase.table("corporate_actions")
        .select(
            "id, scrip_code, company, subject, "
            "attachment_url, local_pdf_path, trading_date, "
            "source, chunk_count"
        )
        .not_.is_("parsed_at", None)
        .is_("ingested_at", None)
    )
    for sub in SKIP_SUBJECT_SUBSTRINGS:
        query = query.not_.ilike("subject", "%{0}%".format(sub))
    response = query.limit(limit or INGEST_BATCH_SIZE).execute()
    return response.data or []


def _load_chunks(record):
    # type: (Dict[str, Any]) -> List[Dict[str, Any]]
    pdf_path = resolve_pdf_path(record.get("local_pdf_path"))
    if pdf_path is None:
        raise FileNotFoundError(
            "local_pdf_path does not resolve: {0}".format(record.get("local_pdf_path"))
        )
    chunks_path = parsed_chunks_path_for(pdf_path)
    if not chunks_path.exists():
        raise FileNotFoundError("chunks JSON missing: {0}".format(chunks_path))
    with chunks_path.open("r", encoding="utf-8") as fh:
        chunks = json.load(fh)
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("chunks JSON is empty or malformed: {0}".format(chunks_path))
    return chunks


def ingest_chunks(chunks, doc_id):
    # type: (List[Dict[str, Any]], str) -> None
    if not INGEST_API_URL:
        raise RuntimeError("INGEST_API_URL is not configured in .env")

    payload = {"doc_id": doc_id, "chunks": chunks}
    resp = requests.post(
        INGEST_API_URL,
        json=payload,
        timeout=300,
        headers={"Content-Type": "application/json"},
    )
    if not resp.ok:
        logger.error(
            "Ingest API returned %s for doc_id=%s: %s",
            resp.status_code, doc_id, resp.text[:2000],
        )
        resp.raise_for_status()


def mark_ingested(record_id):
    # type: (str) -> None
    supabase = get_supabase_client()
    supabase.table("corporate_actions").update(
        {"ingested_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", record_id).execute()


def run(batch_size=None):
    # type: (Optional[int]) -> int
    """Drain all pending ingest rows, fetching in batches of ``batch_size``.

    ``seen_ids`` prevents an infinite loop on rows that keep failing — a row
    that raises never gets ``ingested_at`` stamped, so it would otherwise be
    re-fetched forever within a single run.
    """
    ingested = 0
    seen_ids = set()  # type: set

    while True:
        records = fetch_pending_ingest(limit=batch_size)
        fresh = [r for r in records if r["id"] not in seen_ids]
        logger.info(
            "ingest: fetched %d rows (%d new to this run)",
            len(records), len(fresh),
        )
        if not fresh:
            break

        for record in fresh:
            row_id = record["id"]
            seen_ids.add(row_id)
            try:
                chunks = _load_chunks(record)
                logger.info(
                    "ingest: %s (%s) chunks=%d",
                    row_id, record.get("company"), len(chunks),
                )
                ingest_chunks(chunks, doc_id=row_id)
                mark_ingested(row_id)
                ingested += 1
                logger.info("ingest: OK %s", row_id)
            except FileNotFoundError as fnf:
                logger.warning(
                    "ingest: skipping %s — %s (will be re-picked once parse re-runs)",
                    row_id, fnf,
                )
            except Exception:
                logger.exception("ingest: failed on %s", row_id)

    return ingested
