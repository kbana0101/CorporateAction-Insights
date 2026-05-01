# Build context: repo root (needed for shared yarn.lock and root node_modules)

# ── Stage 1: install workspace dependencies ───────────────────────────────────
FROM node:22-alpine AS deps
WORKDIR /app

COPY package.json yarn.lock ./
COPY frontend/package.json ./frontend/
COPY backend/package.json  ./backend/

RUN yarn install --frozen-lockfile --ignore-engines

# ── Stage 2: build the Next.js app ───────────────────────────────────────────
FROM node:22-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules         ./node_modules
COPY --from=deps /app/frontend/node_modules ./frontend/node_modules

COPY frontend/ ./frontend/

WORKDIR /app/frontend

ARG NEXT_PUBLIC_LANGGRAPH_API_URL=http://localhost:2024
ENV NEXT_PUBLIC_LANGGRAPH_API_URL=$NEXT_PUBLIC_LANGGRAPH_API_URL

RUN yarn build

# ── Stage 3: runtime image ────────────────────────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 nextjs

# Copy root node_modules (contains next, react, etc.)
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules

# Copy built app
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next   ./frontend/.next
COPY --from=builder --chown=nextjs:nodejs /app/frontend/public  ./frontend/public
COPY --from=builder --chown=nextjs:nodejs /app/frontend/package.json ./frontend/package.json

USER nextjs
EXPOSE 3000

WORKDIR /app/frontend
CMD ["../node_modules/.bin/next", "start"]
