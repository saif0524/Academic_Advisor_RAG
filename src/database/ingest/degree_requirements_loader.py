"""Degree-requirement document parsing (FC15/FC18/FC32 records).

Parses data/CS-requirements-BCS.md / data/SE-requirements-BSE.md:
- YAML frontmatter → degree_id, major_name, credit totals (no invention)
- `### <Block> (<n> Hours)` headings → blocks; kind from the enclosing `##`
  section (General Core → general_core, Mathematics & Basic Science →
  math_science, Major Requirements → major_core)
- table rows `**CODE NNNN** | Title | hours` → DegreeBlockCourse; option rows
  ("Option N" / "Choice X") group into select-one option_groups
- bucket rows `**<name>** | n Hours` → one elective block per bucket

Canonical course identity per repo rule: corpus-backed CSE courses use their
4-digit corpus id; everyone else keeps the full code ("ENGL 1301", "CSE 2381").
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from core.entities.course import Course
from core.entities.degree import DegreeBlock, DegreeBlockCourse, DegreeRequirement
from database.ingest.course_desc_loader import load_course_desc

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

_CODE_RE = re.compile(r"^[A-Za-z]{2,5}\s\d{4}$")
_HOURS_HEADING_RE = re.compile(r"^(.*?)\s*\((\d+)\s+Hours?\)$")
_SELECT_LINE_RE = re.compile(r"Select\s+(one|of|4\s+hours|\d+\s+hours)", re.IGNORECASE)
_OPTION_PREFIX_RE = re.compile(r"(Option\s+\d+|Choice\s+[A-Z0-9]|or\s+Choice)", re.IGNORECASE)
_BUCKET_LINE_RE = re.compile(r"\*{2}(.+?)\*{2}\s*\|\s*(\d+)\s*Hours?")

_DEGREE_FILES = ("CS-requirements-BCS.md", "SE-requirements-BSE.md")


def load_degree_requirements(data_dir: Path = DATA_DIR) -> List[DegreeRequirement]:
    """Parse both degree .md files into DegreeRequirement records with blocks."""
    degrees: List[DegreeRequirement] = []
    corpus_ids = {c.course_id for c in load_course_desc(data_dir)}
    for filename in _DEGREE_FILES:
        path = data_dir / filename
        if not path.exists():
            continue
        text = path.read_text()
        frontmatter = _parse_frontmatter(text)
        if frontmatter.get("type") != "DegreeRequirement":
            continue
        degrees.append(_parse_degree_document(frontmatter, text, corpus_ids))
    return degrees


def derive_courses_from_requirements(
    degrees: List[DegreeRequirement], corpus_ids: Optional[set] = None
) -> List[Course]:
    """Course rows for every concrete course referenced by requirement tables.

    Hours/titles come from the requirement tables; catalog-backed CSE courses
    keep their corpus id (and 4-digit identity), the rest keep full codes.
    """
    corpus_ids = corpus_ids if corpus_ids is not None else {c.course_id for c in load_course_desc()}
    merged: Dict[str, Course] = {}
    for degree in degrees:
        for block in degree.blocks:
            if block.kind == "electives":
                continue  # elective buckets hold no concrete course rows
            for row in block.courses:
                department, number, code = _normalize_code(row.course_code)
                course_id = _resolve_course_id(department, number, corpus_ids)
                course = merged.setdefault(course_id, Course(
                    course_id=course_id,
                    title=row.title or code,
                    description=None,
                    credit_hours=row.credit_hours,
                    department=department,
                    number=number,
                    course_code=code,
                ))
                if row.credit_hours is not None:
                    course.credit_hours = row.credit_hours
    return sorted(merged.values(), key=lambda c: c.course_id)


# ----------------------------------------------------------------- internals

def _parse_frontmatter(text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def _parse_degree_document(frontmatter: dict, text: str, corpus_ids: set) -> DegreeRequirement:
    blocks: List[DegreeBlock] = []
    section = "general"
    for line in text.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            if "major" in title.lower():
                section = "major"  # must precede math/science: "Computer Science Major" contains "science"
            elif "general core" in title.lower():
                section = "general"
            elif "math" in title.lower() or "science" in title.lower():
                section = "math_science"
            continue
        if line.startswith("### "):
            heading = line[4:].strip()
            blocks.extend(_parse_block(heading, _table_lines_after(text, heading), section, corpus_ids))
    return DegreeRequirement(
        degree_id=str(frontmatter["degree_id"]),
        major_name=str(frontmatter["major_name"]),
        total_credits_required=frontmatter.get("total_credits_required"),
        max_semester_credits=frontmatter.get("max_semester_credits"),
        institution=frontmatter.get("institution"),
        core_courses=_collect_ids(blocks, "major_core"),
        concentration_courses=_collect_ids(blocks, "concentration"),
        elective_rules={b.elective_bucket: b.credits_required or 0 for b in blocks if b.kind == "electives"},
        blocks=blocks,
    )


def _parse_block(heading: str, lines: List[str], section: str, corpus_ids: set) -> List[DegreeBlock]:
    """One `### ` heading → concrete-course block, or one elective block per
    bucket row (a bucket table never carries concrete course rows)."""
    rows, buckets = _parse_table(lines, corpus_ids)
    if rows:
        header_match = _HOURS_HEADING_RE.match(heading)
        name = header_match.group(1).strip() if header_match else heading
        return [DegreeBlock(
            name=name,
            kind=_kind_for_section(section),
            credits_required=int(header_match.group(2)) if header_match else None,
            courses=rows,
        )]
    return [
        DegreeBlock(name=bucket, kind="electives", credits_required=hours, elective_bucket=bucket)
        for bucket, hours in buckets
    ]


def _kind_for_section(section: str) -> str:
    return {"general": "general_core", "math_science": "math_science", "major": "major_core"}[section]


def _parse_table(lines: List[str], corpus_ids: set) -> Tuple[List[DegreeBlockCourse], List[Tuple[str, int]]]:
    """One requirement table → concrete course rows (+ select-one grouping)
    and/or elective bucket rows (bucket name, credit hours)."""
    rows: List[DegreeBlockCourse] = []
    buckets: List[Tuple[str, int]] = []
    current_group: Optional[str] = None
    for line in lines:
        if _SELECT_LINE_RE.search(line):  # e.g. "**Select one of the following:**"
            current_group = f"select-{len(rows) + 1}"
            continue
        cells = _cells(line)
        if len(cells) == 2 and "**" in line:  # elective bucket: **<name> | n Hours
            match = _BUCKET_LINE_RE.search(line)
            if match:
                buckets.append((match.group(1).strip(), int(match.group(2))))
            continue
        if len(cells) < 3:
            continue
        code_index = 0 if len(cells) == 3 else 1  # 3-cell plain rows; 4-cell option rows
        code = _strip(cells[code_index])
        if not _CODE_RE.match(code):
            continue
        hours_cell = _strip(cells[code_index + 2])
        course = DegreeBlockCourse(
            course_code=code,
            title=_strip(cells[code_index + 1]),
            credit_hours=int(hours_cell) if hours_cell.isdigit() else None,
            course_id=None,
            option_group=current_group if current_group else None,
        )
        department, number, _ = _normalize_code(course.course_code)
        course.course_id = _resolve_course_id(department, number, corpus_ids)
        rows.append(course)
    return rows, buckets


def _table_lines_after(text: str, heading: str) -> List[str]:
    """Lines of the table that follows the given `### heading`."""
    marker = f"### {heading}"
    position = text.find(marker)
    if position < 0:
        return []
    after = text[position + len(marker):]
    lines: List[str] = []
    for line in after.splitlines():
        stripped = line.strip()
        if (line.startswith("### ") or line.startswith("## ")) and lines:
            break
        if not lines and not stripped.startswith("|"):
            continue
        lines.append(stripped)
    return [l for l in lines if l.strip()]


def _cells(line: str) -> List[str]:
    if not line.startswith("|"):
        return []
    cells = [part.strip() for part in line.strip().strip("|").split("|")]
    while cells and not cells[-1]:  # drop the trailing empty cell md tables carry
        cells.pop()
    return cells


def _strip(cell: str) -> str:
    return cell.replace("*", "").replace("\u00a0", " ").strip()


def _normalize_code(code: str) -> Tuple[str, str, str]:
    parts = code.strip().replace("\u00a0", " ").split()
    if len(parts) != 2:
        raise ValueError(f"Cannot parse requirement course code {code!r}")
    department, number = parts[0].upper(), parts[1]
    return department, number, f"{department} {number}"


def _resolve_course_id(department: str, number: str, corpus_ids: set) -> str:
    # Only catalog-backed CSE courses use the bare corpus id — other departments
    # keep full codes ("ENGL 1301") so ids never collide with CSE numbers:
    # ENGL 1301 and CSE 1301 are different courses.
    if corpus_ids and department == "CSE" and number in corpus_ids:
        return number
    return f"{department} {number}"


def _collect_ids(blocks: List[DegreeBlock], kind: str) -> List[str]:
    ids: List[str] = []
    for block in blocks:
        if block.kind == kind:
            for row in block.courses:
                if row.course_id or row.course_code:
                    ids.append(row.course_id or row.course_code)
    return ids