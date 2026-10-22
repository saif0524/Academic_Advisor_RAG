# Implementation log

Reverse-chronological entries for each implementation pass (what landed, which FCs, notable decisions).

---

## 2026-10-22 — DegreePlanGenerator + plan/account/dashboard end to end (FC2/FC3/FC4/FC5/FC6/FC25/FC26 + FC29–FC32 semantics, FC19, FC25/FC32 prefs, FC23 gate, FC33/FC37)

**Scope.** `/build` pass: built the missing §2 engine (plan generation,
comparison, draft review), wired all plan-write endpoints out of 501, added
the planning-preferences round-trip, and swapped the remaining frontend mock
seams (plans/students/catalog/candidates) to the live API. POC fidelity bar
agreed with the user: working > robust.

**Created**
- `src/core/engine/generator.py` — `DegreePlanGenerator`
  (`generate_multi_year_plan`, `review_plan_semesters`, `compare_plans`,
  `simulate_major_switch`, `semesters_payload`) + `PlanGenerationResult` /
  `PlanReviewResult` / `PlanComparisonResult`. Semester placement honors
  FC30 (skip completed), FC29 (prereq in a strictly earlier semester), FC32
  (per-semester cap / degree-total awareness), FC25 (roadmap from the
  current term, optional summer); elective buckets fill from the grounded
  catalog pool with dry-pool notes; unresolvable requirement rows are
  excluded with notes, never invented.
- `src/database/sql/migrations/0002_student_preferences.sql` (FC25/FC32
  inputs) + manager/repo methods; plans repo: `get_active_plan`,
  `activate_plan`, `update_plan_meta`, payload-aware save (new plans start
  INACTIVE — generate → edit → make active).
- Tests: `tests/core/test_plan_generator.py` (16),
  `tests/server/test_plan_endpoints.py` (19),
  `tests/agent/test_plan_generation.py` (4).

**Modified**
- `server/services/plans.py` — generate/update/revert/compare/active/
  activate/options/review wired through the engine (blocking FC30/FC32 →
  422 `validation_failed`; unknown major → 404). `server/services/students.py`
  — preferences + richer FC19 progress numbers (completed/in-progress/
  total hours). Schemas/controllers/routers extended accordingly
  (`PlanDetail.notes`, `PlanOptionsResponse`, `PlanReviewRequest/Response`,
  comparison hour fields; `GET/PUT /students/me/preferences`).
- `agent/llm/classify.py` + `prompts.py` — `plan_generation` intent (stub
  rule + LLM system line); `agent/llm/graph.py` — `plan_tools` node + route;
  `agent/tools/plan_tools.py` — `generate_plan` (engine + persistence,
  honest refusal for unresolved majors); `llm/summarize.py` — grounded
  plan-rendering template.
- Frontend: `api/{plans,students,courses}.ts` now live; `api/types.ts`
  extended; `Dashboard` reads `GET /plans/active` + FC19 progress;
  `PlanGenerator` generates previews (notes surfaced) with Make active /
  Open-in-timeline actions; `TimelinePage` gains plan switching (FC6),
  `Make active`, version history + revert (FC4/FC5), engine reviews via
  `POST /plans/review`, saving via engine-validated `PATCH`; `AccountPage`
  compares against the plan on file (FC26) and its confirmed change applies
  the major (FC1/FC7) + auto-generates an inactive plan; stories updated
  with a `reviewFn` DI seam (stories stay off the network).
- Updated stale tests that asserted 501 plan writes
  (`tests/server/test_smoke.py`, `tests/server/test_data_endpoints.py`) —
  expectation change per the agreed spec (plan writes are now wired), not
  test weakening.

**Decisions**
- Plan flow (product decision): generate → edit → make active; exactly one
  active plan per student; program-change confirm auto-generates an
  INACTIVE plan for the new degree.
- Concentrations aren't structured in the degrees seed → plan options list
  'General' per major; requested concentration strings persist as-is.
- Review severities: FC30/FC32 blocking (reject save), FC29 ordering
  warnings (forward-plans advisory; prereq data is empty in the seed).
- Credits missing in the corpus (e.g. '2312') are placed with an honest
  'FC32 unverifiable' note instead of blocking placement.
- Chat plan requests create persisted plans directly (not FC23 actions —
  plans are derived artifacts, not profile changes).

**Verified** `pytest`: 237 passed. Frontend typecheck + lint + build clean;
boots live and walked the full chain (generate → activate → preferences →
edit/version → revert → compare → review → chat-generated plan).

