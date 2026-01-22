import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import logging

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

XML_DIR = Path("./xbrl_files")  # make this configurable later

# Namespace dictionary
ns = {
    "bse": "http://www.bseindia.com/xbrl/co/2017-06-21/in-bse-co"
}

# --------------------
# XML Parsing
# --------------------
def parse_xbrl(file_path: Path) -> Optional[Dict]:
    """Parse one XBRL XML file and return DB-ready metadata"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        announcement_dt = root.findtext(
            ".//bse:DateAndTimeOfSubmission", namespaces=ns
        )

        return {
            "scrip_code": root.findtext(".//bse:ScripCode", namespaces=ns),
            "company": root.findtext(".//bse:NameOfTheCompany", namespaces=ns),
            "subject": root.findtext(".//bse:SubjectOfAnnouncement", namespaces=ns),
            "description": root.findtext(".//bse:DescriptionOfAnnouncement", namespaces=ns),

            "category": root.findtext(".//bse:CategoryOfAnnouncement", namespaces=ns),
            "announcement_type": root.findtext(".//bse:TypeOfAnnouncement", namespaces=ns),

            "attachment_url": root.findtext(".//bse:AttachmentURL", namespaces=ns),
            "local_pdf_path": None,

            "announcement_datetime": parse_datetime(announcement_dt),
            "trading_date": parse_trading_date(announcement_dt),

            "source": "BSE"
        }

    except Exception as e:
        logging.warning(f"⚠️ Error parsing {file_path.name}: {e}")
        return None


def parse_datetime(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def parse_trading_date(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        return None
    
def serialize_record(record: Dict) -> Dict:
    """Convert datetime/date fields to JSON-safe strings"""
    serialized = {}

    for k, v in record.items():
        if isinstance(v, datetime):
            serialized[k] = v.isoformat()
        elif hasattr(v, "isoformat"):  # date
            serialized[k] = v.isoformat()
        else:
            serialized[k] = v

    return serialized



# --------------------
# Bulk Processing
# --------------------
def parse_all_xbrl(directory: Path) -> List[Dict]:
    results = []

    for file_path in directory.glob("*.xml"):
        data = parse_xbrl(file_path)
        if data:
            results.append(data)

    logging.info(f"Parsed {len(results)} XBRL files")
    return results


def insert_metadata(records: List[Dict]):
    if not records:
        logging.info("No records to insert")
        return

    logging.info(f"Inserting {len(records)} records into Supabase")

    safe_records = [serialize_record(r) for r in records]

    response = (
        supabase
        .table("corporate_actions")
        .insert(safe_records)
        .execute()
    )

    logging.info(f"Inserted {len(response.data)} records")


# --------------------
# Entrypoint
# --------------------
if __name__ == "__main__":
    records = parse_all_xbrl(XML_DIR)
    insert_metadata(records)
