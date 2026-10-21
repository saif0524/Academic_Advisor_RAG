"""Core academic domain entities (§1 of the domain model).

Dataclasses only: no LLM, no database, no I/O. They are the shared language
between `database` managers and `server` services. Any constraint math on
recommendations lives in the §2 engine (built separately — FC29–FC32).
"""