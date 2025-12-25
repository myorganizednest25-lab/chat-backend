# Chat Backend

FastAPI backend that answers parent questions using retrieval over entity-specific documents with a swappable LLM layer.

## Features
- Swappable LLM providers (OpenAI + mock) with configurable model/temperature.
- Persistence for chat sessions/messages/state plus retrieval metadata.
- Entity resolution with fuzzy matching and city/state filters.
- Retrieval of all documents for an entity (stored as raw documents in Supabase Postgres) with citation formatting.
- Structured logging with request ids, CORS config, and in-memory rate limiting stub (TODO: Redis).

## Quickstart
1) Install dependencies (uses `uv`):  
   ```bash
   uv sync
   ```
2) Start Postgres locally:  
   ```bash
   docker-compose up -d db
   ```
3) Apply migrations (creates chat tables and required indexes on existing Supabase tables):  
   ```bash
   uv run alembic upgrade head
   ```
4) Run the API:  
   ```bash
   uv run uvicorn app.main:app --reload
   ```

## API
- `POST /v1/sessions` – create a chat session.
- `GET /v1/sessions/{id}` – fetch session with recent messages.
- `POST /v1/chat` – send a message `{session_id, user_id?, message, city?, state?}` → returns `{answer, entity?, citations[], debug?}`.
- `GET /healthz` – liveness probe.

## Configuration
Environment variables (pydantic settings):
- `DATABASE_URL` (default `postgresql+psycopg://chat:chat@localhost:5432/chat`)
- `LLM_PROVIDER` (`openai`|`mock`, default `mock`)
- `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`
- `OPENAI_API_KEY` (required for `openai` provider)
- `CORS_ORIGINS` (comma-separated)
- `HISTORY_WINDOW`, `MAX_DOCUMENTS`, `RATE_LIMIT_PER_MINUTE`
- `ENTITY_RESOLUTION_MODE` (`fuzzy`|`llm`, default `fuzzy`) and `ENTITY_RESOLUTION_CANDIDATE_LIMIT`

Entities and raw documents already live in Supabase Postgres tables (`entities`, `raw_documents`); migrations only add indexes and chat tables.

`.env` is loaded from the project root by default (`<repo>/.env`). If you run the server from elsewhere, make sure that file exists or export the variables in your shell.

## Project Structure
- `app/main.py` – FastAPI app + middleware
- `app/api/routes.py` – versioned routes and rate limiting
- `app/services/` – orchestrator, entity resolver, retrieval
- `app/llm/` – provider interfaces and implementations
- `app/db/` – SQLAlchemy models, session, Alembic migrations
- `app/schemas/`, `app/utils/` – pydantic models and helpers
- `tests/` – unit tests for resolver/retrieval/provider and integration test for `/v1/chat`

## Testing
```bash
uv run pytest
```
