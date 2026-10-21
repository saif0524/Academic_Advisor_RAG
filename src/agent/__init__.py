"""Agent zone (§3 LangChain conversation layer + HTTP transport).

Dependency rule: agent → database → core; nothing below this zone may import
from it. Layout lives in docs/2026-10-19-src-monorepo-structure.md §agent.
"""