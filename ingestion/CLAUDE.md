# ingestion/

Python pipeline that populates Supabase `corporate_actions` and pushes PDFs
into the chatbot's vector index.

Entry point: `main.py` (run via `./run_ingest.sh` or manually).
Detailed usage is in `ingestion/README.md` — this file focuses on
non-obvious internals and what to touch for common changes.

## Five-stage pipeline

Stages run sequentially from `main.py`. Each has a `--skip-*` flag.

| Stage | Module | Reads | Writes |
|---|---|---|---|
| 1 crawl | `ingestion/crawler.py` | BSE public announcements API | `data/xbrl_files/*.xml` |
| 2 metadata | `ingestion/metadata.py` | `data/xbrl_files/*.xml` | Supabase `corporate_actions` rows |
| 3 pdfs | `ingestion/pdfs.py` | Rows with `attachment_url IS NOT NULL AND local_pdf_path IS NULL` | `data/pdfs/*.pdf` + updates `local_pdf_path` |
| 3.5 parse | `ingestion/parser.py` | Rows with `local_pdf_path IS NOT NULL AND parsed_at IS NULL AND parse_attempts < 3` | `data/parsed/<stem>.chunks.json` + stamps `parsed_at`, `chunk_count` (or `parse_error`) |
| 4 ingest | `ingestion/ingest.py` | Rows with `parsed_at IS NOT NULL AND ingested_at IS NULL` | POSTs chunks JSON to `INGEST_API_URL`, stamps `ingested_at` |

Stage 4 uses `INGEST_BATCH_SIZE` (default 5) as the row limit per run — it's
designed to be called repeatedly (e.g. from cron), not to drain the queue in
one shot. Stage 3.5 uses `PARSE_BATCH_SIZE` (default 10) because parsing is
CPU-heavy and worth capping separately.

### Stage 3.5 parsing — Docling + OCR fallback

The parser is `docling` running fully offline (models baked into the Docker
image). Behavior:

1. Convert the PDF with OCR **off**.
2. Measure average characters per page. If below `MIN_CHARS_PER_PAGE = 50`,
   re-convert the same PDF with OCR **on** (EasyOCR). This fallback catches
   scanned-image PDFs without paying the OCR cost on every doc.
3. If OCR-on still falls below the threshold, mark the row with
   `parse_error = "no_text_layer"` and stop retrying.

Other classified failures written to `parse_error`: `encrypted`,
`corrupt_pdf`, `empty_chunks`, `docling_timeout`. Only `docling_timeout` is
retryable (via the `parse_attempts < 3` gate).

### Chunking rules

`ingestion/chunker.py` walks the DoclingDocument tree and emits chunks
whose boundaries follow structure, not fixed sizes:

- New chunk at every section heading.
- Tables are atomic (one chunk each, regardless of size).
- Paragraphs accumulate to a ~600-token soft budget; overflow emits with a
  60-token tail overlap on the next chunk.
- Chunks under 40 tokens merge forward.
- Every chunk carries denormalized corp-action metadata (company,
  scrip_code, subject, announcement_date, source) so retrieval-time
  citations render fully from the vector row alone.

Enable `--verbose` to see per-item chunker debug logs (every boundary
decision, budget check, and emit).

## Config surface

All config comes from env vars via `ingestion/config.py`:

- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — required (bypasses RLS)
- `INGEST_API_URL` — required for stage 4; usually
  `http://localhost:3000/api/ingest` locally
- `XBRL_DIR` — default `./data/xbrl_files`
- `PDF_DIR` — default `./data/pdfs`
- `PARSED_DIR` — default `./data/parsed` (chunks.json output)
- `PDF_DOWNLOAD_LIMIT` — cap on stage 3 downloads per run (default 500)
- `PARSE_BATCH_SIZE` — cap on stage 3.5 parses per run (default 10)
- `INGEST_BATCH_SIZE` — cap on stage 4 ingests per run (default 5)
- `PARSED_KEEP_FULL` — when true, retain the raw DoclingDocument JSON
  alongside the chunks JSON (dev debugging; default false)

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

- Docker image is intentionally large (~3.5–5 GB) because Docling's layout
  model, TableFormer, and EasyOCR English models are baked in for offline
  operation. `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` are set at
  runtime — any accidental cache miss raises an error rather than silently
  reaching for the internet.
- Python target inside the Docker image is 3.11 (bumped from 3.9 so Docling's
  transitive deps install cleanly). Local dev still works on 3.9+ if you
  don't run Docling locally; the `# type: (...)` comment-style hints are
  kept for consistency across the codebase.
- `urllib3<2` is pinned in `requirements.txt` for macOS LibreSSL
  compatibility on host systems. It's functionally moot inside the Debian
  container but harmless.
- Stage 2 (`metadata.py`) is **insert-only** — no upsert. Rerunning against
  the same XBRL will insert duplicates unless the Supabase table has a
  uniqueness constraint on `(scrip_code, announcement_datetime, subject)` or
  similar. Check the table before backfilling.
- Stage 3 was rewritten to skip Selenium — `--no-headless` is a deprecated
  no-op kept for CLI compatibility. The BSE JSON endpoint is called directly
  and XBRL/PDF files are fetched via `requests`.
- Stage 3.5's converter singletons load Docling models once per process and
  reuse them across the batch. Cold-start (first parse) takes 15–30s while
  models load into RAM; subsequent parses are fast. Provision >= 4 GB RAM
  on the cron host.
- `_repair_missing_pdf()` from the old `ingest.py` was removed. If a
  `local_pdf_path` points at a missing file, stage 3.5 flags it as
  `corrupt_pdf` and the row will be re-picked once stage 3 re-downloads
  (follow-up: automate the clear-and-redownload path).
- The whole pipeline talks to Supabase using the service-role key. Never
  commit `.env` — it's in `.gitignore` already.
- `data/` (including `data/parsed/`) is gitignored and recreated on first
  run by `ensure_dirs()`.
- Supabase schema for stage 3.5 lives in `migrations/001_parse_stage_columns.sql`;
  apply it manually via `psql` or the Supabase SQL editor before deploying
  the parser stage.
