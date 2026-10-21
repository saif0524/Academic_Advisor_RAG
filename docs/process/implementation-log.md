# Implementation log

Reverse-chronological entries for each implementation pass (what landed, which FCs, notable decisions).

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