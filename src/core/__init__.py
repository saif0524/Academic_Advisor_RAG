"""Core academic entities & deterministic engine (§1–§2 of the domain model).

Pure Python: stdlib only, no LLM/database imports. The engine (validator,
plan generator) is built as its own feature; this module currently holds the
§1/§2 entity dataclasses that the database and server zones map onto.
"""