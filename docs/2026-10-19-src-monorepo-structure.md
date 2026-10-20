# Proposal: Layered `src/` monorepo structure

*Date: 2026-10-19 · Status: proposed (pre-implementation)*

## Summary

Restructure `src/` from the current two-file stub (`src/main/AI_Assistant.py` + the leftover `AI_Assistant 5.java`) into a layered monorepo with four top-level zones — `core`, `database`, `agent`, `frontend` — one per domain-model layer (§1/§2, §4, §3, §5). The organizing constraint is the repo's deterministic-engine-first rule: the `core` zone holds all domain entities and the planning/validation engine as pure Python with **zero LLM or database imports**, so `CourseRecommendationValidator` (FC29–FC32) and `DegreePlanGenerator` (FC2, FC25, FC26) stay unit-testable without a model or store.

## Scope

- **Existing FCs affected (indirect):**
  - FC29–FC32 (recommendation safeguards), FC2/FC25/FC26 (plan generation & comparison) — implemented in `core/`, never under the LangChain zone.
  - FC33 (data routing), FC9/FC35 (semantic search, requirement ingest) — `database/sql/` for SQLite, `database/vector/` for Chroma.
  - FC22–FC24 (assistant engine), FC27–FC28 (multi-turn clarification), FC23 (confirm-before-acting) — `agent/` tools + HTTP surface.
  - FC1–FC21, FC36 — served by `frontend/`; assistant actions confirmed in the UI layer (§5).
- **Genuinely new (proposed: `FC-new-rest-api`)** — an explicit HTTP transport between the React frontend and the Python agent (FastAPI). Currently implicit in the stack table; this proposal names it as its own package.

## Target tree

```
src/
├── core/                      # §1 + §2. Pure Python. NO langchain/db imports.
├── database/                  # §4. SQL + vector managers, schema, seed loaders.
├── agent/                     # §3. LangChain conversation layer + HTTP API.
└── frontend/                  # §5. React app (own toolchain: npm).
```

### `src/core/` — domain entities & deterministic engine

```
core/
├── __init__.py
├── entities/                  # §1 domain models (plain dataclasses)
│   ├── student.py             # Student, EnrollmentRecord
│   ├── course.py              # Course, CourseSection
│   └── degree.py              # DegreeRequirement, SemesterPlan, DegreePlan
├── engine/                    # §2 deterministic planning/validation
│   ├── validator.py           # CourseRecommendationValidator (FC29–FC32)
│   ├── plan_generator.py      # DegreePlanGenerator (FC2, FC25, FC26)
│   ├── major_switch.py        # simulate_major_switch (FC5a–c)
│   └── results.py             # ValidationResult, PlanComparisonResult
└── errors.py                  # domain-level exceptions (constraint failures, FC29–32 rejections)
```

Rules: no `langchain`, no I/O, no SDK imports beyond stdlib. Validators receive entities + the data they need as arguments (managers are passed in by callers, per §2 `sql_db` attribute).

### `src/database/` — persistence & retrieval

```
database/
├── __init__.py
├── base.py                    # DatabaseManager ABC (§4)
├── sql/
│   ├── sqlite_manager.py      # SQLDatabaseManager: students, sections, enrollments, plans, chat (FC34)
│   ├── schema.sql             # DDL for students/sections/enrollments/plans/chat_history
│   ├── migrations/            # numbered, forward-only .sql files
│   └── repositories/          # thin per-entity query modules (students.py, sections.py, plans.py)
├── vector/
│   ├── chroma_manager.py      # VectorDatabaseManager: ingest_documents, similarity_search (FC9, FC35)
│   └── embeddings.py          # embedding-model choice behind one seam
├── ingest/
│   ├── course_desc_loader.py  # data/course-desc.jsonl → documents (75-line seed corpus)
│   └── degree_pdf_ingest.py   # data/cse_undergrad_courses.pdf → DegreeRequirement records
└── seed.py                    # build/refresh SQLite + Chroma from data/
```

May import `core` (for entity mapping) and LangChain **core abstractions only** (`Embeddings`, vector-store types) — never the agent layer.

### `src/agent/` — LangChain conversation layer + HTTP transport

```
agent/
├── __init__.py
├── llm/
│   ├── advisor_agent.py       # AIAdvisorAgent: process_query, classify_query_intent (FC9/FC33 routing)
│   ├── graph.py               # build_advisor_graph(): LangGraph nodes/edges/tools/state, FC23 interrupts
│   ├── memory.py              # ConversationBufferMemory wiring (FC6, FC27–28 follow-ups)
│   └── prompts/               # prompt templates (classification, summarization, clarification)
├── session/
│   └── conversation.py        # ConversationSession + context_state (§3; FC27 multi-turn state)
├── tools/                     # LangChain tools — thin bridges to core, never constraint logic
│   ├── schedule_tools.py      # exact/SQLite-backed (FC8, FC33)
│   ├── search_tools.py        # semantic/Chroma-backed (FC9)
│   └── plan_tools.py          # DegreePlanGenerator/Validator wrappers (FC22–24)
│                              # plan-affecting tools enforce confirm-before-acting (FC23, FC27–28)
└── server/                    # HTTP transport (proposed: FC-new-rest-api)
    ├── app.py                 # FastAPI app factory + lifespan; mounts routers, error handlers
    ├── dependencies.py        # DI providers: advisor agent, db managers, pre-auth student (FC36)
    ├── routers/               # thin per-resource APIRouters (<resource>.py, no business logic)
    ├── controllers/           # orchestrate services → map errors → build response models
    ├── services/              # business logic wrapping agent/database/core
    └── schemas/               # Pydantic request/response models (no internal entities leaked)
```

