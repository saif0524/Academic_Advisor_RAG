"""Resource services — each one wraps the agent, db managers, or core engine.

Decisions always come from deterministic code (`CourseRecommendationValidator`,
`DegreePlanGenerator`); data comes from SQLite/Chroma, never invented.
"""
