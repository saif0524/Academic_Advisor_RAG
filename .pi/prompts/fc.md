---
description: Look up functional requirements by FC ID
argument-hint: "[fc ids, e.g. 29 31 32]"
---
Read `docs/2026-10-18-functional-requirements.md` and locate the requirements with these IDs: $@

Treat each argument as one FC number (e.g. `29` → FC29). For each requirement, output its ID, title, and full notes, plus one line on where it belongs in the architecture (React UI / LangChain agent / SQLite / Chroma / deterministic validator engine).

If no IDs were supplied, instead output a compact index of the entire document: each section heading with its FC range and a one-line description.