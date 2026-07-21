# frontend/

Next.js 14 App Router UI. Two user-facing pages plus a set of API routes that
proxy to the backend LangGraph server and read from Supabase.

## Pages

| Route | File | Purpose |
|---|---|---|
| `/` | `app/page.tsx` | Landing (minimal) |
| `/chat` | `app/chat/page.tsx` | Streaming chat UI. Accepts `?doc_id=<uuid>` to scope retrieval to one PDF |
| `/corporate-actions` | `app/corporate-actions/page.tsx` + `CorporateActionsClient.tsx` | Browsable list of ingested BSE actions filterable by category |

## API routes (`app/api/`)

| Route | Backing |
|---|---|
| `POST /api/ingest` | Accepts multipart form (`files[]`, `metadata` JSON). Calls the backend `ingestion_graph` via `langGraphServerClient`. Max 5 files, 1000MB each, PDF only |
| `POST /api/chat` | Streams SSE from the backend `retrieval_graph`. Body: `{ message, threadId, docId? }` |
| `GET /api/pdf?path=<abs-path>` | Streams a local PDF from the filesystem. **Server reads by absolute path — no auth, no sandboxing.** Only safe when the server has trusted access to the paths written by the ingestion pipeline |
| `GET /api/corporate-actions?category=<cat>` | Queries Supabase `corporate_actions` for today's IST trading date |
| `GET /api/corporate-actions/by-id?id=<uuid>` | Single row lookup |
| `GET /api/corporate-actions/categories` | Distinct categories list |

## Directory map

```
app/
├── page.tsx                  # landing
├── layout.tsx                # root layout (themes, fonts)
├── globals.css               # Tailwind entry
├── chat/                     # /chat streaming UI
├── corporate-actions/        # /corporate-actions list + client components + getCorporateActions()
└── api/                      # route handlers listed above

components/
├── chat-message.tsx, example-prompts.tsx, file-preview.tsx, theme-provider.tsx
└── ui/                       # shadcn/ui primitives (Radix + Tailwind)

lib/
├── langgraph-server.ts       # server-side LangGraph client (singleton, lazy)
├── langgraph-client.ts       # browser-side LangGraph client
├── langgraph-base.ts         # shared wrapper (createThread, streamRun helpers)
├── supabase-server.ts        # server Supabase client + getTodayIST()
├── pdf.ts                    # processPDF() — uses pdf-parse for text extraction
└── utils.ts                  # cn() helper (clsx + tailwind-merge)

constants/graphConfigs.ts     # retrievalAssistantStreamConfig, indexConfig — keep in sync with backend defaults
types/graphTypes.ts           # AgentConfiguration, IndexConfiguration, PDFDocument, AgentState, …
hooks/                        # use-mobile, use-toast
```

## Common commands

```bash
yarn dev           # http://localhost:3000 (next dev)
yarn build         # next build
yarn start         # production server
yarn lint          # next lint
yarn test          # jest (jsdom)
```

Tests live under `__tests__/api/`.

## Non-obvious things

- **All API routes set `export const dynamic = 'force-dynamic'`** because they
  either stream, read secrets, or hit Supabase per-request. Don't remove this
  or Next will try to statically prerender them.
- `supabase-server.ts` overrides `fetch` with `cache: 'no-store'` — Next
  otherwise caches Supabase responses via its patched fetch. Do the same for
  any new server-side Supabase clients.
- `langgraph-server.ts` throws if `NEXT_PUBLIC_LANGGRAPH_API_URL` or
  `LANGCHAIN_API_KEY` are unset. The client is a lazy `Proxy` — importing at
  module top-level is safe; initialisation is deferred to first request.
- `getTodayIST()` in `supabase-server.ts` is the canonical "today" for
  corporate-actions listing — timezone matters (BSE trading date is IST).
- shadcn/ui components in `components/ui/` are generated; don't hand-edit —
  regenerate via the shadcn CLI (config in `components.json`).
- `MAX_FILE_SIZE` in `app/api/ingest/route.ts` is 1000MB despite the error
  message saying "less than 10MB". Fix message before adjusting size.
- `pdf.ts` uses `pdf-parse`, which has a well-known require-time side effect
  that reads a test PDF; if you refactor, keep it lazy-imported.
