# Corporate Actions Ingestion Pipeline

End-to-end pipeline that fetches BSE corporate-action announcements, persists
metadata in Supabase, downloads attached PDFs, and feeds them into the chatbot
ingestion API.

The whole pipeline is invoked from a **single entry point**: `main.py`.

## Pipeline stages

| # | Module | What it does |
|---|---|---|
| 1 | `ingestion/crawler.py` | Calls BSE's public announcement API for a target date and downloads each row's XBRL XML into `data/xbrl_files/`. |
| 2 | `ingestion/metadata.py` | Parses the XBRL files and bulk-inserts rows into the Supabase `corporate_actions` table. |
| 3 | `ingestion/pdfs.py` | For rows with `attachment_url IS NOT NULL` and `local_pdf_path IS NULL`, downloads the PDF into `data/pdfs/` and updates `local_pdf_path`. |
| 4 | `ingestion/ingest.py` | For rows with a local PDF but `ingested_at IS NULL`, POSTs the PDF + metadata to `INGEST_API_URL` and stamps `ingested_at`. |

## Requirements

- Python 3.9+ (works with macOS system Python; `urllib3<2` is pinned so
  LibreSSL builds keep working)
- Supabase project with a `corporate_actions` table
- The frontend's `/api/ingest` endpoint reachable at `INGEST_API_URL`

## Setup

```bash
cd ingestion
cp .env.example .env
# edit .env with your Supabase credentials and INGEST_API_URL

./runner.sh
```

`runner.sh` creates `.venv`, installs `requirements.txt`, and runs `main.py`.

## Manual usage

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### CLI flags

```text
--date DD/MM/YYYY     target date (default: today)
--no-headless         deprecated no-op; kept for compatibility
--skip-crawl          skip stage 1
--skip-metadata       skip stage 2
--skip-download       skip stage 3
--skip-ingest         skip stage 4
-v, --verbose         debug logging
```

Examples:

```bash
# Re-run only the ingest step against pending rows
python main.py --skip-crawl --skip-metadata --skip-download

# Fetch yesterday and stop after parsing metadata
python main.py --date 24/04/2026 --skip-download --skip-ingest
```

## Folder layout

```
ingestion/
├── main.py              # single entry point
├── runner.sh            # one-command setup + run
├── requirements.txt
├── .env.example
├── ingestion/
│   ├── config.py        # env loading + supabase client + paths
│   ├── crawler.py       # stage 1
│   ├── metadata.py      # stage 2
│   ├── pdfs.py          # stage 3
│   └── ingest.py        # stage 4
└── data/
    ├── xbrl_files/      # downloaded XBRL XML
    └── pdfs/            # downloaded PDFs
```

## Notes

- The crawler no longer uses Selenium. It calls BSE's JSON endpoint and then
  downloads each XBRL XML document directly from BSE.
- The Supabase service-role key bypasses RLS — keep `.env` out of source
  control (already covered by `.gitignore`).
- For the same source URL/date the crawler will overwrite XML files in
  `data/xbrl_files/`, but metadata insertion is currently **insert-only**;
  rerunning stage 2 against the same data may insert duplicates unless your
  table has a uniqueness constraint.
