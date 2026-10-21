"""§2 deterministic engine results (FC29–FC32 payloads).

`ConstraintCheck` mirrors `server.schemas.audit.ConstraintCheck` one level
down (core can't import the server layer): `check_id` names the owning FC so
clients and the summarizer can render per-check pass/fail honestly.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List, Optional


@dataclass
class ConstraintCheck:
    """One deterministic safeguard result (FC29–FC32 / §2 Req 4c).

    `passed is None` means the check needs data that isn't on record — an
    honest 'unknown', never a guess."""

    check_id: str
    description: str
    passed: Optional[bool] = None
    reason: Optional[str] = None

    def payload(self) -> dict:
        return asdict(self)


@dataclass
class ValidationResult:
    """Aggregated eligibility (§2): `eligible` is False when any hard check
    (FC29–FC32) fails; None when the hard checks are unanimously unknown;
    True only when every hard check passes. Informational checks (§2 4c)
    ride along without affecting eligibility."""

    eligible: Optional[bool] = None
    checks: List[ConstraintCheck] = field(default_factory=list)

    @classmethod
    def aggregate(
        cls, hard_checks: List[ConstraintCheck],
        informational: Optional[List[ConstraintCheck]] = None,
    ) -> "ValidationResult":
        informational = informational or []
        passed_values = [c.passed for c in hard_checks]
        if any(v is False for v in passed_values):
            eligible = False
        elif any(v is None for v in passed_values):
            eligible = None
        else:
            eligible = True
        return cls(eligible=eligible, checks=hard_checks + informational)

    def payload(self) -> dict:
        return {"eligible": self.eligible, "checks": [c.payload() for c in self.checks]}