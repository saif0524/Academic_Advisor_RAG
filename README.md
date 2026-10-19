# Academic AI Advisor

RAG-based academic advising platform: course search/discovery, degree exploration, personal degree plans, and a conversational advising assistant that can act on a student's behalf (with confirmation).

| Layer | Choice |
| --- | --- |
| Frontend | React (built-in state management only) |
| Agent / LLM | Python + LangChain (`src/main/AI_Assistant.py`) |
| Structured data | SQLite — students, sections, enrollments, plans, chat history |
| Unstructured data | Chroma — course descriptions, catalog text, degree requirements (embeddings) |

## Repo structure

- `AGENTS.md` — repo guide + architecture rules, auto-loaded as pi instructions
- `docs/2026-10-18-functional-requirements.md` — FC1–FC36, single source of truth for scope
- `docs/2026-10-18-ai-advisor-domain-model.md` — class specs (§1 entities, §2 engine, §3 agent, §4 DB managers, §5 UI)
- `docs/` — planning documents for the AI advisor implementation: functional requirements, the domain model, dated feature proposals, implementation logs
- `data/course-desc.jsonl` — seed RAG corpus (75 lines of `{"id", "title", "description"}`)
- `data/cse_undergrad_courses.pdf` — CSE undergraduate degree requirements
- `src/main/` — backend entry point
- `.pi/` — project-level pi configuration (see below)

## Documentation map

What each documentation file is for and when to touch it:

| File | Purpose |
| --- | --- |
| `README.md` | This file — project overview, setup, and how to use the pi skills, prompt templates, and `/build` in this repo. |
| `AGENTS.md` | Repo guide auto-loaded as pi instructions: repo map, stack, core architecture rules, and workflow. Update whenever the repo structure or architecture rules change. |
| `docs/2026-10-18-functional-requirements.md` | Single source of truth for scope: FC1–FC36 grouped by feature area (§1 degree plans, §2 course discovery, §3 degree requirements, §4 class management, §5 assistant engine, §6 recommendation safeguards, §7 data & assumptions). Every feature is traced to FC IDs here; look them up with `/fc <ids>`. |
| `docs/2026-10-18-ai-advisor-domain-model.md` | Class specifications for the implementation: §1 domain entities (`Student`, `Course`, `DegreePlan`, …), §2 planning/validation engine (`CourseRecommendationValidator`, `DegreePlanGenerator`), §3 LangChain conversation layer (`AIAdvisorAgent`), §4 DB managers, §5 UI. |
| `docs/2026-10-19-src-monorepo-structure.md` | Dated planning proposal: layered `src/` monorepo (core / database / agent / frontend) with dependency rules; status: proposed, pre-implementation. |
| `docs/implementation-log.md` | Append-only build log written by the `/build` DOC WRITER phase; created on the first `/build` run, so it may not exist yet. |

New planning documents follow the dated convention `docs/<YYYY-MM-DD>-<slug>.md` (e.g. written by the architect skill when you ask it to "write the proposal").

## Project setup

### 1. Prerequisites

- **Node.js 22.19+** (for pi and the dev tooling)
- **Python 3.x** (for the LangChain agent)
- **git**

### 2. Install the pi coding agent

```bash
curl -fsSL https://pi.dev/install.sh | sh
# or: npm install -g --ignore-scripts @earendil-works/pi-coding-agent
pi --version
```

This repo also pins pi as a dev dependency (`package.json` → `@earendil-works/pi-coding-agent`); run `npm install` in the repo root to get it locally.

### 3. Configure model access

The repo uses an Ollama Cloud endpoint via a custom provider. Copy the committed template and fill in your key:

```bash
cp models.json.example models.json
export OLLAMA_API_KEY="your-key"
```

- `models.json` is **gitignored** — never commit real keys. Use `$OLLAMA_API_KEY` env interpolation in the file (as the example does).
- `.pi/settings.json` sets the project default model/provider; switch at runtime with `/model` or `/login`.

### 4. Start pi in the repo

```bash
cd /path/to/Academic_Advisor_RAG
pi
```

On first start pi asks you to **trust the project** — this is what enables the project `.pi/` config (skills, prompts, extension). Say yes. Then check `/skill:advisor-domain` and `/fc` appear in `/` command completion.

Useful daily commands: `/model`, `/login`, `/settings`, `/resume`, `/continue` (CLI: `pi --continue`), and `/reload` (see below).

## Using pi in this repo

Pi discovers project resources from `.pi/` after project trust. Everything below is team-shared and versioned — if you change anything under `.pi/`, **commit it so teammates get it via `git pull` + `/reload`**.

### Instructions (always loaded)