**Follow-ups.** OpenAPI codegen for the frontend DTOs; richer concentration
modeling if the seed data ever structures them; Storybook review of the new
states.
---

## 2026-10-21 — SQLite + Chroma databases, fully wired into managers + API layer (FC33, FC34, FC9, FC8–FC12, FC13–FC21, FC1/FC7/FC15–FC19, new **FC37**)

**Scope.** `/build` pass: database zone + core entities + server DI/data-endpoint wiring, preparing end-to-end feature work. Not touched: agent zone (chat send), §2 engine (plan generate/update/revert/compare, audits) — all still 501 `not_wired` by design (FC37).

**Created**
- `src/core/entities/{__init__,student,course,degree}.py` — §1/§2 entities as dataclasses (Student/EnrollmentRecord, Course/CourseSection, DegreeRequirement(+blocks)/SemesterPlan/DegreePlan).
- `src/database/base.py` (§4 ABC), `src/database/errors.py` (`RecordNotFoundError`).
- `src/database/sql/migrations/0001_init.sql` (+ migration runner: students, major_history, courses, course_prerequisites, sections, student_classes, degrees, degree_requirement_blocks/courses, plans, plan_versions, chat_sessions, chat_messages, chat_pending_actions (FC23-ready)).
- `src/database/sql/repositories/{students,courses,degrees,plans,chat}.py` (thin query modules; `sqlite_manager.py` = §4 `SQLDatabaseManager`, connection-per-op, commit-on-success).
- `src/database/vector/embeddings.py` (pluggable: ONNX MiniLM default via `ADVISOR_EMBEDDING_FUNCTION`; deterministic `HashEmbeddings` for offline tests) + `vector/chroma_manager.py` (§4 `VectorDatabaseManager`; collections `courses` + `catalog`).
- `src/database/ingest/{course_desc_loader,degree_requirements_loader,catalog_text_loader,demo_seed_loader}.py` and `seed.py` (full reload on startup: seed-owned tables refreshed from `data/`; chat/plan user state persists — FC34).
- Tests: `tests/database/{test_ingest_loaders,test_vector_manager,test_sql_manager,test_seed}.py`, `tests/server/{test_course_service_routing,test_data_endpoints}.py` (all FC-mapped).

**Modified**
- `src/server/dependencies.py` — real `initialize_state()`/`shutdown_state()` (managers + seeding + env config: `ADVISOR_SQLITE_PATH`, `ADVISOR_CHROMA_PATH`, `ADVISOR_DATA_DIR`, `ADVISOR_SEED_MODE=reload|off`, `ADVISOR_EMBEDDING_FUNCTION=onnx|hash`); `advisor_agent` stays None.
- `src/server/errors.py` — `RecordNotFoundError` → 404 `not_found`; `InvalidRequestError` → 422 `validation_failed` (FC16 alignment).
- `src/server/services/{courses,classes,students,degrees,chat,plans,audit}.py` — data-backed methods implemented; engine/LLM-dependent methods keep `NotWiredError` (501).
- `requirements.txt` (+chromadb, +PyYAML, +numpy); `.gitignore` (+`var/`, `*.db*`).
- `tests/server/test_smoke.py` — expectations updated to the wired surface (501 only where zones are genuinely missing).

**Data (new labeled mock seeds)** `data/sections-mock.json` (Fall 2026 schedules incl. a full section + a deliberate time overlap for FC31 demos), `data/student-demo.json` (one demo student matching the FC36 default identity, FC21 statuses + grades, no prior major switches).

**Grounded-data decisions**
- Course identity: 4-digit corpus id for catalog-backed CSE courses; full code otherwise — CSE 2320/CSE 2381 exist only in requirement docs (corpus-missing) → id `"CSE 2320"`; other depts always full code (`"ENGL 1301"` — avoids CSE 1301 collisions).
- Credit hours backfilled only from requirement tables; prerequisites stay empty (no source data); sections exist only from the labeled mock seed; offered_terms derived from seeded sections.
- Certificates are Chroma catalog text only, not selectable degrees (FC16 applies to degrees).

**Status codes / mapping** 501 `not_wired` (chat send, plan gen/update/revert/compare, audits) · 404 `not_found` misses · 422 `validation_failed` FC16 misalignment · 201 POST /classes (shipped router contract).

**Verified** `pytest`: 92 passed. Manual `uvicorn` run: /health, profile, exact + semantic search, class lifecycle, degrees, FC19 progress, misalignment 422, chat history, chat-send 501.

