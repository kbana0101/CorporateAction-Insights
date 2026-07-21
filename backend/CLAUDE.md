# backend/

LangGraph.js server that hosts two graphs consumed by the frontend.

## Entry point

`langgraph.json` registers the compiled graphs by path:

```
ingestion_graph  → src/ingestion_graph/graph.ts:graph
retrieval_graph  → src/retrieval_graph/graph.ts:graph
```

`yarn langgraph:dev` runs `langgraphjs dev` (from `@langchain/langgraph-cli`),
which serves both graphs on `http://localhost:2024` with a Studio UI.

`node_version` in `langgraph.json` is pinned to `22`.

## Directory map

```
src/
├── ingestion_graph/     # single-node graph: docs → SupabaseVectorStore
│   ├── graph.ts         # StateGraph wiring; entry point registered in langgraph.json
│   ├── configuration.ts # ingestion-only knobs (docsFile, useSampleDocs, …)
│   └── state.ts         # IndexStateAnnotation (docs[])
│
├── retrieval_graph/     # router → (retrieve → generate | direct answer)
│   ├── graph.ts         # 4 nodes: checkQueryType, retrieveDocuments, generateResponse, directAnswer
│   ├── configuration.ts # AgentConfiguration (queryModel, …)
│   ├── prompts.ts       # ROUTER_SYSTEM_PROMPT, RESPONSE_SYSTEM_PROMPT
│   ├── state.ts         # AgentStateAnnotation (query, route, documents, messages)
│   └── utils.ts         # formatDocs()
│
├── shared/              # shared between both graphs
│   ├── configuration.ts # BaseConfigurationAnnotation (retrieverProvider, k, filterKwargs)
│   ├── retrieval.ts     # makeRetriever() — currently supabase only
│   ├── state.ts         # reduceDocs()
│   └── utils.ts         # loadChatModel()
│
└── sample_docs.json     # fallback corpus when useSampleDocs=true

app/, db/, jobs/         # empty stubs from an earlier iteration — safe to ignore
demo.ts, ingest-demo.ipynb  # standalone demos, not wired into the server
```

## Retrieval flow

`retrieval_graph` routes every query through `checkQueryType` (LLM with a Zod
schema → `route: 'retrieve' | 'direct'`). "retrieve" goes to
`retrieveDocuments` → `generateResponse`; "direct" goes to `directAnswer`.

`docId` is passed via `config.configurable.docId` and injected into
`filterKwargs` inside `shared/retrieval.ts` — this scopes retrieval to a
single ingested document. If no `docId` is supplied, the filter is empty
(retrieval spans all docs).

## Configuration surface

Callers configure a run by passing `configurable: {...}` on the invocation.
Defaults are read via `ensureBaseConfiguration` / `ensureAgentConfiguration` /
`ensureIndexConfiguration`. Common knobs:

- `queryModel` — e.g. `openai/gpt-4o-mini` (loaded via `loadChatModel`)
- `k` — number of docs to retrieve (default 5)
- `retrieverProvider` — currently only `supabase`
- `filterKwargs` — Supabase vector filter (merged with `docId`)
- `useSampleDocs` — ingestion falls back to `src/sample_docs.json` if `docs` is empty

The frontend's canonical config values live in
`frontend/constants/graphConfigs.ts` — keep the two in sync.

## Common commands

```bash
yarn langgraph:dev          # dev server on :2024
yarn build                  # tsc → dist/
yarn test                   # jest
yarn test:int               # only *.int.test.ts
yarn lint                   # eslint src
yarn lint:langgraph-json    # verify graph paths in langgraph.json exist
yarn demo                   # runs demo.ts standalone (not the server)
```

Tests live in `__tests__/{ingestion_graph,retrieval_graph}/`. `test_docs/`
holds fixture PDFs and `docSplits.json` used by ingestion tests.

## Non-obvious things

- ESM module (`"type": "module"` in `package.json`) — all local imports use
  the `.js` extension even though sources are `.ts` (e.g. `./state.js`). Don't
  "fix" these to `.ts`.
- Supabase requires a `documents` table and a `match_documents` SQL function.
  See the LangChain Supabase vector store docs; project doesn't include the
  SQL.
- `.langgraph_api/` is dev-server state — gitignored, safe to delete.
- Adding a new retriever: extend the `switch` in `shared/retrieval.ts` and the
  `retrieverProvider` union in `shared/configuration.ts`.
