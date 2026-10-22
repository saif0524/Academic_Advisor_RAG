# Academic AI Advisor

RAG-based academic advising platform: course search/discovery, degree exploration, personal degree plans, and a conversational advising assistant that can act on a student's behalf (with confirmation).

| Layer | Choice |
| --- | --- |
| Frontend | React + TypeScript + Vite (`src/frontend/`) |
| Agent / LLM | Python + LangGraph/LangChain (`src/agent/`), served by FastAPI (`src/server/`) |
| Structured data | SQLite — students, sections, enrollments, plans, chat history |
| Unstructured data | Chroma — course descriptions, catalog text, degree requirements (embeddings) |

## Quick start

Pick one: **Docker** (one command, nothing else to install) or **local dev** (hot reload).

### Option A — Docker (FC38)

Prerequisite: Docker with Compose.

```bash
cp .env.example .env          # set OLLAMA_API_KEY (gitignored); see "Configuration"
docker compose --env-file .env -f docker/docker-compose.yml up --build   # run from repo root
```

| Service | URL | Notes |
| --- | --- | --- |
| api (FastAPI) | http://localhost:8000 (`/health`, `/docs`) | Seeds SQLite + Chroma from `data/` on every startup (FC33) |
| web (React + nginx) | http://localhost:3000 | Static production bundle; calls the api at `http://localhost:8000` |

- **LLM stays external:** the api container reaches the **host** Ollama at `http://host.docker.internal:11434`. For a fully offline demo set `ADVISOR_LLM_PROVIDER=stub` in `.env`.
- **Persistence:** seed-owned tables reload each `up` (FC33); chat/plan/preference data persists in the `advisor-runtime` volume (FC34). Wipe it with `docker compose --env-file .env -f docker/docker-compose.yml down -v`.
- **First start:** the api downloads the ONNX MiniLM embedding model once (~90 MB, cached in the `advisor-model-cache` volume). Without network it falls back to deterministic hash embeddings (weaker semantics, still grounded).
- If the api isn't at `localhost:8000`, set `VITE_API_BASE_URL` in `.env` and rebuild: `docker compose --env-file .env -f docker/docker-compose.yml build web`.

### Option B — Local development

Prerequisites: **Python 3.9+** (Docker image uses 3.12), **Node.js 22+**, git.

**1. Backend (terminal 1)** — from the repo root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env    # optional; only needed for OLLAMA_API_KEY
PYTHONPATH=src .venv/bin/uvicorn server.app:app --reload   # http://127.0.0.1:8000/docs
```

On startup the server seeds `.runtime/` (SQLite + Chroma, gitignored) from `data/`. Health check: `curl http://127.0.0.1:8000/health`.

**2. Frontend (terminal 2):**

```bash
cd src/frontend
npm install
npm run dev             # http://localhost:5173
```

The frontend calls `http://localhost:8000` by default (override with `VITE_API_BASE_URL`). The api allows CORS from `localhost:3000` and `localhost:5173`.

**3. LLM** — default provider is Ollama with model `glm-5.3-flash:cloud`:

- Run Ollama locally (`http://localhost:11434`) and export `OLLAMA_API_KEY` for cloud models, **or**
- Skip the LLM entirely: `ADVISOR_LLM_PROVIDER=stub PYTHONPATH=src .venv/bin/uvicorn server.app:app --reload` (deterministic, grounded stub answers).

For fast offline runs without the embedding download also set `ADVISOR_EMBEDDING_FUNCTION=hash`.

## Configuration

