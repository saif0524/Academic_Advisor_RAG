---
description: Draft an implementation plan traced to functional requirements
argument-hint: "<feature description>"
---
Propose an implementation plan for this feature: $@

Ground the plan in the project docs before proposing anything:
1. Read `docs/functional-requirements.md` and identify every FC this feature touches; cite the IDs explicitly.
2. Read `docs/ai_advisor_domain_model.md` and map the feature onto the existing classes (`Student`, `Course`, `CourseSection`, `DegreePlan`, `CourseRecommendationValidator`, `DegreePlanGenerator`, `AIAdvisorAgent`, DB managers, UI). Note any new classes versus new methods/attributes on existing ones.
3. Follow the architecture rules in `AGENTS.md` (deterministic engine first, data routing, grounded answers).
4. If the feature recommends or schedules courses, list exactly which validator checks (FC29–FC32) apply and confirm none can be bypassed by the LLM path.

Output format: affected FCs → components per layer (frontend / agent / SQL / Chroma / engine) → data model changes → open questions for the team.

Do NOT modify source code in this step — produce the plan only.