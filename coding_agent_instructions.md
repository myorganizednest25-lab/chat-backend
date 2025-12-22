You are Codex. Generate a complete, production-ready GitHub repo for a chat backend that answers parent questions using an LLM with retrieval over entity-specific documents. Use Python.

# High-level goals
- Chat API backend with swappable LLM providers (OpenAI first, but easy to add others).
- Persist chat sessions + messages + extracted entity + retrieval results.
- Initial flow (rule-based-ish) but architecture must cleanly evolve into more agentic workflows later.
- Retrieval: “detect entity from query → retrieve all documents for that entity → send to LLM along with session context”.
- Clean separation between: API layer, services/orchestration, LLM provider interface, storage layer, retrieval layer.
- Entities already live in a Supabase Postgres table; do not recreate them.
- Raw documents are also stored in Supabase in a separate Postgres table.

# Tech requirements
- Framework: FastAPI
- Dependency management: uv (preferred) or poetry; include lock file if applicable.
- DB: Postgres (target Supabase). Use SQLAlchemy 2.0 + Alembic migrations.
- Use pydantic settings for config. Support local dev with docker-compose.
- Observability: structured logging + request ids. Optional OpenTelemetry hooks.
- Testing: pytest with unit tests for entity detection, retrieval, provider swap, and an integration test for /chat.

# Data model (must implement)
Create tables via Alembic migrations:
1) chat_sessions
   - id (uuid pk)
   - user_id (nullable text)  # allow anonymous
   - created_at (timestamptz default now)
   - updated_at (timestamptz default now)

2) chat_messages
   - id (uuid pk)
   - session_id (fk -> chat_sessions.id)
   - role (text: 'user'|'assistant'|'system')
   - content (text)
   - created_at (timestamptz default now)
   - metadata (jsonb default '{}')  # store tokens, provider, etc.

3) session_state
   - session_id (pk fk -> chat_sessions.id)
   - state (jsonb default '{}')   # holds entity_id, last intent, etc.
   - updated_at (timestamptz default now)

Also add:
- trigger/function to auto-update updated_at where appropriate
- indexes on entity_documents.entity_id, chat_messages.session_id, entities(entity_type, city, state)

# API requirements
Implement endpoints:
- POST /v1/sessions  -> create session (returns session_id)
- GET  /v1/sessions/{session_id} -> session + recent messages
- POST /v1/chat
  request: { session_id, user_id?, message: string, city?, state? }
  response: { session_id, answer: string, entity: {id,name,type}?, citations: [], debug?: {} }
- Optional: GET /healthz

# Core chat workflow (must implement exactly for MVP)
In /v1/chat:
1) Save user message to chat_messages.
2) Detect entity from user query:
   - First pass: exact / fuzzy match against entities.name (case-insensitive).
   - If multiple matches, pick best score; if low confidence, set entity to null.
   - If city/state passed, use it to filter candidates.
   - Keep this in an EntityResolver service with a clean interface so it can be replaced later by an LLM-based router.
3) Retrieve all documents for the resolved entity:
   - For MVP, simply fetch ALL entity_documents rows for that entity_id (limit configurable, e.g. 20 most recent by fetched_at).
   - Return list of {title, source_url, content}.
4) Build LLM prompt:
   - Include a concise system prompt for “helpful, cite sources, be honest”.
   - Include the last N turns from chat_messages as session context (configurable window).
   - Include retrieved documents as context with stable citation keys (e.g. [doc1], [doc2]) and require the model to cite them when making factual claims.
5) Call LLM provider to generate answer.
6) Save assistant message to chat_messages with metadata including provider/model, tokens, entity_id, doc ids.
7) Return response with answer + citations (doc titles + urls).

# LLM Provider abstraction (must be swappable)
- Create an interface/protocol like LLMClient with method:
  - generate_chat(messages: list[ChatMessage], model: str, temperature: float, max_tokens: int) -> LLMResponse
- Implement OpenAI provider first using official OpenAI Python SDK.
- Implement a “MockProvider” for tests.
- Make provider selection configurable via env var (LLM_PROVIDER=openai|mock|...).
- Make model configurable (LLM_MODEL=...).

# Future agentic evolution (architecture requirement)
Even though MVP is linear, structure code so we can later:
- swap EntityResolver to an LLM-based classifier
- replace “retrieve all docs” with hybrid retrieval + embeddings
- add tool calls (web fetch, database lookup, calendar) behind a Tools interface
- introduce a Planner/Executor style agent
Do this by implementing a simple Orchestrator with well-defined steps and data classes, not a monolithic route handler.

# Repo structure (must produce)
- README.md with setup, env vars, how to run locally, how to run tests
- docker-compose.yml for local Postgres
- app/
  - main.py (FastAPI)
  - api/routes.py
  - core/config.py
  - core/logging.py
  - db/session.py, db/models.py, db/migrations/ (alembic)
  - services/orchestrator.py
  - services/entity_resolver.py
  - services/retrieval.py
  - llm/base.py, llm/openai_provider.py, llm/mock_provider.py
  - schemas/ (pydantic request/response)
  - utils/ (fuzzy matching, citation formatting)
- tests/
  - unit tests for resolver/retrieval/provider swap
  - integration test hitting /v1/chat with TestClient

# Security & operational requirements
- Don’t log full user content by default (or make it configurable).
- Basic rate limiting stub (in-memory) with TODO for Redis.
- CORS configurable.
- Input validation and helpful error responses.

# Output
Generate all code files. Include Alembic migrations. Ensure `uv run` (or `poetry run`) can start the server. Ensure tests pass.
