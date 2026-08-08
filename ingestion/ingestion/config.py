"""Centralised configuration loaded from environment / .env."""
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _get_required(name):
    # type: (str) -> str
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            "Missing required environment variable: {0}. "
            "Copy .env.example to .env and fill it in.".format(name)
        )
    return value


def _get_int(name, default):
    # type: (str, int) -> int
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_bool(name, default):
    # type: (str, bool) -> bool
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


INGEST_API_URL = os.getenv("INGEST_API_URL", "")

XBRL_DIR = Path(os.getenv("XBRL_DIR", "./data/xbrl_files")).resolve()
PDF_DIR = Path(os.getenv("PDF_DIR", "./data/pdfs")).resolve()
PARSED_DIR = Path(os.getenv("PARSED_DIR", "./data/parsed")).resolve()

PDF_DOWNLOAD_LIMIT = _get_int("PDF_DOWNLOAD_LIMIT", 500)
PARSE_BATCH_SIZE = _get_int("PARSE_BATCH_SIZE", 10)
INGEST_BATCH_SIZE = _get_int("INGEST_BATCH_SIZE", 5)

# When true, keep the raw DoclingDocument JSON dump next to the chunks JSON.
# Handy for debugging chunking rules; disable in prod to save disk.
PARSED_KEEP_FULL = _get_bool("PARSED_KEEP_FULL", False)

# Subject substrings that mark a row as noise to skip across all pipeline
# stages (download, parse, ingest). Case-insensitive substring match.
SKIP_SUBJECT_SUBSTRINGS = ["Newspaper Publication"]


def ensure_dirs():
    # type: () -> None
    XBRL_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging(level=logging.INFO):
    # type: (int) -> None
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def get_supabase_client():
    """Lazy import so importing config doesn't trigger network init."""
    from supabase import create_client

    return create_client(
        _get_required("SUPABASE_URL"),
        _get_required("SUPABASE_SERVICE_ROLE_KEY"),
    )
