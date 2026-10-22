"""HTTP layer for the Academic AI Advisor (FC37).

A thin adapter over `agent`, `database`, and `core` (none of which import
this package):

    routers (HTTP shape) → services (logic over agent/database/core)
    schemas = Pydantic request/response contracts
"""
