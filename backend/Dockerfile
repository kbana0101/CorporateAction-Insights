# Build context: repo root (needed for shared yarn.lock and root node_modules)

# ── Stage 1: install workspace dependencies ───────────────────────────────────
FROM node:22-alpine AS deps
WORKDIR /app

COPY package.json yarn.lock ./
COPY frontend/package.json ./frontend/
COPY backend/package.json  ./backend/

RUN yarn install --frozen-lockfile --ignore-engines

# ── Stage 2: runtime (LangGraph dev server) ───────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

COPY --from=deps /app/node_modules        ./node_modules
COPY --from=deps /app/backend/node_modules ./backend/node_modules

# Copy only the backend source
COPY backend/ ./backend/

WORKDIR /app/backend

EXPOSE 2024

# Use the lockfile-pinned CLI from node_modules — bare `npx @langchain/langgraph-cli`
# resolves to the latest release and breaks against @langchain/langgraph@0.2.x in this repo.
# PORT is injected by Render (or any cloud host); falls back to 2024 locally
CMD ["sh", "-c", "../node_modules/.bin/langgraphjs dev --host 0.0.0.0 --port ${PORT:-2024}"]
