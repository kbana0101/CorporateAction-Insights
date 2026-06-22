"""Stage 2: Parse XBRL XML files and upsert metadata into Supabase."""
import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from .config import XBRL_DIR, get_supabase_client

logger = logging.getLogger(__name__)

NS = {"bse": "http://www.bseindia.com/xbrl/co/2017-06-21/in-bse-co"}


def _parse_dt(value):
    # type: (Optional[str]) -> Optional[datetime]
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _parse_trading_date(value):
    # type: (Optional[str]) -> Optional[date]
    parsed = _parse_dt(value)
    return parsed.date() if parsed else None


def parse_xbrl_file(file_path):
    # type: (Path) -> Optional[Dict]
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as exc:
        logger.warning("Could not parse %s: %s", file_path.name, exc)
        return None

    announcement_dt = root.findtext(".//bse:DateAndTimeOfSubmission", namespaces=NS)

    return {
        "scrip_code": root.findtext(".//bse:ScripCode", namespaces=NS),
        "company": root.findtext(".//bse:NameOfTheCompany", namespaces=NS),
        "subject": root.findtext(".//bse:SubjectOfAnnouncement", namespaces=NS),
        "description": root.findtext(
            ".//bse:DescriptionOfAnnouncement", namespaces=NS
        ),
        "category": root.findtext(".//bse:CategoryOfAnnouncement", namespaces=NS),
        "announcement_type": root.findtext(
            ".//bse:TypeOfAnnouncement", namespaces=NS
        ),
        "attachment_url": root.findtext(".//bse:AttachmentURL", namespaces=NS),
        "local_pdf_path": None,
        "announcement_datetime": _parse_dt(announcement_dt),
        "trading_date": _parse_trading_date(announcement_dt),
        "source": "BSE",
    }


def _serialize(record):
    # type: (Dict) -> Dict
    out = {}
    for key, value in record.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
        elif hasattr(value, "isoformat"):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def parse_all(directory=None):
    # type: (Optional[Path]) -> List[Dict]
    directory = Path(directory) if directory else XBRL_DIR
    records = []  # type: List[Dict]

    for file_path in directory.glob("*.xml"):
        parsed = parse_xbrl_file(file_path)
        if parsed:
            records.append(parsed)

    logger.info("Parsed %d XBRL files from %s", len(records), directory)
    return records


def insert_metadata(records):
    # type: (List[Dict]) -> int
    if not records:
        logger.info("No records to insert")
        return 0

    supabase = get_supabase_client()
    safe_records = [_serialize(r) for r in records]

    # Insert corporate actions
    response = (
        supabase.table("corporate_actions").insert(safe_records).execute()
    )
    inserted = len(response.data or [])
    logger.info("Inserted %d records into corporate_actions", inserted)

    # Build deduplicated companies records (one per scrip_code)
    company_map = {}
    for r in safe_records:
        sc = r.get("scrip_code")
        if not sc:
            continue
        if sc not in company_map:
            company_map[sc] = {
                "scrip_code": sc,
                "company": r.get("company"),
                "source": r.get("source"),
            }

    company_records = list(company_map.values())

    if company_records:
        try:
            # Use the unique key `scrip_code` as the conflict target so Postgres
            # performs an upsert rather than raising a duplicate-key error.
            supabase.table("companies").upsert(
                company_records, on_conflict="scrip_code"
            ).execute()
            logger.info("Upserted %d records into companies", len(company_records))
        except Exception:
            logger.exception("Failed to upsert companies records")

    return inserted


def run():
    # type: () -> int
    return insert_metadata(parse_all())