**Follow-ups (next /build passes).**
1. Core §2 engine (`CourseRecommendationValidator` FC29–FC32 → unblocks audits FC24) + `DegreePlanGenerator` (FC2/FC25/FC26 → unblocks plan writes).
2. Agent zone (`AIAdvisorAgent` + LangGraph; FC22–24, FC27–28; consumes chat_pending_actions + FC23 confirmation).
3. OpenAPI codegen for the frontend mocks swap.
---

## 2026-10-20 — LangGraph agent + core validator + wired chat/audits (FC22–FC24, FC27–FC28, FC29–FC32, FC33/FC34/FC37)

**Scope.** `/build` pass: the §3 conversation layer end-to-end, including the
FC29–FC32 deterministic validation the agent depends on, and the
search-page/chat-drawer switch to the live API.

**Created**
- `src/core/engine/` — `validator.py` (`CourseRecommendationValidator`, FC29/FC30/FC31/FC32 + §2-4c informational), `progress.py` (`compute_degree_progress`, FC19/FC24), `results.py` (`ConstraintCheck`/`ValidationResult`). Pure, offline, entity-passed.
- `src/agent/` — `llm/graph.py` (LangGraph `AdvisorState`; entry gate → classify → conditional route → exact/semantic/recommend/audit/propose-tool nodes → summarize; no checkpointer — SQLite IS the durable state), `llm/advisor_agent.py` (`AIAdvisorAgent.process_query`), `llm/config.py` (LLM seam provider pattern like embeddings: `ADVISOR_LLM_PROVIDER=ollama` default `glm-5.3-flash:cloud`, `stub` deterministic), `llm/{classify,summarize,prompts}.py` (LLM paths degrade to the grounded stubs, never fabricate), `session/conversation.py` (§3 `ConversationSession`), `tools/` (`AdvisorToolkit`; `course_ids` normalizer), `errors.py`.
- Tests: `tests/core/test_validator.py` + `test_progress_math.py` (pure); `tests/agent/{conftest,test_graph_routing,test_pending_actions,test_llm_seams}.py` (stubbed LLM; FC23 gate/ownership/cancel; FC24/27/28; FC33 routing); `tests/server/test_chat_endpoints.py` + `test_audits.py`.
- Frontend live: `api/chat.ts` (real chat seams), `api/liveSearch.ts` (search page: FC22 answer + FC9 results + FC24 verdict badges), `ChatPanel`/`CourseSearch` defaulting to live (`stories` keep injected fixtures via the DI seams), `client.ts` typed `ApiError` from the error envelope.

