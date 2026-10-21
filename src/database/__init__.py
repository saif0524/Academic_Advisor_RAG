"""Persistence & retrieval zone (§4 of the domain model).

SQLDatabaseManager (SQLite — FC33 structured side) and VectorDatabaseManager
(Chroma — unstructured side, FC9/FC35). May import `core` entities and
LangChain-core abstractions only — never the agent or server zones.
"""