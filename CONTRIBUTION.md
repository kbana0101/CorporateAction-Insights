# Contributing to Corporate Action Insights

Thank you for your interest in contributing. This guide covers how to set up a development environment, make changes, and submit them for review.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Ways to Contribute](#ways-to-contribute)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Coding Standards](#coding-standards)
6. [Testing](#testing)
7. [Pull Request Process](#pull-request-process)
8. [Reporting Issues](#reporting-issues)
9. [Security](#security)

---

## Code of Conduct

Be respectful and constructive in all project interactions. Focus on the technical merits of ideas and keep feedback actionable.

---

## Ways to Contribute

- **Bug fixes** — Reproduce the issue, fix the root cause, and add or update tests when practical.
- **Features** — Open an issue first for significant changes so approach and scope can be discussed.
- **Documentation** — Improve README, inline comments, or pipeline docs.
- **Ingestion pipeline** — Improve BSE fetching, XBRL parsing, PDF handling, or batch reliability.
- **Agent behavior** — Tune prompts, retrieval settings, or graph logic in the backend.
- **UI/UX** — Enhance the chat or corporate-actions dashboard.

---

## Development Setup

### 1. Fork and clone

```bash
git clone <your-fork-url>
cd CorporateAction-Insights
```

### 2. Install dependencies

```bash
# Node workspaces (backend + frontend)
yarn install

# Python ingestion pipeline
cd ingestion
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 3. Configure environment

Copy example env files and fill in credentials:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp ingestion/.env.example ingestion/.env
```

You will need:

- A Supabase project with `corporate_actions` and `documents` tables (see [README.md](README.md#supabase-setup))
- An OpenAI API key
- LangSmith credentials (optional but recommended for debugging graphs)

### 4. Run the stack locally

Use three terminals for full-stack work:

```bash
# Terminal 1 — LangGraph backend
cd backend && yarn langgraph:dev

# Terminal 2 — Next.js frontend
cd frontend && yarn dev

# Terminal 3 — (optional) ingestion pipeline
cd ingestion && source .venv/bin/activate && python main.py --skip-ingest
```

Verify the app at [http://localhost:3000](http://localhost:3000) and LangGraph Studio at [http://localhost:2024](http://localhost:2024).

---

## Making Changes

### Branch naming

Use descriptive branch names:

```
fix/ingest-timeout
feat/category-filter-export
docs/readme-supabase-setup
```

### Scope your changes

This repo has three main areas. Keep pull requests focused on one area when possible:

| Area | Path | Language |
|------|------|----------|
| LangGraph agents | `backend/src/` | TypeScript |
| Web app & API routes | `frontend/app/`, `frontend/components/` | TypeScript / React |
| BSE ingestion pipeline | `ingestion/` | Python |

Avoid unrelated formatting or drive-by refactors in the same PR as a feature or fix.

### Commit messages

Write clear, imperative commit messages:

```
fix ingestion: retry BSE PDF download on 404
feat frontend: add date picker to corporate actions view
docs: clarify Supabase setup steps
```

---

## Coding Standards

### TypeScript (backend + frontend)

- Match existing patterns in the file you are editing.
- Run lint and format before submitting:

```bash
cd backend && yarn lint && yarn format:check
cd frontend && yarn lint
```

- Prefer typed interfaces over `any`.
- Keep API route handlers thin; put reusable logic in `lib/` or shared modules.

### Python (ingestion)

- Follow PEP 8 style; keep functions focused on one pipeline stage.
- Use the existing `logging` setup rather than bare `print` statements.
- Do not commit `.env` files or downloaded PDFs/XBRL data from local runs.

### General

- Do not commit secrets, API keys, or service-role tokens.
- Add comments only for non-obvious business logic (e.g. BSE URL fallbacks, date/timezone handling).
- Reuse existing utilities (`config.py`, `supabase-server.ts`, shared LangGraph config) instead of duplicating setup code.

---

## Testing

All non-trivial changes should include tests or a documented manual test plan.

### Backend

```bash
cd backend
yarn test              # Unit tests
yarn test:int          # Integration tests (needs real Supabase + OpenAI in .env)
yarn test:changed      # Tests related to changed files
```

### Frontend

```bash
cd frontend
yarn test
```

### Ingestion

There is no automated test suite for the Python pipeline yet. For ingestion changes, document manual verification:

```bash
cd ingestion
python main.py --date DD/MM/YYYY --skip-ingest -v   # Stages 1–3 only
python main.py --skip-crawl --skip-metadata --skip-download -v  # Stage 4 only
```

Confirm:

- XBRL files appear under `ingestion/data/xbrl_files/`
- Rows are inserted into `corporate_actions`
- PDFs download to `ingestion/data/pdfs/`
- Stage 4 successfully calls `/api/ingest` and sets `ingested_at`

---

## Pull Request Process

1. **Sync** your branch with the latest default branch.
2. **Implement** your change with tests or a clear test plan.
3. **Run** lint and relevant tests locally.
4. **Open a PR** with:
   - A short summary of what changed and why
   - Steps to reproduce or verify the change
   - Screenshots for UI changes
   - Notes on env vars or Supabase migrations, if applicable
5. **Respond** to review feedback with focused follow-up commits.

### PR checklist

- [ ] Code builds and runs locally (backend + frontend, and ingestion if touched)
- [ ] Lint passes (`yarn lint` in affected workspaces)
- [ ] Tests added or updated, or manual test steps included in the PR description
- [ ] No secrets or large binary artifacts committed
- [ ] Documentation updated if behavior or setup changed

---

## Reporting Issues

When opening an issue, include:

1. **Summary** — What happened vs. what you expected
2. **Steps to reproduce** — Commands, dates, and config (redact secrets)
3. **Environment** — OS, Node version, Python version
4. **Logs** — Relevant terminal output or LangSmith trace links
5. **Screenshots** — For UI problems

Label ingestion issues with the pipeline stage (crawl, metadata, PDF download, ingest) when known.

---

## Security

- Never open a public issue with API keys, Supabase service-role keys, or `.env` contents.
- The Supabase **service role key** bypasses row-level security — treat it like a root password.
- Report security vulnerabilities privately to the repository maintainers rather than in a public issue.

---

Thank you for helping improve Corporate Action Insights.
