e# Academic AI Advisor — repo guide

RAG-based academic advising platform: course search/discovery, degree exploration, personal degree plans, and a conversational advising assistant that can act on a student's behalf (with confirmation).

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | React (built-in state management only) |
| Agent / LLM | Python + LangChain (`src/main/AI_Assistant.py`) |
| Structured data | SQLite — students, sections, enrollments, plans, chat history |
| Unstructured data | Chroma — course descriptions, catalog text, degree requirements (embeddings) |

## Repo map

- `docs/functional-requirements.md` — FC1–FC36. Single source of truth for scope. Sections: 1 Degree Plans (FC1–7, 25–26), 2 Course Discovery (FC8–14), 3 Degree Requirements (FC15–19), 4 Class Management (FC20–21), 5 Assistant Engine (FC22–24, 27–28), 6 Recommendation Safeguards (FC29–32), 7 Data & Assumptions (FC33–36).
- `docs/ai_advisor_domain_model.md` — class specs: domain entities (§1), planning/validation engine (§2), LangChain conversation layer (§3), DB managers (§4), UI (§5).
- `data/course-desc.jsonl` — seed RAG corpus: 75 lines, one JSON object per line `{"id", "title", "description"}` (4-digit course IDs).
- `data/cse_undergrad_courses.pdf` — CSE undergraduate degree requirements; source for degree requirement records.
- `src/main/` — backend entry (`AI_Assistant.py`; the `.java` file is an early-design leftover).

## Core architecture rules

1. **Deterministic engine first** (`docs/ai_advisor_domain_model.md` §2): constraint checks (prereqs, repeat-pass, time conflicts, credit caps — FC29–32) and plan generation run as plain code through `CourseRecommendationValidator` and `DegreePlanGenerator`. The LLM interprets and summarizes; it never does constraint math and never generates plans itself.
2. **Route by data type:** structured lookups → SQLite; semantic/natural-language search over course and degree text → Chroma (FC9, FC33).
3. **Grounded answers only:** the assistant never invents courses, sections, or requirements.
4. **Confirm before acting:** assistant actions on the user's behalf (FC23) require explicit user confirmation.
5. **Auth out of scope** (FC36): baseline assumes pre-authenticated student sessions.

## Workflow in this repo

- Trace every feature to its FC ID(s) before implementing.
- `/fc <ids>` — pull up requirements (e.g. `/fc 29 30 31`).
- `/plan-feature <description>` — draft a design mapped to the domain model.
- `/skill:advisor-domain` — load domain knowledge, safeguard ownership, and data-format details.