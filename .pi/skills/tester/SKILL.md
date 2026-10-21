---
name: tester
description: Testing conventions for the Academic AI Advisor — write and review unit tests for business logic only (deterministic engine, services, agent orchestration with stubbed LLM, db managers). Explicitly excludes React/UI tests; UI is verified via Storybook review instead. Use when writing, running, or reviewing tests, or deciding what a /build phase 3 test suite must cover.
---

# Tester — business logic only

The test surface is **business logic**. No unit tests for UI.

**POC fidelity (2026-10-22):** test the spec'd behavior and the deterministic
paths — skip exhaustive edge-case matrices, negative-permutation testing, and
robustness suites the assignment doesn't require. A lean suite that pins the
engine semantics and endpoint contracts beats a sprawling one.

## In scope (pytest; tests mirror `src/` zones)

```text
tests/
├── core/       # the heart: offline, zero-mock tests
├── database/
└── agent/
```

- **`src/core/engine/` — the priority.** Every validator check (`CourseRecommendationValidator`: FC29–FC32), plan generation invariants (`DegreePlanGenerator`: FC2, FC25–FC26), major-switch/comparison logic — pure Python, must pass with no LLM and no stores: if a core test needs a mock, the architecture is wrong — flag it instead of mocking.
- **`services/` (FastAPI layer)** — orchestration, error mapping, FC23 confirmation enforcement; db managers and agent faked or overridden via `app.dependency_overrides`.
- **agent orchestration (`src/agent/`)** — routing and state transitions (`classify_query_intent`, FC22, FC33), LangGraph nodes/edges/interrupt flow, tool wiring — always with the **LLM stubbed**: never make live model calls; assert on routing outcomes, state transitions, and which tools were invoked, not on model wording. The confirmation gate (FC23) and clarification loop (FC27–28) are tested here with fake messages/tools.
- **`src/database/`** — `SQLDatabaseManager` against in-memory SQLite fixtures; `VectorDatabaseManager` against an ephemeral Chroma client or fake embeddings; seed loaders against `data/` fixtures (`course-desc.jsonl` etc.).

For a `/build` feature whose plan spans layers: test the layers **below** the UI — e.g. a new React card backed by an endpoint + service tests the service rules; the component itself gets no tests, only its Storybook story.

## Out of scope (do not create or ask for these)

- React component/page tests — no Vitest, no Testing Library; UI verification is Storybook review (`react-component` skill).
- Pydantic schema-shape tests; HTTP smoke tests (allowed but optional, not part of a suite).
- Snapshot/golden-file tests of LLM output — stub the model; test deterministic paths and tool calls.

## Rules

- Name or comment every test with the FC(s) it verifies.
- Clear arrange/act/assert; test names state behavior (`test_plan_generator_rejects_semester_over_credit_cap_FC32`).
- A suite must be runnable offline and fast — anything requiring network/LLM goes behind a stub.
- For `/build`: phase 3 writes this suite first and confirms it fails for the right reason; phase 4 runs `pytest` after each change until green. Never weaken a test to make it pass — expected-behavior changes require the user's sign-off (per `/build`).