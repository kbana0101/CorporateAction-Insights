# Corporate Action Insights

An AI-powered platform for exploring BSE (Bombay Stock Exchange) corporate-action announcements. The system fetches announcement metadata and PDF attachments, stores structured records in Supabase, embeds document content in a vector database, and lets you ask natural-language questions over those filings through a chat interface.

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Quick Start](#quick-start)
6. [Environment Variables](#environment-variables)
7. [Supabase Setup](#supabase-setup)
8. [Running Locally](#running-locally)
9. [Usage](#usage)
10. [Running Tests](#running-tests)
11. [Production & Deployment](#production--deployment)
12. [Customization](#customization)
13. [Troubleshooting](#troubleshooting)
14. [Contributing](#contributing)
15. [License](#license)

---

## Features

- **BSE ingestion pipeline** — Fetches corporate-action announcements from BSE, parses XBRL metadata, downloads PDF attachments, and pushes them into the chatbot ingestion API.
- **Corporate Actions dashboard** — Browse today's announcements by category, see ingestion status, and open linked PDFs.
- **Document ingestion graph** — Parses PDFs, chunks text, and stores vector embeddings in Supabase.
- **Retrieval graph** — Routes user questions, retrieves relevant document chunks, and generates answers with source references.
- **Streaming chat UI** — Real-time responses with optional source citations.
- **LangGraph orchestration** — Ingestion and retrieval workflows are modeled as LangGraph state machines, debuggable via LangGraph Studio.

---

## Architecture

```
┌──────────────────────┐     crawl / parse / download     ┌─────────────────────┐
│  Ingestion (Python)  │ ─────────────────────────────────> │      Supabase       │
│  BSE API → XBRL/PDF  │                                    │ corporate_actions   │
└──────────┬───────────┘                                    │ documents (vectors)│
           │ POST /api/ingest                                 └──────────┬──────────┘
           v                                                              │
┌──────────────────────┐   LangGraph API (port 2024)                      │
│  Frontend (Next.js)  │ <──────────────────────────────────────────────> │
│  Chat + CA dashboard │                                                    │
└──────────┬───────────┘                                                    │
           │                                                                 │
           v                                                                 v
┌──────────────────────┐                                    ┌─────────────────────┐
│  Backend (LangGraph) │ ─── embeddings + retrieval ──────> │  OpenAI + Supabase  │
│  ingestion_graph     │                                    │  vector search      │
│  retrieval_graph     │                                    └─────────────────────┘
└──────────────────────┘
```

| Component | Stack | Role |
|-----------|-------|------|
| `frontend/` | Next.js 14, React, Tailwind | Web UI, API routes for chat/ingest/corporate actions |
| `backend/` | Node.js, TypeScript, LangGraph | Ingestion and retrieval agent graphs |
| `ingestion/` | Python 3.9+ | Automated BSE data pipeline |
| Supabase | Postgres + pgvector | Metadata store and vector search |
| OpenAI | GPT + embeddings | Language model and vector embeddings |

---

## Project Structure

```
CorporateAction-Insights/
├── backend/                 # LangGraph agents (ingestion + retrieval)
│   ├── src/
│   │   ├── ingestion_graph/
│   │   ├── retrieval_graph/
│   │   └── shared/
│   └── langgraph.json
├── frontend/                # Next.js web application
│   └── app/
│       ├── chat/
│       ├── corporate-actions/
│       └── api/
├── ingestion/               # BSE corporate-actions pipeline
│   ├── main.py              # Single entry point for all stages
│   └── ingestion/
│       ├── crawler.py       # Stage 1: fetch XBRL from BSE
│       ├── metadata.py      # Stage 2: parse XBRL → Supabase
│       ├── pdfs.py          # Stage 3: download PDF attachments
│       └── ingest.py        # Stage 4: POST PDFs to /api/ingest
├── xbrl_files/              # Sample XBRL files (optional local data)
└── package.json             # Yarn workspaces root (backend + frontend)
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Node.js 18+** | Node 20+ recommended; backend LangGraph config targets Node 22 |
| **Yarn** | Monorepo uses Yarn workspaces |
| **Python 3.9+** | For the BSE ingestion pipeline |
| **Supabase project** | Stores `corporate_actions` metadata and `documents` vectors |
| **OpenAI API key** | Used for embeddings and chat completions |
| **LangSmith API key** | Optional; recommended for tracing and debugging |

---

## Quick Start

```bash
# 1. Clone and install Node dependencies
git clone <your-repo-url>
cd CorporateAction-Insights
yarn install

# 2. Configure environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp ingestion/.env.example ingestion/.env
# Edit each .env with your Supabase and OpenAI credentials

# 3. Set up Supabase tables (see Supabase Setup below)

# 4. Start backend + frontend (in separate terminals)
cd backend && yarn langgraph:dev    # http://localhost:2024
cd frontend && yarn dev             # http://localhost:3000

# 5. (Optional) Run the BSE ingestion pipeline
cd ingestion
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Open [http://localhost:3000](http://localhost:3000) — the app redirects to the chat page. Use the sidebar to switch between **Chat** and **Corporate Actions**.

---

## Environment Variables

### Backend (`backend/.env`)

```env
OPENAI_API_KEY=your-openai-api-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Optional: LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=corporate-action-insights
```

### Frontend (`frontend/.env`)

```env
NEXT_PUBLIC_LANGGRAPH_API_URL=http://localhost:2024
LANGGRAPH_INGESTION_ASSISTANT_ID=ingestion_graph
LANGGRAPH_RETRIEVAL_ASSISTANT_ID=retrieval_graph

# Optional: LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=corporate-action-insights
```

### Ingestion pipeline (`ingestion/.env`)

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
INGEST_API_URL=http://localhost:3000/api/ingest

XBRL_DIR=./data/xbrl_files
PDF_DIR=./data/pdfs
PDF_DOWNLOAD_LIMIT=500
INGEST_BATCH_SIZE=5
```

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_LANGGRAPH_API_URL` | LangGraph server URL (default `http://localhost:2024`) |
| `LANGGRAPH_INGESTION_ASSISTANT_ID` | Graph ID for document ingestion (`ingestion_graph`) |
| `LANGGRAPH_RETRIEVAL_ASSISTANT_ID` | Graph ID for Q&A (`retrieval_graph`) |
| `INGEST_API_URL` | Frontend ingest endpoint the Python pipeline calls |
| `SUPABASE_SERVICE_ROLE_KEY` | Bypasses RLS — keep secret, never commit |

---

## Supabase Setup

You need two tables in your Supabase project.

### 1. Vector store (`documents` + `match_documents`)

Follow the [LangChain Supabase integration guide](https://js.langchain.com/docs/integrations/vectorstores/supabase/) to create:

- A `documents` table with an embedding column (pgvector)
- A `match_documents` RPC function for similarity search

The backend uses `text-embedding-3-small` embeddings and queries via the `match_documents` function.

### 2. Corporate actions metadata (`corporate_actions`)

Create a table to hold parsed BSE announcement metadata:

```sql
create table corporate_actions (
  id uuid primary key default gen_random_uuid(),
  scrip_code text,
  company text,
  subject text,
  description text,
  category text,
  announcement_type text,
  attachment_url text,
  local_pdf_path text,
  announcement_datetime timestamptz,
  trading_date date,
  source text default 'BSE',
  ingested_at timestamptz
);

create index idx_corporate_actions_trading_date on corporate_actions (trading_date);
create index idx_corporate_actions_category on corporate_actions (category);
```

Consider adding a unique constraint on `(scrip_code, announcement_datetime, subject)` if you want to prevent duplicate inserts when re-running the metadata stage.

---

## Running Locally

The app has three runnable parts. For full functionality, start the backend and frontend first, then optionally run the ingestion pipeline.

### Backend (LangGraph server)

```bash
cd backend
yarn langgraph:dev
```

Starts LangGraph on [http://localhost:2024](http://localhost:2024) and opens LangGraph Studio for debugging graph runs.

### Frontend (Next.js)

```bash
cd frontend
yarn dev
```

Serves the UI at [http://localhost:3000](http://localhost:3000).

### Ingestion pipeline (Python)

```bash
cd ingestion
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

#### Pipeline stages

| Stage | Module | Description |
|-------|--------|-------------|
| 1 | `crawler.py` | Fetch BSE announcements for a date; save XBRL XML |
| 2 | `metadata.py` | Parse XBRL; insert rows into `corporate_actions` |
| 3 | `pdfs.py` | Download PDF attachments for pending rows |
| 4 | `ingest.py` | POST PDFs to `/api/ingest`; set `ingested_at` |

#### CLI flags

```bash
python main.py --date 21/06/2026          # Target date (DD/MM/YYYY; default: today)
python main.py --skip-crawl               # Skip stage 1
python main.py --skip-metadata            # Skip stage 2
python main.py --skip-download            # Skip stage 3
python main.py --skip-ingest              # Skip stage 4
python main.py -v                         # Verbose (debug) logging
```

Examples:

```bash
# Re-ingest only pending PDFs (backend + frontend must be running)
python main.py --skip-crawl --skip-metadata --skip-download

# Fetch a specific date and stop after metadata
python main.py --date 20/06/2026 --skip-download --skip-ingest
```

See [`ingestion/README.md`](ingestion/README.md) for pipeline-specific details.

### Monorepo scripts (root)

```bash
yarn build          # Build backend + frontend via Turborepo
yarn lint           # Lint all workspaces
yarn format         # Format all workspaces
```

---

## Usage

### Corporate Actions dashboard

1. Navigate to **Corporate Actions** in the sidebar.
2. Filter announcements by category.
3. Rows show company, subject, announcement time, and whether the PDF has been ingested.
4. Run the ingestion pipeline (or upload PDFs manually in chat) to populate searchable content.

### Chat

1. Go to **Chat** in the sidebar.
2. Upload PDFs via the paperclip icon (up to 5 files per request), or chat against documents already ingested by the pipeline.
3. Ask questions about corporate filings — answers stream in real time.
4. When documents are retrieved, use **View Sources** to see the chunks used in the response.

### LangGraph Studio

With the backend running, open LangGraph Studio (linked from the `langgraph:dev` output) to inspect graph state, step through nodes, and debug ingestion/retrieval runs.

---

## Running Tests

### Backend

```bash
cd backend
yarn test                  # All unit tests
yarn test:int              # Integration tests (requires .env with Supabase + OpenAI)
yarn test:coverage         # Coverage report
```

Integration tests need valid `OPENAI_API_KEY`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` in `backend/.env`.

### Frontend

```bash
cd frontend
yarn test
```

---

## Production & Deployment

### Backend

Deploy the LangGraph agent using either:

- [LangGraph Cloud](https://langchain-ai.github.io/langgraph/cloud/quick_start/)
- [Self-hosted deployment](https://langchain-ai.github.io/langgraph/how-tos/deploy-self-hosted/)

Set `NEXT_PUBLIC_LANGGRAPH_API_URL` in the frontend to your deployed backend URL.

### Frontend

Deploy to any Next.js-compatible host (Vercel, Netlify, etc.). Configure all frontend environment variables in the hosting dashboard.

### Ingestion pipeline

Run `python main.py` on a schedule (cron, GitHub Actions, etc.) with backend and frontend reachable at the configured `INGEST_API_URL`.

---

## Customization

### Backend

| File | What to change |
|------|----------------|
| `backend/src/shared/configuration.ts` | Default retriever settings, model provider, k-value |
| `backend/src/retrieval_graph/prompts.ts` | System prompts for routing and answer generation |
| `backend/src/shared/retrieval.ts` | Vector store / retriever implementation |

### Frontend

| File | What to change |
|------|----------------|
| `frontend/app/api/ingest/route.ts` | Upload limits, file validation |
| `frontend/constants/graphConfigs.ts` | Default config sent to LangGraph graphs |

### Ingestion

| File | What to change |
|------|----------------|
| `ingestion/ingestion/crawler.py` | BSE API date/source logic |
| `ingestion/.env` | Batch sizes, directory paths, ingest URL |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `.env` not loaded | Copy `.env.example` → `.env` in each sub-project; restart dev servers |
| LangGraph connection errors | Confirm backend is running on port 2024 and `NEXT_PUBLIC_LANGGRAPH_API_URL` matches |
| Supabase vector errors | Verify `documents` table and `match_documents` function exist ([LangChain docs](https://js.langchain.com/docs/integrations/vectorstores/supabase/)) |
| No corporate actions shown | Run the ingestion pipeline or check `corporate_actions` has rows for today's `trading_date` |
| OpenAI errors | Verify `OPENAI_API_KEY` and account quota |
| Ingest pipeline fails at stage 4 | Ensure frontend (`yarn dev`) and backend (`yarn langgraph:dev`) are both running |
| Duplicate metadata rows | Re-running stage 2 without a unique constraint inserts duplicates — add a constraint or skip stage 2 on reruns |

---

## Contributing

We welcome contributions. Please read [CONTRIBUTION.md](CONTRIBUTION.md) for development workflow, coding standards, and pull request guidelines.

---

## License

This project is licensed under the [MIT License](LICENSE).
