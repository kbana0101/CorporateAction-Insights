"""End-to-end runner for the BSE corporate-actions ingestion pipeline.

Pipeline stages:
    1. Fetch BSE corporate-action announcements -> XBRL XML files.
    2. Parse XBRL -> insert metadata rows into Supabase.
    3. Download PDFs for rows missing local_pdf_path.
    4. For rows with local PDFs but not yet ingested, POST them to the chatbot
       ingestion API and mark ingested_at.

Run the whole pipeline with:
    python main.py

Or skip stages with flags, e.g. only re-ingest pending PDFs:
    python main.py --skip-crawl --skip-metadata --skip-download
"""
import argparse
import logging
import sys

from ingestion.config import ensure_dirs, setup_logging
from ingestion.crawler import crawl_bse_corporate_actions
from ingestion.ingest import run as run_ingest
from ingestion.metadata import run as run_metadata
from ingestion.pdfs import run as run_pdfs

logger = logging.getLogger("ingestion.main")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="BSE corporate-actions ingestion pipeline"
    )
    parser.add_argument(
        "--date",
        help="Target date in DD/MM/YYYY format (default: today)",
        default=None,
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Deprecated no-op kept for compatibility; crawler no longer uses Chrome",
    )
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="Skip stage 1 (Selenium crawl)",
    )
    parser.add_argument(
        "--skip-metadata",
        action="store_true",
        help="Skip stage 2 (parse XBRL + insert metadata)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip stage 3 (download PDFs)",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip stage 4 (POST PDFs to ingest API)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)
    ensure_dirs()

    if not args.skip_crawl:
        logger.info("=== Stage 1: Fetch BSE announcements ===")
        crawl_bse_corporate_actions(
            target_date=args.date,
            headless=not args.no_headless,
        )
    else:
        logger.info("Skipping stage 1 (crawl)")

    if not args.skip_metadata:
        logger.info("=== Stage 2: Parse XBRL & insert metadata ===")
        run_metadata()
    else:
        logger.info("Skipping stage 2 (metadata)")

    if not args.skip_download:
        logger.info("=== Stage 3: Download PDFs ===")
        run_pdfs()
    else:
        logger.info("Skipping stage 3 (PDF download)")

    if not args.skip_ingest:
        logger.info("=== Stage 4: Ingest PDFs into chatbot ===")
        run_ingest()
    else:
        logger.info("Skipping stage 4 (ingest)")

    logger.info("Pipeline finished.")


if __name__ == "__main__":
    sys.exit(main())
