"""Stage 3: Download PDFs for corporate actions that don't have a local copy yet."""
import logging
from pathlib import Path
from typing import Dict, List, Optional

import requests

from .config import (
    PDF_DIR,
    PDF_DOWNLOAD_LIMIT,
    SKIP_SUBJECT_SUBSTRINGS,
    get_supabase_client,
)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/pdf,application/octet-stream,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bseindia.com/corporates/ann.html",
}


def _clean(value, max_len=40):
    # type: (str, int) -> str
    if not value:
        return "unknown"
    return "".join(c if c.isalnum() else "_" for c in value)[:max_len]


def fetch_pending_actions(limit=None):
    # type: (Optional[int]) -> List[Dict]
    supabase = get_supabase_client()
    query = (
        supabase.table("corporate_actions")
        .select("*")
        .is_("local_pdf_path", None)
        .not_.is_("attachment_url", None)
    )
    for sub in SKIP_SUBJECT_SUBSTRINGS:
        query = query.not_.ilike("subject", "%{0}%".format(sub))
    response = query.limit(limit or PDF_DOWNLOAD_LIMIT).execute()
    return response.data or []


def download_pdf(url, target_path):
    # type: (str, Path) -> bool
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        content_type = (resp.headers.get("content-type") or "").lower()
        if not resp.content.startswith(b"%PDF"):
            logger.warning(
                "Download did not return a PDF: %s (%s)", url, content_type
            )
            return False
        target_path.write_bytes(resp.content)
        return True
    except Exception as exc:
        logger.warning("Download failed: %s -> %s", url, exc)
        return False


def update_pdf_path(record_id, path):
    # type: (str, str) -> None
    supabase = get_supabase_client()
    supabase.table("corporate_actions").update(
        {"local_pdf_path": path}
    ).eq("id", record_id).execute()


def run(limit=None):
    # type: (Optional[int]) -> int
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    actions = fetch_pending_actions(limit=limit)
    logger.info("Found %d PDFs to download", len(actions))

    downloaded = 0
    for action in actions:
        url = action.get("attachment_url")
        if not url or not url.startswith("http"):
            continue

        company = _clean(action.get("company") or "unknown")
        scrip = action.get("scrip_code") or "na"
        trading_date = action.get("trading_date") or "unknown"

        filename = "{0}_{1}_{2}.pdf".format(company, scrip, trading_date)
        pdf_path = PDF_DIR / filename

        if pdf_path.exists():
            logger.info("Already exists: %s", filename)
            update_pdf_path(action["id"], str(pdf_path))
            continue

        if download_pdf(url, pdf_path):
            logger.info("Downloaded %s", filename)
            update_pdf_path(action["id"], str(pdf_path))
            downloaded += 1

    return downloaded
