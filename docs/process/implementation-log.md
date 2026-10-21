# Implementation log

Reverse-chronological entries for each implementation pass (what landed, which FCs, notable decisions).

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