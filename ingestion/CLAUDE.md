# ingestion/

Python pipeline that populates Supabase `corporate_actions` and pushes PDFs
into the chatbot's vector index.

Entry point: `main.py` (run via `./run_ingest.sh` or manually).
Detailed usage is in `ingestion/README.md` — this file focuses on
non-obvious internals and what to touch for common changes.

## Four-stage pipeline

Stages run sequentially from `main.py`. Each has a `--skip-*` flag.

| Stage | Module | Reads | Writes |
|---|---|---|---|
| 1 crawl | `ingestion/crawler.py` | BSE public announcements API | `data/xbrl_files/*.xml` |
| 2 metadata | `ingestion/metadata.py` | `data/xbrl_files/*.xml` | Supabase `corporate_actions` rows |
| 3 pdfs | `ingestion/pdfs.py` | Rows with `attachment_url IS NOT NULL AND local_pdf_path IS NULL` | `data/pdfs/*.pdf` + updates `local_pdf_path` |
| 4 ingest | `ingestion/ingest.py` | Rows with `local_pdf_path IS NOT NULL AND ingested_at IS NULL` | POSTs to `INGEST_API_URL`, stamps `ingested_at` |

Stage 4 uses `INGEST_BATCH_SIZE` (default 5) as the row limit per run — it's
designed to be called repeatedly (e.g. from cron), not to drain the queue in
one shot.

## Config surface

All config comes from env vars via `ingestion/config.py`:

- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — required (bypasses RLS)
- `INGEST_API_URL` — required for stage 4; usually
  `http://localhost:3000/api/ingest` locally
- `XBRL_DIR` — default `./data/xbrl_files`
- `PDF_DIR` — default `./data/pdfs`
- `PDF_DOWNLOAD_LIMIT` — cap on stage 3 downloads per run (default 500)
- `INGEST_BATCH_SIZE` — cap on stage 4 ingests per run (default 5)

`.ingest.lock` (gitignored) is a mutex file created by `run_ingest.sh` to
prevent overlapping runs.

## Common commands

```bash
./run_ingest.sh                        # one-command venv setup + run
python main.py                         # once venv is active
python main.py --date 24/04/2026       # historical backfill
python main.py --skip-crawl --skip-metadata --skip-download  # ingest-only
python main.py -v                      # DEBUG logging
```

## Non-obvious things

- Python target is 3.9+ but the codebase uses PEP 484 comment-style type hints
  (`# type: (...) -> ...`) instead of inline annotations — keep that style
  when adding functions.
- `urllib3<2` is pinned in `requirements.txt` so macOS system Python's
  LibreSSL keeps working. Don't upgrade unless you also switch off LibreSSL.
- Stage 2 (`metadata.py`) is **insert-only** — no upsert. Rerunning against
  the same XBRL will insert duplicates unless the Supabase table has a
  uniqueness constraint on `(scrip_code, announcement_datetime, subject)` or
  similar. Check the table before backfilling.
- Stage 3 was rewritten to skip Selenium — `--no-headless` is a deprecated
  no-op kept for CLI compatibility. The BSE JSON endpoint is called directly
  and XBRL/PDF files are fetched via `requests`.
- Stage 4's `_repair_missing_pdf()` re-downloads a PDF if `local_pdf_path`
  points at a missing file. It tries both `AttachLive` and `AttachHis` URL
  shapes because BSE moves files after some time window. If both fail,
  `local_pdf_path` is cleared so the row falls back to stage 3 on the next
  run.
- The whole pipeline talks to Supabase using the service-role key. Never
  commit `.env` — it's in `.gitignore` already.
- `data/` is gitignored and will be recreated on first run by `ensure_dirs()`.
