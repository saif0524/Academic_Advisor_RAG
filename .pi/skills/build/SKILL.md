---
name: build
description: End-to-end feature build workflow (/build) for the Academic AI Advisor — resolve or create the FC spec, plan with clarifying questions, write unit tests first, then implement and iterate until every test passes. Use when the user invokes /build or explicitly asks to build a feature from spec to passing tests.
---

# /build — spec → plan → tests → implement

Run this workflow in-session, phase by phase, with the user in the loop. Everything is done by you in this conversation — no subagents. Never skip a phase; never begin the next phase while a question to the user is still open.

Ground rules (every phase):

- **Deterministic engine first.** Constraint checks (FC29–FC32) and plan generation (FC2, FC25, FC26) live in plain code — `CourseRecommendationValidator`, `DegreePlanGenerator` (`docs/2026-10-18-ai-advisor-domain-model.md` §2). The LLM classifies intent, calls tools, and summarizes; it never does constraint math and never generates plans.
- **Never fabricate academic data.** Courses, sections, prerequisites, credit limits, and degree requirements exist only in SQLite and Chroma. Empty lookup → say so.
- **Cite FC IDs** in all phase output and in code comments where a requirement is implemented.
- **Confirm before acting.** If the feature lets the assistant act on the student's behalf (FC23), its design and its tests must include the explicit-confirmation step.
- **No git commits** unless the user asks.

## Phase 0 — Orientation

Read before deciding anything: `AGENTS.md`, `docs/2026-10-18-functional-requirements.md`, `docs/2026-10-18-ai-advisor-domain-model.md`, any dated `docs/<date>-<slug>.md` proposals relevant to the feature, `docs/implementation-log.md` if present, and the source files the feature will touch. Also discover the current test setup (pytest config, `package.json` scripts, or none). Load relevant skills — deliberately, not by feel:

- `advisor-domain` — whenever the feature touches advising behavior (courses, prereqs, plans, degrees, audits).
- `tester` — **always**; it defines what phase 3 must and must not test (business logic only).
- `react-component` — when the request mentions UI, components, pages, or styling, or when frontend work cannot yet be ruled out. Its conventions (component anatomy, CSS, Storybook) govern frontend files in phases 3–4; the frontend gets **no** unit tests (see `tester`).
- `fastapi` — when the feature adds/changes HTTP endpoints, `src/server/` files, DI, or request/response schemas.
- `langgraph` — when the feature adds/changes graph nodes, tools, edges, state, interrupts, or the checkpointer in `src/agent/`.

**Re-check at phase 2:** the file-level change list is authoritative — before finalizing affected plan sections, load every skill above whose zone the list touches (`src/frontend/` → `react-component`; `src/server/` → `fastapi`; graph changes → `langgraph`).

## Phase 1 — Resolve the spec (FC)

1. Search `docs/2026-10-18-functional-requirements.md` for requirement(s) already covering this feature — match by behavior and section, not just keywords.
2. **If covered:** use those FC(s) as the spec. Quote the governing FC text (and any FR-doc notes) as the start of your output.
3. **If not covered:** draft and append a new requirement to the FR document. Place it in the most fitting numbered section, with the next FC ID (highest existing + 1, currently FC37 onward), using the section's exact table format: `| **FCn** | Title | Additional Notes |` (`•` bullets separated by `<br>` in Notes). Keep it implementation-neutral, consistent in style with neighboring rows — and consistent with the ground rules (deterministic engine, data routing FC33, auth out of scope FC36).
4. State which path was taken and quote the final spec text.

## Phase 2 — Plan + clarifying questions (STOP for answers)

Draft a plan, mapped to `docs/2026-10-18-ai-advisor-domain-model.md`:

- Affected FC IDs (cite existing and any newly added — and check the user agrees with the new FC's wording).
- Component map per layer: React UI / LangChain agent / SQLite / Chroma / deterministic engine.
- Domain-model impact: new classes vs methods/attributes on existing ones (§1–§5).
- If the feature recommends or schedules courses: exactly which FC29–FC32 validator checks apply, and confirmation that the LLM path cannot bypass them.
- File-level change list (files to create/modify — e.g. `src/main/AI_Assistant.py` — and their roles).

Then **end the reply with clarifying questions** — ask whatever would most change the implementation: ambiguous behavior, scope, seed-data needs, UI depth — and, if no test setup exists, the test-runner choice (propose pytest under `tests/`, one new dependency-light setup, as the default). **Wait for the user's answers. Do not write any code until they respond.**

## Phase 3 — Unit tests first

Encode the agreed spec as executable tests before implementing, **scoped by the `tester` skill — business logic only** (engine, services, agent orchestration with stubbed LLMs, db managers; no React/UI tests):

- Use the runner chosen in phase 2 (default: pytest, with tests mirroring the `src/` zones — `tests/core/`, `tests/database/`, `tests/agent/`).
- Name or comment every test with the FC it verifies. Cover the deterministic paths exhaustively: each applicable validator check (FC29–FC32), plan generation invariants (FC25, FC26), the SQLite/Chroma routing split (FC33), and the FC23 confirmation gate where actions are taken on the student's behalf.
- If a plan for a UI-only feature yields no backend logic, state that no unit tests apply — UI verification is Storybook review — and get the user's acknowledgment before phase 4.
- Run the new tests and confirm they fail for the right reason (feature not yet built) — not because of import/syntax errors in existing code. Report the baseline to the user.

## Phase 4 — Build until green, then update docs

1. Implement the plan file by file, citing FC IDs in code where requirements are implemented, and applying each loaded skill's conventions to the files it governs (component anatomy/CSS/stories; routers/controllers/services/DI/schemas; nodes/edges/tools/interrupts).
2. Run the full test suite after each meaningful change. On failures: read them, fix the code, re-run. If a test itself was wrong, correct it — but only when it contradicts the agreed spec, and call that out explicitly. Never weaken a test just to make it pass.
3. Repeat until every test passes.
4. **Docs stay current** (repo rule): re-assess what the change affected — the FR document, the domain model, `AGENTS.md` repo map, and any dated proposals — and update anything now stale.
5. Finish with a short summary: spec FCs implemented, files changed, final test output, docs updated — and suggest `git diff` review before committing.