# Academic AI Advisor — repo guide

RAG-based academic advising platform: course search/discovery, degree exploration, personal degree plans, and a conversational advising assistant that can act on a student's behalf (with confirmation).

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | React (built-in state management only) |
| Agent / LLM | Python + LangChain (`src/agent/`; FastAPI HTTP layer in `src/server/`; legacy CLI entry `src/main/AI_Assistant_New.py`) |
| Structured data | SQLite — students, sections, enrollments, plans, chat history |
| Unstructured data | Chroma — course descriptions, catalog text, degree requirements (embeddings) |

## Repo map

- `docs/planning/2026-10-18-functional-requirements.md` — FC1–FC36. Single source of truth for scope. Sections: 1 Degree Plans (FC1–7, 25–26), 2 Course Discovery (FC8–14), 3 Degree Requirements (FC15–19), 4 Class Management (FC20–21), 5 Assistant Engine (FC22–24, 27–28), 6 Recommendation Safeguards (FC29–32), 7 Data & Assumptions (FC33–36).
- `docs/planning/2026-10-18-ai-advisor-domain-model.md` — class specs: domain entities (§1), planning/validation engine (§2), LangChain conversation layer (§3), DB managers (§4), UI (§5).
- `docs/` — organized as `planning/` (requirements, domain model, dated proposals — new proposals go here), `process/` (git process, implementation log), `wireframes/` (UI wireframes for the frontend screens), `example-chats/` (exported example advising sessions; reference material, not requirements).
- `data/course-desc.jsonl` — seed RAG corpus: 75 lines, one JSON object per line `{"id", "title", "description"}` (4-digit course IDs).
- `data/cse_undergrad_courses.pdf` — CSE undergraduate degree requirements; source for degree requirement records.
- `src/agent/` — agent zone: LangChain conversation layer (`agent/llm`, `agent/session`, `agent/tools`) per `docs/planning/2026-10-19-src-monorepo-structure.md` §agent.
- `src/server/` — FastAPI HTTP transport (proposed `FC-new-rest-api`): app factory + lifespan, all DI in `dependencies.py`, routers/controllers/services/schemas per resource (chat, courses, classes, plans, degrees, students, audits). Thin adapter over agent/database/core; unwired endpoints return 501 `not_wired` until those zones are built. Conventions: `.pi/skills/fastapi/SKILL.md`.
- `src/main/` — backend entry (`AI_Assistant_New.py`; the `.java` file is an early-design leftover).
- `tests/` — Python unit tests mirroring the src zones (smoke tests in `tests/server/` today).
- `src/frontend/` — React app (TypeScript: components `.tsx` + plain CSS + required Storybook story; `npm run typecheck` = `tsc --noEmit`). One folder per component; domain groups `components/{chat,planner,degrees,classes,search,shared}` + `pages/` composition roots + `api/client.ts` (single HTTP wrapper) + `state/SessionContext.tsx` (built-in state only). Conventions: `.pi/skills/react-component/SKILL.md`; structure: `docs/planning/2026-10-19-src-monorepo-structure.md`; UI wireframes: `docs/wireframes/`.

## Core architecture rules

1. **Deterministic engine first** (`docs/planning/2026-10-18-ai-advisor-domain-model.md` §2): constraint checks (prereqs, repeat-pass, time conflicts, credit caps — FC29–32) and plan generation run as plain code through `CourseRecommendationValidator` and `DegreePlanGenerator`. The LLM interprets and summarizes; it never does constraint math and never generates plans itself.
2. **Route by data type:** structured lookups → SQLite; semantic/natural-language search over course and degree text → Chroma (FC9, FC33).
3. **Grounded answers only:** the assistant never invents courses, sections, or requirements.
4. **Confirm before acting:** assistant actions on the user's behalf (FC23) require explicit user confirmation.
5. **Auth out of scope** (FC36): baseline assumes pre-authenticated student sessions.

## Workflow in this repo

- Trace every feature to its FC ID(s) before implementing.
- `/fc <ids>` — pull up requirements (e.g. `/fc 29 30 31`).
- `/plan-feature <description>` — draft a design mapped to the domain model.
- `/build <feature description>` or `/skill:build <feature description>` — end-to-end build: resolve or add the FC spec in `docs/planning/2026-10-18-functional-requirements.md`, plan with clarifying questions, write unit tests first, then implement until all tests pass (`.pi/skills/build/SKILL.md`; thin `/build` alias in `.pi/prompts/build.md`).
- `/skill:advisor-domain` — load domain knowledge, safeguard ownership, and data-format details.
- `/skill:architect <feature>` — scope a feature in a design chat; explicitly ask to "write the proposal" to generate `docs/planning/<date>-<slug>.md`.
- `/skill:react-component` — React component conventions for `src/frontend/` (one folder per component: `.jsx` + plain `.css` + required Storybook story; atomic decomposition by domain group; built-in state management only).
- `/skill:fastapi` — HTTP layer conventions for `src/server/` (routers/controllers/services split, `Depends` DI for services, Pydantic request/response schemas).
- `/skill:langgraph` — advisor-graph conventions for `src/agent/` (nodes, edges, conditional routing, tools, state, FC23 interrupt-based confirmation, checkpointing).
- `/skill:tester` — testing scope: business logic only (engine, services, agent orchestration with stubbed LLMs, db managers); no UI unit tests — Storybook review instead.
- **Docs stay current:** an implementation task is not done until affected docs are re-assessed for accuracy. After every change, check the docs it touches — the FC requirements doc, the domain model, this file's repo map, and any dated feature proposals — and update anything the change made stale (including this file itself).