Environment variables (backend reads the process env; Docker reads `.env` via `--env-file`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_API_KEY` | — | Key for Ollama Cloud models |
| `ADVISOR_LLM_PROVIDER` | `ollama` | `ollama` or `stub` (deterministic, no model) |
| `ADVISOR_LLM_MODEL` | `glm-5.3-flash:cloud` | Ollama model name |
| `ADVISOR_LLM_BASE_URL` | `http://localhost:11434` (Docker: `host.docker.internal`) | Ollama endpoint |
| `ADVISOR_EMBEDDING_FUNCTION` | `onnx` | `onnx` (MiniLM) or `hash` (offline/tests) |
| `ADVISOR_SEED_MODE` | `reload` | Reload seed-owned tables from `data/` on startup |
| `ADVISOR_SQLITE_PATH` / `ADVISOR_CHROMA_PATH` | `.runtime/…` | Storage locations |
| `ADVISOR_DATA_DIR` | `data/` | Seed data directory |
| `ADVISOR_HOST` / `ADVISOR_PORT` | `127.0.0.1` / `8000` | Bind address when run via `python -m server.app` |
| `ADVISOR_CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed browser origins |
| `ADVISOR_DEFAULT_STUDENT_ID` | demo student | Student used when no `X-Student-Id` header is sent (FC36) |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend → api URL (build-time) |

## Tests and checks

```bash
.venv/bin/pytest                         # backend tests (engine, db, agent, server)
cd src/frontend
npm run typecheck && npm run lint && npm run build
npm run storybook                        # component review, http://localhost:6006
npx vitest --project storybook run       # story-driven browser tests (Playwright)
```

Backend tests use the stub LLM and hash embeddings; no network or Ollama needed. There are no UI unit tests — UI is reviewed in Storybook.

## Repo structure

- `AGENTS.md` — repo guide + architecture rules, auto-loaded as pi instructions
- `data/` — seed data: `course-desc.json` (RAG corpus), `degrees/*.json`, `AICertification.json`, `general-core.json`, MOCK `sections-mock.json` and `student-demo.json`; `cse_undergrad_courses.pdf` is reference-only
- `src/core/` — pure entities + deterministic engine (validator FC29–FC32, progress FC19/FC24, plan generator FC2/FC25/FC26)
- `src/database/` — `SQLDatabaseManager`, Chroma manager, migrations, seed loaders
- `src/agent/` — LangGraph advisor graph (`llm/`) + tools (`tools/`: lookups → engine → FC23 actions)
- `src/server/` — FastAPI HTTP layer (FC37): routers → services → schemas
- `src/frontend/` — React + TypeScript UI with Storybook (see `src/frontend/README.md`)
- `docker/` + `src/frontend/Dockerfile` — containerized deployment (FC38)
- `tests/` — pytest suites mirroring the src zones
- `docs/` — `planning/` (FC requirements, domain model, proposals), `process/`, `wireframes/`, `example-chats/`
- `.pi/` — project-level pi configuration (see below)

## Documentation map

| File | Purpose |
| --- | --- |
| `README.md` | This file — setup and run instructions, plus pi usage. |
| `AGENTS.md` | Repo map, stack, architecture rules, and workflow (auto-loaded by pi). Update when structure or rules change. |
| `docs/planning/2026-10-18-functional-requirements.md` | Single source of truth for scope: FC1–FC36 (look up with `/fc <ids>`). |
| `docs/planning/2026-10-18-ai-advisor-domain-model.md` | Class specs: entities, engine, agent, DB managers, UI. |
| `docs/planning/2026-10-19-src-monorepo-structure.md` | Layered `src/` structure and dependency rules. |
| `docs/process/2026-10-20-git-process.md` | Branch naming (`<type>/fc<NN>-<slug>`), PR format, merge rules. |
| `docs/process/implementation-log.md` | Build log written by `/build` (may not exist yet). |
| `docs/wireframes/`, `docs/example-chats/` | UI wireframes; example advising sessions (reference only). |

New planning docs use `docs/planning/<YYYY-MM-DD>-<slug>.md`.

## Developing with pi (optional)

The repo ships a pi coding-agent configuration in `.pi/`. Install pi (`curl -fsSL https://pi.dev/install.sh | sh` or `npm install -g --ignore-scripts @earendil-works/pi-coding-agent`), then:

```bash
cp .pi/models.json.example ~/.pi/agent/models.json   # then: export OLLAMA_API_KEY="your-key"
pi                                                    # from the repo root; trust the project when asked
```

`~/.pi/agent/models.json` is read from your home dir; a local `.pi/models.json` is gitignored — never commit keys.

Pi resources are team-shared — if you change anything under `.pi/`, **commit it so teammates get it via `git pull` + `/reload`**.

### Instructions (always loaded)

- `AGENTS.md` (repo root) and `.pi/APPEND_SYSTEM.md` are loaded into pi's system prompt at startup. They carry the non-negotiable architecture rules: **deterministic engine first** (FC29–FC32 in code, never the LLM), **never fabricate academic data**, **cite FC IDs**, **confirm before acting** (FC23), and **route queries by data type** (SQLite for exact facts, Chroma for semantic search — FC9/FC33).
- Run `/reload` after editing either file (or any `.pi/` resource) in an active session.

### Skills (loaded on demand)

Skills are directories under `.pi/skills/` containing a `SKILL.md` with a `name` and a `description`. Pi advertises only the name + description to the model at startup; the full instructions enter context only when the task matches. To force-load one explicitly, use `/skill:<name>` (arguments become the user request).

| Command | Skill | Use it for |
| --- | --- | --- |
| `/skill:advisor-domain` | advisor-domain | **Implementing or reviewing feature code.** Loads the engineering rules: safeguard ownership table (FC29–FC32 → validator methods), intent routing (`AIAdvisorAgent` classify → tool → summarize), SQLite/Chroma split (FC33), seed-data formats, and stack/baseline assumptions. |
| `/skill:architect <feature>` | architect | **Scoping a feature before implementation.** Starts a two-phase design chat: (1) scoping — grounded discussion, cites FC IDs, no files written; (2) after you explicitly say "write the proposal", it writes exactly one `docs/planning/<date>-<slug>.md` proposal with required sections. |
| `/skill:build <feature>` | build | End-to-end build: FC spec → plan → tests first → implement until green. |
| `/skill:fastapi` | fastapi | HTTP-layer conventions for `src/server/`. |
| `/skill:langgraph` | langgraph | Advisor-graph conventions for `src/agent/` (FC23 confirmation, checkpointing). |
| `/skill:react-component` | react-component | Frontend component conventions + Storybook/wireframe check. |
| `/skill:tester` | tester | Testing scope: business logic only, no UI tests. |

Rules of thumb: new feature work starts with `architect` (scope → proposal), then switches to `advisor-domain` when writing or reviewing the actual code. The model also auto-loads a skill when your prompt clearly matches its description, but forcing it via `/skill:` is more reliable.

### Prompt templates (slash commands)

Markdown files under `.pi/prompts/` become `/` commands; `$@` is replaced by your arguments.

| Command | Template | What it does |
| --- | --- | --- |
| `/fc <ids>` | `.pi/prompts/fc.md` | Look up functional requirements, e.g. `/fc 29 30 31 32` — outputs ID, title, notes, and where each lives in the architecture. With no IDs, prints a full index of the FC document. |
| `/plan-feature <description>` | `.pi/prompts/plan-feature.md` | Drafts an implementation plan traced to FC IDs, mapped onto domain-model classes, listing which validator checks (FC29–FC32) apply. Plan only — modifies no source code. |

### `/build` extension

`.pi/extensions/orchestrator.ts` registers a `/build <feature description>` command: a deterministic pipeline of sequential pi subprocesses — **ARCHITECT** (read-only, emits a JSON task graph) → **WORKER** (one subprocess per task, in dependency order) → **TESTER** (fresh subprocess, must output `PASS`/`FAIL`) → **DOC WRITER** (appends to `docs/process/implementation-log.md`).

Per-phase model defaults live in the committed `.pi/pipeline.json`; override per user with `PI_BUILD_ARCHITECT_MODEL`, `PI_BUILD_WORKER_MODEL`, `PI_BUILD_TESTER_MODEL`, `PI_BUILD_DOCS_MODEL`, `PI_BUILD_TIMEOUT_MS`, etc. The orchestrator itself contains no LLM logic.

## Workflow

1. Trace the feature to its FC ID(s) before implementing (see `docs/planning/2026-10-18-functional-requirements.md`).
2. `/skill:architect <feature>` to scope → say "write the proposal" to get `docs/planning/<date>-<slug>.md`.
3. `/plan-feature <description>` (or the proposal's implementation outline) to get the plan.
4. `/skill:advisor-domain` while implementing; `/fc <ids>` to check requirements anytime.
5. Docs stay current: an implementation isn't done until affected planning docs are updated if stale — the FC requirements doc, the domain model, any related dated proposals in `docs/planning/`, and the `AGENTS.md` repo map.

## Data & assumptions

- Courses, sections, prerequisites, credit limits, and degree requirements exist **only** in SQLite and Chroma — the assistant never invents them. Lookup failure is relayed, not papered over.
- Seed data lives in `data/` (JSON; the PDF is reference-only): `course-desc.json`, `degrees/*.json`, `AICertification.json`, `general-core.json` go to Chroma/SQLite; `sections-mock.json` and `student-demo.json` are labeled MOCK demo data.
- Auth is out of scope (FC36): pre-authenticated student sessions are assumed.

## References

- [Pi documentation](https://github.com/earendil-works/pi/tree/main/docs): [skills](https://github.com/earendil-works/pi/blob/main/docs/skills.md), [prompt templates](https://github.com/earendil-works/pi/blob/main/docs/prompt-templates.md), [extensions](https://github.com/earendil-works/pi/blob/main/docs/extensions.md), [models & providers](https://github.com/earendil-works/pi/blob/main/docs/models.md)