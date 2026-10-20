"""Resource services — business logic wrapping the agent, db managers, and core engine.

In the wired app, every method here delegates to deterministic components
(`AIAdvisorAgent` for conversation, `CourseRecommendationValidator` /
`DegreePlanGenerator` in `core` for decisions) or to `SQLDatabaseManager` /
`VectorDatabaseManager`. Scaffold state: methods whose backing zone doesn't
exist yet (monorepo outline steps 2–4) raise `NotWiredError` → HTTP 501
(never fake data, per AGENTS.md's grounded-answers rule).
"""