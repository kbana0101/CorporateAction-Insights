import os
import requests
import json
import logging
from datetime import datetime, timezone
from supabase import create_client
from dotenv import load_dotenv

#from .fetch_pending_pdfs import fetch_pending_corporate_action_pdfs
from fetch_pending_pdfs import (
    fetch_pending_corporate_action_pdfs
)


# --------------------
# Setup
# --------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
INGEST_API_URL = os.getenv("INGEST_API_URL")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def ingest_pdf(pdf_path: str, metadata: dict) -> None:
    """
    Calls existing /api/ingest endpoint.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)

    with open(pdf_path, "rb") as f:
        files = {
            "files": (os.path.basename(pdf_path), f, "application/pdf")
        }

        # Optional: pass metadata if your API supports it later
        data = {
            "metadata": json.dumps(metadata)
        }

        resp = requests.post(
            INGEST_API_URL,
            files=files,
            data=data,
            timeout=300
        )

    resp.raise_for_status()


def mark_ingested(corp_action_id: str):
    supabase.table("corporate_actions").update(
        {
            "ingested_at": datetime.now(timezone.utc).isoformat()
        }
    ).eq("id", corp_action_id).execute()


def run_ingestion_batch(batch_size: int = 5):
    records = fetch_pending_corporate_action_pdfs(batch_size)

    logging.info(f"Found {len(records)} pending PDFs")

    for record in records:
        try:
            logging.info(
                f"Ingesting: {record['company']} | {record['local_pdf_path']}"
            )

            metadata = {
                "doc_id": record["id"],  # Ensure doc_id is included
                "company": record["company"],
                "scrip_code": record["scrip_code"],
                "announcement_date": record["trading_date"],
                "subject": record["subject"],
                "source": record["source"],
            }

            logging.info(f"Metadata being sent: {metadata}")

            ingest_pdf(
                pdf_path=record["local_pdf_path"],
                metadata=metadata,
            )

            mark_ingested(record["id"])
            logging.info("✅ Ingested successfully")

        except Exception as e:
            logging.exception(
                f"❌ Failed ingestion for {record['local_pdf_path']}"
            )


if __name__ == "__main__":
    run_ingestion_batch()