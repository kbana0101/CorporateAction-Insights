# CorporateAction-Insights

Monorepo that ingests BSE corporate-action announcements as PDFs, indexes them
with LangGraph + Supabase pgvector, and exposes a Next.js chat UI on top.

## Workspaces

Managed by Turborepo + Yarn workspaces (declared in `package.json`). Only
`backend/` and `frontend/` are true JS workspaces; `ingestion/` is a standalone
Python project.

| Path | Runtime | Purpose |
|---|---|---|
| `backend/` | Node/TS (LangGraph.js) | Ingestion + Retrieval graphs, served by `langgraphjs dev` on `:2024` |
| `frontend/` | Next.js 14 (App Router) | Chat UI + REST wrappers that call the LangGraph server |
| `ingestion/` | Python 3.9+ | Nightly crawler → parses BSE XBRL → downloads PDFs → POSTs to frontend `/api/ingest` |
| `scripts/` | Node | `checkLanggraphPaths.js` lints `backend/langgraph.json` paths |
| `xbrl_files/` | data | Legacy/sample XBRL sources; not consumed by current pipeline (ingestion writes to `ingestion/data/xbrl_files/`) |

## Data flow

```
BSE public API  ──►  ingestion/  ──►  Supabase (corporate_actions table)
                        │                 │
                        ▼                 ▼
                     PDFs on disk   frontend /corporate-actions (list view)
                        │
                        ▼
             frontend /api/ingest ──► backend ingestion_graph ──► pgvector
                                                                       │
      frontend /chat (SSE) ──► /api/chat ──► backend retrieval_graph ──┘
```

## Common commands

```bash
# from root
yarn install                  # installs both workspaces
yarn build                    # turbo build across workspaces
yarn lint / lint:fix / format

# backend (LangGraph server)
cd backend && yarn langgraph:dev        # http://localhost:2024

# frontend
cd frontend && yarn dev                 # http://localhost:3000

# ingestion pipeline (one-shot; see ingestion/CLAUDE.md for flags)
cd ingestion && ./run_ingest.sh
```

Frontend expects the backend to be reachable at `NEXT_PUBLIC_LANGGRAPH_API_URL`
(default `http://localhost:2024`). Ingestion expects the frontend's `/api/ingest`
to be reachable at `INGEST_API_URL`.

## Deployment

- `render.yaml` — backend LangGraph service
- `vercel.json` — frontend deployment on Vercel
- `docker-compose.yml` + per-service `Dockerfile`s exist for local containerised
  runs

## Non-obvious things

- The upstream template README (`README.md`) still describes the generic
  "AI PDF chatbot" starter and doesn't mention the corporate-actions layer.
  For pipeline-specific details, prefer `ingestion/README.md` and the
  per-workspace CLAUDE.md files.
- `README_old.md` is an unused copy of the pre-fork README — don't edit it.
- `node_modules/` at the repo root is populated by Yarn workspaces; both
  `backend/` and `frontend/` also have their own hoisting exceptions.
- Env vars live in each workspace's `.env` (never at root). See `.env.example`
  in `backend/`, `frontend/`, and `ingestion/`.
- Supabase `documents` table (vector store) and `corporate_actions` table
  (metadata) coexist in the same project. The frontend uses the
  `SUPABASE_SERVICE_ROLE_KEY` — RLS is bypassed.
