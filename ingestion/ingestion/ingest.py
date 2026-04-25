"""Stages 4 & 5: Find pending PDFs in DB and ingest them via the chatbot API."""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from .config import INGEST_API_URL, INGEST_BATCH_SIZE, PDF_DIR, get_supabase_client
from .pdfs import download_pdf

logger = logging.getLogger(__name__)
BSE_WEB_BASE = "https://www.bseindia.com"


def fetch_pending_corporate_action_pdfs(limit=None):
    # type: (Optional[int]) -> List[Dict]
    supabase = get_supabase_client()
    response = (
        supabase.table("corporate_actions")
        .select(
            "id, scrip_code, company, subject, attachment_url, "
            "local_pdf_path, trading_date, source"
        )
        .is_("ingested_at", None)
        .not_.is_("local_pdf_path", None)
        .limit(limit or INGEST_BATCH_SIZE)
        .execute()
    )
    return response.data or []


def _normalise_path_text(path):
    # type: (str) -> str
    return path.replace("\\", "/")


def _resolve_pdf_path(pdf_path):
    # type: (str) -> Optional[Path]
    if not pdf_path:
        return None

    cleaned = _normalise_path_text(pdf_path)
    raw_path = Path(cleaned)
    candidates = []

    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append(Path.cwd() / raw_path)
        candidates.append(PDF_DIR / raw_path.name)
        candidates.append(PDF_DIR.parent / raw_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def _repair_missing_pdf(record):
    # type: (Dict) -> Optional[Path]
    attachment_url = record.get("attachment_url")
    if not attachment_url or not attachment_url.startswith("http"):
        return None

    stored_path = record.get("local_pdf_path") or ""
    filename = Path(_normalise_path_text(stored_path)).name
    if not filename:
        filename = "{0}_{1}_{2}.pdf".format(
            record.get("company") or "unknown",
            record.get("scrip_code") or "na",
            record.get("trading_date") or "unknown",
        )

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    target = PDF_DIR / filename

    logger.info("Local PDF missing; re-downloading %s", filename)
    for url in _candidate_pdf_urls(attachment_url):
        if download_pdf(url, target):
            break
    else:
        _clear_pdf_path(record["id"])
        logger.warning(
            "Could not repair missing PDF for %s; cleared local_pdf_path",
            record["id"],
        )
        return None

    supabase = get_supabase_client()
    supabase.table("corporate_actions").update(
        {"local_pdf_path": str(target)}
    ).eq("id", record["id"]).execute()

    return target


def _candidate_pdf_urls(attachment_url):
    # type: (str) -> List[str]
    """Try old and current BSE PDF URL shapes for a stored attachment URL."""
    candidates = [attachment_url]
    filename = attachment_url.rsplit("Pname=", 1)[-1].rsplit("/", 1)[-1]

    if filename and filename.lower().endswith(".pdf"):
        candidates.extend(
            [
                BSE_WEB_BASE + "/xml-data/corpfiling/AttachLive/" + filename,
                BSE_WEB_BASE + "/xml-data/corpfiling/AttachHis/" + filename,
            ]
        )

    seen = set()
    unique = []
    for url in candidates:
        if url not in seen:
            unique.append(url)
            seen.add(url)
    return unique


def _clear_pdf_path(corp_action_id):
    # type: (str) -> None
    supabase = get_supabase_client()
    supabase.table("corporate_actions").update(
        {"local_pdf_path": None}
    ).eq("id", corp_action_id).execute()


def ingest_pdf(pdf_path, metadata):
    # type: (Path, Dict) -> None
    if not INGEST_API_URL:
        raise RuntimeError("INGEST_API_URL is not configured in .env")
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    with pdf_path.open("rb") as fh:
        files = {
            "files": (pdf_path.name, fh, "application/pdf"),
        }
        data = {"metadata": json.dumps(metadata)}

        resp = requests.post(
            INGEST_API_URL,
            files=files,
            data=data,
            timeout=300,
        )

    if not resp.ok:
        logger.error(
            "Ingest API returned %s for %s: %s",
            resp.status_code,
            pdf_path.name,
            resp.text[:2000],
        )
        resp.raise_for_status()


def mark_ingested(corp_action_id):
    # type: (str) -> None
    supabase = get_supabase_client()
    supabase.table("corporate_actions").update(
        {"ingested_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", corp_action_id).execute()


def run(batch_size=None):
    # type: (Optional[int]) -> int
    records = fetch_pending_corporate_action_pdfs(limit=batch_size)
    logger.info("Found %d pending PDFs", len(records))

    ingested = 0
    for record in records:
        try:
            logger.info(
                "Ingesting %s (%s)",
                record.get("company"),
                record.get("local_pdf_path"),
            )
            metadata = {
                "doc_id": record["id"],
                "company": record.get("company"),
                "scrip_code": record.get("scrip_code"),
                "announcement_date": record.get("trading_date"),
                "subject": record.get("subject"),
                "source": record.get("source"),
            }

            pdf_path = _resolve_pdf_path(record["local_pdf_path"])
            if pdf_path is None:
                pdf_path = _repair_missing_pdf(record)
            if pdf_path is None:
                logger.warning(
                    "Skipping %s because its PDF is unavailable locally and "
                    "could not be re-downloaded",
                    record.get("id"),
                )
                continue

            ingest_pdf(pdf_path=pdf_path, metadata=metadata)
            mark_ingested(record["id"])
            ingested += 1
            logger.info("Ingested %s", record["id"])

        except Exception:
            logger.exception(
                "Failed ingestion for %s", record.get("local_pdf_path")
            )

    return ingested