**Modified**
- `src/server/dependencies.py` (builds `AIAdvisorAgent` in lifespan; `ADVISOR_LLM_PROVIDER/MODEL/BASE_URL`), `server/services/chat.py` (real send: session verify, FC23 decision-prevalidation, FC34 persistence of both turns), `server/schemas/chat.py` (+`cancelled_action_id`, `ChatSessionsResponse`), `server/routers/chat.py` (+`GET /chat/sessions`), `server/errors.py` (LLMError → 503 `llm_unavailable`), `server/services/audit.py` (wired via validator), `server/services/students.py` (delegates FC19 math to core), `database/sql/repositories/chat.py` (+`session_exists`, `list_chat_sessions`, student_id in pending-action rows), `data/sections-mock.json` (the intended FC31 overlap demo was factually wrong — days differed; 1311-001 now genuinely overlaps the demo student's in-progress 1325-501), `requirements.txt` (+langgraph/langchain-core/langchain-ollama), `tests/server/{test_smoke,test_data_endpoints}.py` (wired expectations).

**Decisions**
- FC23 as a durable pause/resume in SQLite (restart-safe) instead of in-process `interrupt()`; cancel is an explicit `cancelled_action_id` field.
- LLM classification/summarization degrade to the deterministic stubs on failure — availability with grounded data (503 only if even the degraded path is unreachable).
- Recommendation answers only ever show validator-filtered candidates (FC29–FC32); unknown data renders as `unknown`, never a guess.
- Plan generation/comparison stays `DegreePlanGenerator` (not built — next `/build`).

**Verified** `pytest`: 198 passed (was 92). Live `uvicorn` + real `glm-5.3-flash:cloud`: grounded course Q&A, FC23 propose→confirm→SQLite write, FC24 audits, GET /chat/sessions. Frontend `npm run typecheck` + build + lint clean.

**Follow-ups (next `/build` passes).**
1. `DegreePlanGenerator` (FC2/FC25/FC26) → unblocks plan writes (then the agent's plan tools can generate).
2. Remaining pages' mock→live swap (plans/students/classes services).
3. OpenAPI codegen for the frontend DTOs.

## 2026-10-20 — Docker Compose deployment (FC38)

**Scope.** `/build` pass: containerize the stack so `docker compose up --build`
brings up api + web for testing (spec: new FC38 in FR section 7).

**Created**
- `Dockerfile` (api) — python:3.12-slim, `pip install -r requirements.txt`, `src/`+`data/`, `PYTHONPATH=src`, `ADVISOR_HOST=0.0.0.0`, healthcheck on `/health`, ENTRYPOINT `python -m server.app` (ServerSettings stays the host/port source).
- `src/frontend/Dockerfile` — node:22-alpine build (`npm ci`, `vite build`, `ARG VITE_API_BASE_URL` baked) → nginx:1.27-alpine static serve; `src/frontend/nginx.conf` (SPA fallback); `src/frontend/.dockerignore`.
- `.dockerignore` (root) — secrets/models.json/var/db/dist excluded from the build context (FC36).
- `docker-compose.yml` — `api` (8000, `advisor-var` + `advisor-model-cache` volumes, LLM env `ADVISOR_LLM_BASE_URL=http://host.docker.internal:11434` default, `OLLAMA_API_KEY` from `.env`, `extra_hosts host-gateway` for Linux) + `web` (3000→80, `VITE_API_BASE_URL` build arg default `http://localhost:8000`).

**Modified**
- `requirements.txt` (+`onnxruntime` — the default `ADVISOR_EMBEDDING_FUNCTION=onnx` imports it; a fresh image otherwise silently degrades to hash embeddings), `.env.example` (documented compose vars), `README.md` (§5 Run the whole stack with Docker + repo-structure bullet), `AGENTS.md` (repo map), FR doc (FC38 added).

**Decisions**
- Ollama stays external: the api container points at the host's Ollama (`host.docker.internal:11434`) so the demo reuses the local `glm-5.3-flash:cloud` + `OLLAMA_API_KEY`; optional `ADVISOR_LLM_PROVIDER=stub` for fully offline.
- `ADVISOR_SEED_MODE=reload` unchanged (FC33): seed tables reload each `up`; user-owned chat/plan data persists in the `advisor-var` volume (FC34).
- No unit tests: infra carries no business logic (tester scope) — user-acknowledged; verification = pytest regression + smoke bring-up.

**Verified** `pytest`: 237 passed (unchanged by this pass). Compose YAML structure-checked; container run mode (`python -m server.app` with `ADVISOR_HOST/PORT`) smoke-proven locally: seeds, serves `/health` → 200 ok. Docker wasn't available in the build shell — first real `docker compose up --build` happens on the user's machine.

**Follow-ups.** None required; revisit only if the frontend gains runtime env needs or the api gains new ports.

## 2026-10-22 — Agent access to the active degree plan (FC22/FC24/FC27, FC3 via FC23)

**Scope.** `/build` pass: the assistant had no plan context (`AdvisorToolkit.active_plan` was never called, and returned the *newest* plan rather than the active one).

**Modified**
- `src/agent/tools/schedule_tools.py` — `active_plan` now `sql.get_active_plan` (FC6); new `plan_context` (full semester roadmap, titles, credit totals, progress; `None` when no plan is active). `tools/__init__.py` exposes it.
- `src/agent/llm/graph.py` — `exact` node returns `plan` for `params.topic == "plan"`; progress audits carry `plan`; recommendations exclude planned courses (`already_planned` reported); classifier gets `{student_id, major, has_active_plan}`.
- `src/agent/tools/plan_tools.py` — FC23 actions `plan_add_course`, `plan_remove_course`, `plan_move_course`, `activate_plan`: prechecked by `DegreePlanGenerator.review_plan_semesters` (only NEW blocking FC30/FC32 verdicts refuse), executed on confirm as a new plan version (FC4).
- `classify.py`/`prompts.py`/`summarize.py` — routing rules, prompt contract, plan rendering ("no active plan" is stated plainly).
- Docs: FR FC22/FC23 notes, `AGENTS.md`, domain model §3 note.

**Tests.** `tests/agent/test_plan_context.py`, `tests/agent/test_plan_edits.py`; full suite 254 passed.

**Decisions.** Plans stay in SQLite (not Chroma). The demo seed has no plan (plans are user-owned and persist across reseeds) — generate one in chat, then "make my plan active".
