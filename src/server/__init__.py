"""HTTP transport for the Academic AI Advisor (proposed FC-new-rest-api).

Its own top-level zone (`src/server/`): a thin adapter over `agent`,
`database`, and `core` — and nothing in `agent`/`database`/`core` may import
this package. Conventions live in `.pi/skills/fastapi/SKILL.md`:

    routers (HTTP shape) → controllers (orchestration) → services
    (business logic wrapping agent/database/core) → schemas (Pydantic contracts)
"""