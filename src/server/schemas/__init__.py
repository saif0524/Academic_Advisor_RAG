"""Pydantic v2 request/response contracts, grouped per resource.

Internal domain objects (core.entities) are never returned raw — schemas map
explicitly from SQLite/Chroma/engine output once those zones are wired.
"""