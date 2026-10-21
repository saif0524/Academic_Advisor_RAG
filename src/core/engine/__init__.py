"""§2 deterministic planning/audit engine — pure Python, no LLM/db imports.

`CourseRecommendationValidator` (FC29–FC32) + degree-progress counting (FC19,
FC24). `DegreePlanGenerator` (FC2/FC25/FC26) remains unbuilt — plan writes
are a separate build pass."""
from core.engine.progress import compute_degree_progress
from core.engine.results import ConstraintCheck, ValidationResult
from core.engine.validator import CourseRecommendationValidator

__all__ = [
    "CourseRecommendationValidator",
    "ConstraintCheck",
    "ValidationResult",
    "compute_degree_progress",
]