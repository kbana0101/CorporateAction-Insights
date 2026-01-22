from typing import List, Dict
import logging
import os
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

def fetch_pending_corporate_action_pdfs(limit: int = 20) -> List[Dict]:
    """
    Fetch corporate actions whose PDFs exist locally
    but are not yet ingested.
    """
    response = (
        supabase
        .table("corporate_actions")
        .select(
            "id, scrip_code, company, subject, local_pdf_path, trading_date, source"
        )
        .is_("ingested_at", None)
        .not_.is_("local_pdf_path", None)
        .limit(limit)
        .execute()
    )

    return response.data or []
