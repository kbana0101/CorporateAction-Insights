import os
import logging
from pathlib import Path
from typing import List, Dict, Optional

import requests
from supabase import create_client
from dotenv import load_dotenv

# --------------------
# Setup
# --------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

PDF_DIR = Path("./pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CorporateActionsBot/1.0)"
}

# --------------------
# Helpers
# --------------------
def clean_filename(value: str, max_len: int = 40) -> str:
    return "".join(c if c.isalnum() else "_" for c in value)[:max_len]


def fetch_pending_actions(limit: int = 500) -> List[Dict]:
    """Fetch actions where PDF not yet downloaded"""
    response = (
        supabase
        .table("corporate_actions")
        .select("*")
        .is_("local_pdf_path", None)
        .not_.is_("attachment_url", None)
        .limit(limit)
        .execute()
    )

    return response.data or []


def download_pdf(url: str, target_path: Path) -> bool:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()

        target_path.write_bytes(resp.content)
        return True

    except Exception as e:
        logging.warning(f"⚠️ Download failed: {url} → {e}")
        return False


def update_pdf_path(record_id: str, path: str):
    supabase.table("corporate_actions") \
        .update({"local_pdf_path": path}) \
        .eq("id", record_id) \
        .execute()


# --------------------
# Main job
# --------------------
def run():
    actions = fetch_pending_actions()

    logging.info(f"Found {len(actions)} PDFs to download")

    for action in actions:
        url = action.get("attachment_url")
        if not url or not url.startswith("http"):
            continue

        company = clean_filename(action.get("company", "unknown"))
        scrip = action.get("scrip_code", "na")
        date = (action.get("trading_date") or "unknown")

        filename = f"{company}_{scrip}_{date}.pdf"
        pdf_path = PDF_DIR / filename

        if pdf_path.exists():
            logging.info(f"⏩ Already exists: {filename}")
            update_pdf_path(action["id"], str(pdf_path))
            continue

        success = download_pdf(url, pdf_path)

        if success:
            logging.info(f"✅ Downloaded {filename}")
            update_pdf_path(action["id"], str(pdf_path))


if __name__ == "__main__":
    run()
