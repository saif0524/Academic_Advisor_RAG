---
name: advisor-domain
description: Domain knowledge for building the Academic AI Advisor RAG platform — FC1–FC36 functional requirements, the deterministic planning/audit engine rules, LangChain agent + Chroma/SQLite data split, and seed-data formats. Use when implementing or reviewing any feature in this repo, including degree plans, course search/recommendation, audits, or agent tool design. For pre-implementation feature scoping and proposals, the architect skill is used instead.
---

# Academic AI Advisor — engineering knowledge

Full documentation lives in `docs/planning/2026-10-18-functional-requirements.md` (FC1–FC36) and `docs/planning/2026-10-18-ai-advisor-domain-model.md` (class specs). This skill carries the rules and details that are easy to get wrong.

## The one non-negotiable rule

LLMs are not constraint solvers in this system. Advising decisions go through deterministic code, and the model never bypasses it:

| Safeguard | FC | Deterministic owner |
| --- | --- | --- |
| Verify prerequisites before recommending any course | FC29 | `CourseRecommendationValidator.check_prerequisites_met` |
| Never recommend already-passed courses | FC30 | `check_not_already_passed` |
| Detect/prevent section time conflicts | FC31 | `check_no_schedule_conflict` / `SemesterPlan.has_schedule_conflicts` |
| Enforce per-semester and degree-total credit caps | FC32 | `check_within_semester_credit_limit`, `check_within_total_degree_credits` |

The `AIAdvisorAgent` classify → tool-call → summarize loop is in `docs/planning/2026-10-18-ai-advisor-domain-model.md` §3 (`classify_query_intent`, `handle_exact_query`, `handle_semantic_query`, `handle_plan_generation_request`). Plans come from `DegreePlanGenerator.generate_multi_year_plan` and `compare_plans` (FC25, FC26), never from the model's imagination. LangGraph implementation conventions for that loop (nodes/edges/tools, FC23 interrupts): `.pi/skills/langgraph/SKILL.md`.

## Data routing (FC33)

- **SQLite** (via `SQLDatabaseManager`): student records, course sections, enrollment history, degree plans, chat/advising history (FC34).
- **Chroma** (via `VectorDatabaseManager`): course-description embeddings, catalog/PDF text, degree requirements. Semantic or natural-language course search (FC9) hits Chroma; anything with an exact ID or count hits SQL. `handle_exact_query` vs `handle_semantic_query` encodes this split.

## Seed data

- `data/course-desc.json` — JSON array of 75 objects: `{"id", "title", "description"}`. IDs are 4-digit numbers (e.g. `1105` = Intro to CS&E). This is the initial Chroma ingest corpus; `Course.to_document_chunk()` defines the chunk format.
- `data/cse_undergrad_courses.pdf` — CSE undergraduate degree requirements. Parse into `DegreeRequirement` records (core, concentration courses, elective rules, credit totals).

## Stack decisions

- React frontend, built-in state management only (no Redux/Zustand/etc.). Component anatomy (per-component folder with `.jsx` + plain `.css` + required Storybook story), atomic decomposition, and state rules live in `.pi/skills/react-component/SKILL.md`.
- Python + LangChain/LangGraph backend; entry point is the FastAPI app `src/server/app.py`. FastAPI HTTP conventions (routers/services, DI, Pydantic): `.pi/skills/fastapi/SKILL.md`. Testing scope (business logic only, no UI tests): `.pi/skills/tester/SKILL.md`.
- Embeddings/ingest flow through `VectorDatabaseManager.ingest_documents`; assume pluggable embedding model choice.

## Baseline assumptions

- Pre-authenticated student sessions; login/logout/security is out of scope (FC36).
- One major + one specialization per student (FC1); one selected degree at a time (FC17).
- Multiple degree plans per major/spec combo are allowed (FC6), with version history and revert (FC4, FC5).