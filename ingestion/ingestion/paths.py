"""Shared path helpers used by the parse and ingest stages."""
from pathlib import Path
from typing import Optional

from .config import PARSED_DIR, PDF_DIR


def normalise_path_text(path):
    # type: (str) -> str
    return path.replace("\\", "/")


def resolve_pdf_path(pdf_path):
    # type: (str) -> Optional[Path]
    """Best-effort lookup of a PDF referenced by ``local_pdf_path`` in the DB.

    The value may have been written on a different host or with backslashes;
    we try a handful of candidates before giving up.
    """
    if not pdf_path:
        return None

    cleaned = normalise_path_text(pdf_path)
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


def parsed_chunks_path_for(pdf_path):
    # type: (Path) -> Path
    """Where the chunker writes the per-doc chunks JSON."""
    return PARSED_DIR / (pdf_path.stem + ".chunks.json")


def docling_json_path_for(pdf_path):
    # type: (Path) -> Path
    """Where the parser optionally dumps the raw DoclingDocument."""
    return PARSED_DIR / (pdf_path.stem + ".docling.json")