- `AGENTS.md` (repo root) and `.pi/APPEND_SYSTEM.md` are loaded into pi's system prompt at startup. They carry the non-negotiable architecture rules: **deterministic engine first** (FC29–FC32 in code, never the LLM), **never fabricate academic data**, **cite FC IDs**, **confirm before acting** (FC23), and **route queries by data type** (SQLite for exact facts, Chroma for semantic search — FC9/FC33).
- Run `/reload` after editing either file (or any `.pi/` resource) in an active session.

### Skills (loaded on demand)

Skills are directories under `.pi/skills/` containing a `SKILL.md` with a `name` and a `description`. Pi advertises only the name + description to the model at startup; the full instructions enter context only when the task matches. To force-load one explicitly, use `/skill:<name>` (arguments become the user request).

| Command | Skill | Use it for |
| --- | --- | --- |
| `/skill:advisor-domain` | advisor-domain | **Implementing or reviewing feature code.** Loads the engineering rules: safeguard ownership table (FC29–FC32 → validator methods), intent routing (`AIAdvisorAgent` classify → tool → summarize), SQLite/Chroma split (FC33), seed-data formats, and stack/baseline assumptions. |
| `/skill:architect <feature>` | architect | **Scoping a feature before implementation.** Starts a two-phase design chat: (1) scoping — grounded discussion, cites FC IDs, no files written; (2) after you explicitly say "write the proposal", it writes exactly one `docs/<date>-<slug>.md` proposal with required sections. |

Rules of thumb: new feature work starts with `architect` (scope → proposal), then switches to `advisor-domain` when writing or reviewing the actual code. The model also auto-loads a skill when your prompt clearly matches its description, but forcing it via `/skill:` is more reliable.

### Prompt templates (slash commands)

Markdown files under `.pi/prompts/` become `/` commands; `$@` is replaced by your arguments.

| Command | Template | What it does |
| --- | --- | --- |
| `/fc <ids>` | `.pi/prompts/fc.md` | Look up functional requirements, e.g. `/fc 29 30 31 32` — outputs ID, title, notes, and where each lives in the architecture. With no IDs, prints a full index of the FC document. |
| `/plan-feature <description>` | `.pi/prompts/plan-feature.md` | Drafts an implementation plan traced to FC IDs, mapped onto domain-model classes, listing which validator checks (FC29–FC32) apply. Plan only — modifies no source code. |

### `/build` extension

`.pi/extensions/orchestrator.ts` registers a `/build <feature description>` command: a deterministic pipeline of sequential pi subprocesses — **ARCHITECT** (read-only, emits a JSON task graph) → **WORKER** (one subprocess per task, in dependency order) → **TESTER** (fresh subprocess, must output `PASS`/`FAIL`) → **DOC WRITER** (appends to `docs/implementation-log.md`).

Per-phase model defaults live in the committed `.pi/pipeline.json`; override per user with `PI_BUILD_ARCHITECT_MODEL`, `PI_BUILD_WORKER_MODEL`, `PI_BUILD_TESTER_MODEL`, `PI_BUILD_DOCS_MODEL`, `PI_BUILD_TIMEOUT_MS`, etc. The orchestrator itself contains no LLM logic.

## Workflow

1. Trace the feature to its FC ID(s) before implementing (see `docs/2026-10-18-functional-requirements.md`).
2. `/skill:architect <feature>` to scope → say "write the proposal" to get `docs/<date>-<slug>.md`.
3. `/plan-feature <description>` (or the proposal's implementation outline) to get the plan.
4. `/skill:advisor-domain` while implementing; `/fc <ids>` to check requirements anytime.
5. Docs stay current: an implementation isn't done until affected planning docs are updated if stale — the FC requirements doc, the domain model, any related dated docs in `docs/`, and the `AGENTS.md` repo map.

## Data & assumptions

- Courses, sections, prerequisites, credit limits, and degree requirements exist **only** in SQLite and Chroma — the assistant never invents them. Lookup failure is relayed, not papered over.
- Seed corpus: `data/course-desc.jsonl` (Chroma ingest); degree requirements parsed from `data/cse_undergrad_courses.pdf`.
- Auth is out of scope (FC36): pre-authenticated student sessions are assumed.
- `AI_Assistant 5.java` in `src/main/` is an early-design leftover — ignore it.

## References

- [Pi documentation](https://github.com/earendil-works/pi/tree/main/docs): [skills](https://github.com/earendil-works/pi/blob/main/docs/skills.md), [prompt templates](https://github.com/earendil-works/pi/blob/main/docs/prompt-templates.md), [extensions](https://github.com/earendil-works/pi/blob/main/docs/extensions.md), [models & providers](https://github.com/earendil-works/pi/blob/main/docs/models.md)