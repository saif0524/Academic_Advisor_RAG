# Academic AI Advisor — repo guide

RAG-based academic advising platform: course search/discovery, degree exploration, personal degree plans, and a conversational advising assistant that can act on a student's behalf (with confirmation).

**Fidelity bar (2026-10-22, class assignment):** this is a POC — prefer *working* over *robust*. Ship the deterministic engine, grounded data paths, and confirmation gates correctly; skip pro-grade hardening (edge-case audits, pagination, caching, exhaustive error taxonomies) unless tests or grounding rules require it.

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
- `data/course-desc.jsonl` — seed RAG corpus: 75 lines, one JSON object per line `{"id", "title", "description"}` (4-digit CSE course ids).
- `data/cse_undergrad_courses.pdf` — CSE undergraduate degree requirements (source of the catalog).
- `data/CS-requirements-BCS.md`, `data/SE-requirements-BSE.md` — structured degree-requirement records (YAML frontmatter + tables; seed source for the `degrees` tables).
- `data/AICertification.md`, `data/general-course.md` — catalog text ingested to Chroma (not selectable degrees).
- `data/sections-mock.json`, `data/student-demo.json` — **labeled MOCK demo seeds** (mock schedules + the one demo student profile; NOT real registrar/person data) loaded by the seed pipeline.
- `src/core/` — §1/§2 pure entities (dataclasses in `core/entities/`; zero LLM/db imports) + the full §2 deterministic engine (`engine/validator.py` — `CourseRecommendationValidator` FC29–FC32; `engine/progress.py` — FC19/FC24 counting; `engine/generator.py` — `DegreePlanGenerator` FC2/FC25/FC26 + draft review + plan comparison; `engine/results.py`).
- `src/database/` — persistence zone (§4, FC33/FC34): `base.py` ABC; `sql/sqlite_manager.py` + `migrations/` (v1 schema, v2 `student_preferences`) + repositories; `vector/chroma_manager.py` + `vector/embeddings.py` (pluggable: ONNX MiniLM default, `ADVISOR_EMBEDDING_FUNCTION=hash` for offline tests); `ingest/` loaders; `seed.py` — reloads seed-owned tables from `data/` on every server startup (default `ADVISOR_SEED_MODE=reload`; user-owned chat/plan/preference tables persist) into `var/` (gitignored; `ADVISOR_SQLITE_PATH`/`ADVISOR_CHROMA_PATH` override). Canonical course ids: 4-digit corpus ids for catalog-backed CSE courses (`"1105"`), full codes otherwise (`"ENGL 1301"`).
- `src/agent/` — agent zone (§3, **built**): LangGraph advisor graph in `llm/graph.py` (classify → conditional routing → tool nodes → summarize; FC23 durable pause/resume via `chat_pending_actions` + decision ids; FC27/28 clarification bounded to one question per turn; `plan_generation` intent routes plan-building requests through `DegreePlanGenerator`), `llm/advisor_agent.py` (`AIAdvisorAgent.process_query`), `llm/config.py` (LLM seam: `ADVISOR_LLM_PROVIDER=ollama` default `glm-5.3-flash:cloud` | `stub` deterministic), `llm/{classify,summarize,prompts}.py` (LLM paths degrade to the grounded stubs on model failure), `tools/` (`AdvisorToolkit`: schedule → SQLite FC8/FC33, search → Chroma FC9, plan → validator/audits FC24 + plan generation FC2/FC25 + FC23 proposals/executions), `session/conversation.py` (`ConversationSession`). Chat send (FC22) and audits (FC24) answer through it.
- `src/server/` — FastAPI HTTP transport (**FC37**, formalized from the proposed `FC-new-rest-api`): app factory + lifespan (wires managers + agent + seeding; `ADVISOR_SEED_MODE`, `ADVISOR_LLM_*` env), all DI in `dependencies.py`, routers/controllers/services/schemas per resource (chat, courses, classes, plans, degrees, students, audits). Wired now: all data-backed endpoints (courses FC8–12, classes FC13/14/20/21, students FC1/7/16/17/19 + planning preferences FC25/FC32, degrees FC15/18, chat history FC34, chat send FC22–24/27–28 via the agent, audits FC24 via the validator, and all plan writes: generate FC2/FC25, update FC3, versions FC4, revert FC5, activate FC6, compare FC26, draft review FC29–FC32 — all engine-backed via `DegreePlanGenerator`). Conventions: `.pi/skills/fastapi/SKILL.md`.
- `src/frontend/` — React app (TypeScript: components `.tsx` + plain CSS + required Storybook story; `npm run typecheck` = `tsc --noEmit`). One folder per component; domain groups `components/{chat,planner,degrees,classes,search,shared}` + `pages/` composition roots + `api/client.ts` (single HTTP wrapper) + `state/SessionContext.tsx` (built-in state only). Live api seams: chat, search, plans/students/catalog/candidates (plan flow: generate → edit in timeline → make active). Stories keep injected DI fixtures and never hit the real api. Conventions: `.pi/skills/react-component/SKILL.md`; structure: `docs/planning/2026-10-19-src-monorepo-structure.md`; UI wireframes: `docs/wireframes/`.
- `src/main/` — backend entry (legacy `AI_Assistant_New.py`; the `.java` file is an early-design leftover).
- `tests/` — Python unit tests mirroring the src zones (`tests/database/`, `tests/server/`, `tests/core/` when the engine lands) mirroring the tester skill scope.

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