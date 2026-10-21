"""Canonical course-id normalization (repo data rule, FC11/FC33).

4-digit corpus ids for catalog-backed CSE courses ("4380"); full code
otherwise ("ENGL 1301"). The normalizer only shapes input — the SQLite
lookup decides whether anything actually exists (never fabricated)."""
from __future__ import annotations

import re

_NUMBER = re.compile(r"^(\d{3,4})$")
_FULL = re.compile(r"^([A-Z]{2,5})\s+(\d{3,4})$")
_COMPACT = re.compile(r"^([A-Z]{2,5})(\d{3,4})$")

# Department tokens seen in the catalog (data/*.md) — used only to decide
# whether a capitalized word before a number is a course code; unknown words
# are NOT departments, so digits-only ids remain the fallback (never mis-scoped).
DEPARTMENT_TOKENS = frozenset({
    "CSE", "ENGL", "MATH", "PHYS", "POLS", "PHIL", "MUSI", "HIST", "ECON",
    "ART", "THEA", "CHEM", "BIOL", "PSYC", "SOCI", "COMM", "KINE", "SPAN",
    "FREN", "GERM", "ACCT", "FINA", "MANA", "MKTG", "BUSA", "JOUR", "MUAP",
    "MUEN", "NURS", "RELS", "DANC", "MILS", "IE", "CEE", "ME", "EE",
})


def _is_department(token: str) -> bool:
    return token in DEPARTMENT_TOKENS


def normalize_course_id(raw: str) -> str:
    """'CSE 4380'/'cse 4380' → '4380'; 'ENGL 1301' → 'ENGL 1301';
    '4380' → '4380'; anything else returned uppercased unchanged."""
    text = re.sub(r"\s+", " ", (raw or "").strip()).upper()
    if _NUMBER.fullmatch(text):
        return text
    match = _FULL.fullmatch(text) or _COMPACT.fullmatch(text)
    if match:
        dept, number = match.groups()
        if dept == "CSE":
            return number
        return f"{dept} {number}"
    return text


def course_mentions(text: str) -> list:
    """Extract normalized course ids mentioned in a message ('CSE 4380',
    '4380', 'ENGL 1301') — deduplicated, in order of appearance. A non-
    department word before a number is not a course code (verbs like MARK)."""
    text = (text or "").upper()
    mentions: list = []
    covered: list = []  # spans of dept-prefixed codes — skip bare re-extraction
    for match in re.finditer(r"\b([A-Z]{2,5})\s(\d{4})\b", text):
        if _is_department(match.group(1)):
            mentions.append(normalize_course_id(
                f"{match.group(1)} {match.group(2)}"))
            covered.append((match.start(2), match.end(2)))
    for match in re.finditer(r"\b(\d{4})\b", text):
        if any(start <= match.start(1) < end for start, end in covered):
            continue  # already part of a full code
        mentions.append(match.group(1))
    seen: set = set()
    ordered: list = []
    for mention in mentions:
        if mention not in seen:
            seen.add(mention)
            ordered.append(mention)
    return ordered