Dependency rule: `agent → database → core`; nothing below imports `agent`.
`server/` here instead of a separate package because it is a thin adapter over `AIAdvisorAgent`.

Code-level conventions live in skills (source of truth if this tree and they disagree): server routers/controllers/services split + `Depends` DI + Pydantic contracts → `.pi/skills/fastapi/SKILL.md`; graph nodes/edges/tools/state + FC23 interrupt confirmation → `.pi/skills/langgraph/SKILL.md`.

### `src/frontend/` — React UI

```
frontend/
├── package.json               # own toolchain; not part of Python packaging
├── index.html
├── public/
└── src/
    ├── main.jsx               # AdvisorUI entry (§5)
    ├── api/
    │   └── client.js          # single wrapper over the HTTP API
    ├── state/
    │   └── SessionContext.jsx # built-in React state only (no Redux/Zustand)
    ├── components/            # one folder per component — anatomy: <Name>.jsx + <Name>.css + <Name>.stories.jsx
    │   ├── chat/              # render_chat_interface (FC22–24, FC27–28); e.g. components/chat/ChatMessage/
    │   ├── planner/           # degree plan display/compare (FC1–FC7, FC25–FC26)
    │   ├── degrees/           # degree exploration/audit (FC15–FC19)
    │   ├── classes/           # add/drop/confirm dialogs (FC20–FC21, FC23)
    │   └── shared/            # cross-domain primitives (no code may import shared from above)
    └── pages/
        ├── Dashboard.jsx
        └── DegreeExplorer.jsx
```

Component anatomy (per-component folder: component `.jsx`, plain `.css`, mandatory Storybook CSF3 `.stories.jsx`), atomic decomposition into those domain groups, plain-CSS naming, and built-in state-management rules are specified in `.pi/skills/react-component/SKILL.md` — that skill is the source of truth for the frontend if this tree and it disagree.

## Dependency map & import rules

```
frontend ──HTTP──▶ agent/server ──▶ agent(llm,tools) ──▶ database ──▶ core
                                   tools ──▶ core       (managers ──▶ core)
```

- `core` → stdlib only (the whole point: validators runnable offline, FC29–32 provable in unit tests).
- `database` → `core` + LangChain-core abstractions; no agent imports.
- `agent` → `database`, `core`; never reexports internals through routes.
- `frontend` → its own HTTP client only; no shared types generated in v1 (open question 3 below).

## Data & source impact (no changes made yet)

- **Created:** everything under `src/core`, `src/database`, `src/agent`, `src/frontend` per the trees above; tests mirroring each Python zone (`tests/core`, `tests/database`, `tests/agent`).
- **Moved:** `src/main/AI_Assistant.py` content split across `agent/llm/advisor_agent.py` + `agent/server/app.py` (old file becomes a deprecation shim or is deleted).
- **Deleted (in implementation):** `src/main/AI_Assistant 5.java` — early-design leftover, explicitly ignored by AGENTS.md.
- **Read-only consumers:** `data/course-desc.jsonl` → `database/ingest/course_desc_loader.py`; `data/cse_undergrad_courses.pdf` → `database/ingest/degree_pdf_ingest.py`. `data/` itself is not modified.

## Risks, open questions, out-of-scope

- **Not auto-enforced:** skill-based scoping has no tool-level guard; import rules are per-convention. A CI import-linter (e.g. `import-linter` contract `core` ← `database` ← `agent`) would make them real — recommended but is its own scope item.
- **Open questions carried from scoping:**
  1. FastAPI chosen as server default here — confirm; swapping to another framework changes only `agent/server/`.
  2. One Python package with subpackages (proposed) vs. per-component `pyproject.toml`. The proposed single package is simpler for a course-project install; split later if a standalone pippable `core` is ever needed.
  3. Frontend↔backend type sharing (hand-written DTOs vs. OpenAPI codegen) — deferred.
  4. `ConversationSession` lives in `agent/session` (§3), but its history is persisted via `SQLDatabaseManager` (FC34). Confirm that session persistence is agent-owned rather than database-owned.
- **Out of scope:** authentication (FC36); any runtime feature work — moving code and creating packages only; changing `data/` formats (FC35 corpus stays as is).

## Implementation outline

1. Create `src/core/` (entities, engine, results, errors); move nothing yet.
2. Lift `CourseRecommendationValidator` / `DegreePlanGenerator` logic out of `AI_Assistant.py` (if any exists) into `core/engine/` as pure functions/classes; unit-test against entities alone — the deterministic guarantee comes first.
3. Create `src/database/` with the ABC, SQLite schema + manager (FC34), then `vector`/`ingest` (FC9, FC33); wire seed loaders against `data/` reads.
4. Create `src/agent/` — port `AIAdvisorAgent` + intent routing (FC22–24); register tools wrapping `core` and `database`; add `server/` FastAPI app exposing them.
5. Scaffold `src/frontend/` React app (§5, FC1–FC21 UI surface) pointing at the local API.
6. Remove the leftover `.java` file; mark `src/main/` deprecated and remove after the server entry is wired; add the import-linter contract as follow-up.