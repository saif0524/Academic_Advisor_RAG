"""§2 deterministic degree-progress counting (FC19, FC24).

Pure, offline, moved verbatim-in-spirit from the student service during the
agent build so both the HTTP layer and the agent tools count against the
same rules (the service delegates; no drift).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.entities.degree import DegreeRequirement


def compute_degree_progress(
    degree: Optional[DegreeRequirement],
    classes: List[Any],
    hours_by_id: Dict[str, int],
) -> dict:
    """FC19 deterministic counting over real enrollment state.

    Rule per class (status passed/taken = completed; in_progress = underway):
    1. Matched to a requirement course row → hours credit that block.
    2. Unmatched CSE courses fill elective buckets whose parsed level cutoff
       they satisfy (e.g. 'CSE 4000-level' → number >= 4000), until cap.
    3. Everything else is recorded as unmatched (grounded: it maps to
       nothing in this degree) and ignored for completion.

    Returns keys: completion_percent, outstanding_requirements,
    completed_hours, per_block, per_block_in_progress, unmatched_hours.
    """
    if degree is None:
        return {
            "completion_percent": None,
            "outstanding_requirements": [],
            "completed_hours": 0,
            "per_block": {},
            "per_block_in_progress": {},
            "unmatched_hours": 0,
        }

    completed: Dict[str, int] = {}
    underway: Dict[str, int] = {}
    for entry in classes:
        hours = hours_by_id.get(entry.course_id) or 0
        if entry.status in {"passed", "taken"}:
            completed[entry.course_id] = completed.get(entry.course_id, 0) + hours
        elif entry.status == "in_progress":
            underway[entry.course_id] = underway.get(entry.course_id, 0) + hours

    per_block_done: Dict[str, float] = {}
    per_block_progress: Dict[str, float] = {}
    matched = set()
    for block in degree.blocks:
        if block.kind == "electives" or not block.courses:
            continue
        for row in block.courses:
            if row.course_id in completed:
                per_block_done[block.name] = per_block_done.get(block.name, 0.0) + (row.credit_hours or completed[row.course_id])
                matched.add(row.course_id)
            elif row.course_id in underway:
                per_block_progress[block.name] = per_block_progress.get(block.name, 0.0) + (row.credit_hours or underway[row.course_id])
                matched.add(row.course_id)

    # elective buckets: fill from unmatched classes via the bucket's level rule
    for bucket_name, hours_required in degree.elective_rules.items():
        cutoff = _elective_cutoff(bucket_name)
        filled = 0.0
        if cutoff is not None:
            for course_id, hours in list(completed.items()):
                if course_id in matched or filled >= hours_required:
                    continue
                if _satisfies_cutoff(course_id, cutoff):
                    take = min(hours, hours_required - filled)
                    filled += take
                    per_block_done[bucket_name] = per_block_done.get(bucket_name, 0.0) + take
                    matched.add(course_id)
            for course_id, hours in underway.items():
                if course_id in matched or filled >= hours_required:
                    continue
                if _satisfies_cutoff(course_id, cutoff):
                    take = min(hours, hours_required - filled)
                    filled += take
                    per_block_progress[bucket_name] = per_block_progress.get(bucket_name, 0.0) + take

    total_done = sum(per_block_done.values())
    percentage = round(100.0 * total_done / degree.total_credits_required, 1) if degree.total_credits_required else None
    total_input = sum(completed.values())
    unmatched = max(total_input - int(total_done), 0)

    # every counted block gets a key (0 when untouched) so consumers never
    # have to probe for missing entries
    for block in degree.blocks:
        if block.kind == "electives" or not block.courses:
            if block.name in (degree.elective_rules or {}):
                per_block_done.setdefault(block.name, 0.0)
                per_block_progress.setdefault(block.name, 0.0)
            continue
        if block.credits_required is not None:
            per_block_done.setdefault(block.name, 0.0)
        per_block_progress.setdefault(block.name, 0.0)
        per_block_done.setdefault(block.name, 0.0)  # non-counted blocks stay visible

    outstanding: List[str] = []
    for block in degree.blocks:
        if block.kind == "electives":
            required = block.credits_required or 0
        elif block.credits_required is not None:
            required = block.credits_required
        else:
            continue
        done = per_block_done.get(block.name, 0.0)
        progress = per_block_progress.get(block.name, 0.0)
        remaining = max(required - done, 0.0)
        suffix = f" ({progress:g} in progress)" if progress else ""
        outstanding.append(f"{block.name}: {remaining:g} of {required} hours remaining{suffix}")

    return {
        "completion_percent": percentage,
        "outstanding_requirements": outstanding,
        "completed_hours": int(total_done),
        "per_block": per_block_done,
        "per_block_in_progress": per_block_progress,
        "unmatched_hours": unmatched,
    }


def _elective_cutoff(bucket: str) -> Optional[tuple]:
    """Parse elective-bucket level rules into a (dept, min_level) floor.

    Handles the catalog's phrasings: 'CSE 4000-level Technical Electives',
    'CSE 3000-level or 4000-level ...', and 'CSE 3000/4000-level ...'."""
    match = re.search(r"([A-Z]{2,5})\s(\d{4})", bucket)
    if not match:
        return None
    or_match = re.search(r"(\d{4})-level", bucket[match.end():])
    lower_bound = (
        min(int(match.group(2)), int(or_match.group(1))) if or_match else int(match.group(2))
    )
    return match.group(1), lower_bound


def _satisfies_cutoff(course_id: str, cutoff: tuple) -> bool:
    department, number = cutoff
    if course_id.isdigit():
        # Canonical corpus ids (4-digit) are CSE courses (AGENTS.md data rule).
        return department == "CSE" and int(course_id) >= number
    parts = course_id.split()
    if len(parts) != 2 or parts[0] != department:
        return False
    try:
        return int(parts[1]) >= number
    except ValueError:
        return False