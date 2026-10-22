---
name: fastapi
description: FastAPI conventions for the Academic AI Advisor HTTP layer (src/server/) — routers/services separation, dependency injection through FastAPI Depends for services and managers (advisor agent, SQL/Chroma db managers), and typed request/response contracts as Pydantic models. Use when creating, modifying, or reviewing FastAPI code, endpoints, DI providers, schemas, or app setup.
---

# FastAPI server conventions

Scope: `src/server/` (FC37). The server is a thin adapter over `agent`/`database`/`core`; nothing in those zones may import it.

## Layout — routers / services / schemas

```text
src/server/
├── app.py                # app factory + lifespan (init managers, seed/ingest); mounts routers + error handlers
├── dependencies.py       # all DI providers — the single place instances come from
├── errors.py             # error envelope + exception handlers (404 not_found, 422 validation_failed, 503 llm_unavailable)
├── routers/              # one file per resource: chat.py, plans.py, degrees.py, audits.py
│   └── <resource>.py     # APIRouter: paths + methods only, zero business logic; calls the service directly
├── services/             # business logic; wraps AIAdvisorAgent, db managers, core engine
└── schemas/              # Pydantic request/response models per resource
```

Flow rule: **router (HTTP shape only) → service (business logic) → core/database.**
Routers never touch db managers or construct services — they receive services via `Depends`.
(There is deliberately no controller layer: it was pure pass-through and was removed in the 2026-10-23 simplification pass.)

Route style: `@router.get("/path")` with the response type as the function's return annotation (FastAPI infers `response_model`). One-line docstring with the FC ids.

## Dependency injection

- Every service, manager, and agent instance comes from a provider in `dependencies.py`:
  `get_advisor_agent()`, `get_sql_db_manager()`, `get_vector_db_manager()`, `get_current_student()`.
- `get_current_student()` is the pre-auth session per FC36 (student id from header/context) — never build auth flows.
- Providers create once (lifespan state or module-level cache) — one agent graph and one db connection set per app process.
- Tests override providers with `app.dependency_overrides`; never monkeypatch class internals or reach into singletons.

## Request/response contracts (Pydantic)

- Every endpoint has a Pydantic return annotation (FastAPI uses it as `response_model`) and typed request bodies — no bare dicts in or out.
- Schemas live in `schemas/` (Pydantic v2); they map explicitly from internal entities — internal domain objects are never returned raw.
- Responses echo what SQLite/Chroma returned: an empty lookup is an empty list + a message, never fabricated filler.
- Domain failures map to HTTP status codes via the handlers in `errors.py` (`RecordNotFoundError` → 404, `InvalidRequestError` → 422, `LLMError` → 503); don't swallow them into generic 500s.

## Repo rules in the HTTP layer

- **POC fidelity (2026-10-22):** keep endpoints thin and honest, not hardened — no pagination, rate limiting, or exhaustive error taxonomies beyond what the frontend renders (`not_found`, `validation_failed`, `llm_unavailable`).
- Endpoints that recommend, audit, or plan must produce results through the deterministic engine in `core` (FC29–FC32, FC2, FC25–FC26) — never by asking the LLM.
- Actions taken on the student's behalf (add/drop class, create/modify plan — FC20–FC21, FC23) require proof of explicit user confirmation in the confirming request (e.g. a confirmation token/flag carried from the UI dialog); unconfirmed action requests are rejected.
- Chat/session state persists through `SQLDatabaseManager` (FC34), not FastAPI session state.
- Cite FC IDs in endpoint docstrings ("FC23-confirmed plan modification").

## Tests

Business-logic tests live in `services/` and `core` (scope per `<tester>` skill). A thin `TestClient` smoke test per resource is optional — endpoints and schemas need no dedicated unit-test suite.