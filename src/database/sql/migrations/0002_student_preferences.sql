-- 0002: planning preferences (FC25 optional-summer toggle, FC32 cap input).
-- One row per student; created lazily on first save (POC fidelity).
CREATE TABLE IF NOT EXISTS student_preferences (
    student_id              TEXT PRIMARY KEY,
    max_credits_per_semester INTEGER,
    include_summer          INTEGER NOT NULL DEFAULT 0,
    preferred_class_times   TEXT,
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);