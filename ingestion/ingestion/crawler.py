"""Stage 1: Fetch BSE corporate-action announcements and save XBRL XML files."""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests

from .config import XBRL_DIR

logger = logging.getLogger(__name__)

BSE_API_BASE = "https://api.bseindia.com/BseIndiaAPI/api"
BSE_WEB_BASE = "https://www.bseindia.com"
ANNOUNCEMENTS_API_URL = BSE_API_BASE + "/AnnSubCategoryGetData/w"
XBRL_URL = BSE_WEB_BASE + "/Msource/90D/CorpXbrlGen.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": BSE_WEB_BASE + "/corporates/ann.html",
    "Origin": BSE_WEB_BASE,
}


def _normalise_api_date(target_date):
    # type: (str) -> str
    """Convert DD/MM/YYYY or YYYY-MM-DD to BSE API's YYYYMMDD format."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(target_date, fmt).strftime("%Y%m%d")
        except ValueError:
            pass
    raise ValueError("Date must be DD/MM/YYYY or YYYY-MM-DD")


def _safe_filename(value):
    # type: (str) -> str
    cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)
    return cleaned[:120] or "xbrl"


def _save_xml(content, output_dir, filename):
    # type: (str, Path, str) -> Path
    target = output_dir / filename
    target.write_text(content, encoding="utf-8")
    return target


def _fetch_announcements_page(page_no, api_date):
    # type: (int, str) -> dict
    params = {
        "pageno": page_no,
        "strCat": "-1",
        "strPrevDate": api_date,
        "strScrip": "",
        "strSearch": "P",
        "strToDate": api_date,
        "strType": "C",
        "subcategory": "-1",
    }
    response = requests.get(
        ANNOUNCEMENTS_API_URL,
        params=params,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _download_xbrl(news_id, scrip_code):
    # type: (str, str) -> str
    response = requests.get(
        XBRL_URL,
        params={"Bsenewid": news_id, "Scripcode": scrip_code},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def crawl_bse_corporate_actions(target_date=None, output_dir=None, headless=True):
    # type: (Optional[str], Optional[Path], bool) -> List[str]
    """
    Fetch BSE corporate actions for a given date (DD/MM/YYYY or YYYY-MM-DD).

    Defaults to today. Returns list of XML files saved.
    """
    output_dir = Path(output_dir) if output_dir else XBRL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_file in output_dir.glob("*.xml"):
        old_file.unlink()

    if target_date is None:
        target_date = datetime.today().strftime("%d/%m/%Y")

    api_date = _normalise_api_date(target_date)
    logger.info("Fetching BSE announcements for %s", target_date)
    saved = []  # type: List[str]

    page_no = 1
    total_rows = None  # type: Optional[int]

    while True:
        payload = _fetch_announcements_page(page_no, api_date)
        rows = payload.get("Table") or []
        count_rows = payload.get("Table1") or []

        if total_rows is None and count_rows:
            total_rows = int(count_rows[0].get("ROWCNT") or 0)
            logger.info("BSE reports %d announcements", total_rows)

        if not rows:
            logger.info("No rows returned for page %d, finishing.", page_no)
            break

        logger.info("Processing page %d with %d rows", page_no, len(rows))

        for idx, row in enumerate(rows, start=1):
            news_id = row.get("NEWSID")
            scrip_code = row.get("SCRIP_CD")
            xml_name = row.get("XML_NAME") or "xbrl_p{0}_{1}".format(page_no, idx)

            if not news_id or not scrip_code:
                logger.warning("Skipping row without NEWSID/SCRIP_CD: %s", row)
                continue

            try:
                xml_content = _download_xbrl(str(news_id), str(scrip_code))
                filename = _safe_filename(str(xml_name)) + ".xml"
                saved_path = _save_xml(xml_content, output_dir, filename)
                saved.append(str(saved_path))
                logger.info("Saved %s", saved_path.name)
            except Exception as exc:
                logger.warning(
                    "Failed XBRL download for NEWSID=%s SCRIP_CD=%s: %s",
                    news_id,
                    scrip_code,
                    exc,
                )

        if total_rows is not None and page_no * 50 >= total_rows:
            break

        page_no += 1

    logger.info("Crawl complete, saved %d XML files", len(saved))
    return saved
