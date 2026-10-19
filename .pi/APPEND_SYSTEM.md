# Project append: Academic AI Advisor

You are working in the Academic AI Advisor project — a RAG-based advising platform (React frontend, Python/LangChain agent, SQLite + Chroma). `AGENTS.md` at the repo root has the repo map and stack details.

## Behavioral rules for this repo

1. **Deterministic engine first.** LLMs are not constraint solvers here. Every recommendation, audit, or plan answer must be produced or verified through deterministic code paths — `CourseRecommendationValidator` for safeguards (FC29–FC32) and `DegreePlanGenerator` for plans (FC2, FC25, FC26). The LLM classifies intent, calls tools, and summarizes.
2. **Never fabricate academic data.** Courses, sections, prerequisites, credit limits, and degree requirements exist only in SQLite and Chroma. If a tool lookup fails or comes back empty, say so — do not invent plausible courses or sections.
3. **Cite FC IDs.** When discussing requirements, implementing, or reviewing, reference the relevant FC numbers from `docs/functional-requirements.md`.
4. **Confirm before acting.** Any assistant action on the user's behalf (adding classes, changing class status, changing major/concentration/degree — FC23) must be explicitly confirmed by the user before the deterministic side executes it. Multi-turn clarification applies to plan/major changes (FC27, FC28).
5. **Route queries by data type.** Structured facts (schedules, enrollment status, credit counts) go to SQLite; semantic/natural-language questions about courses, degrees, and professor/course fit go to Chroma similarity search (FC9, FC33).
6. **Auth is out of scope** (FC36): assume a pre-authenticated student session; do not build authentication flows.
7. When modifying shared team config under `.pi/`, remind the user to commit so teammates pick it up via `git pull` + `/reload`.