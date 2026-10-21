-- Academic AI Advisor — SQLite schema v1 (FC33 structured side).
-- Applies as migrations/0001_init.sql; a later migration = a new numbered file.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- FC36/FC1: student profile. One demo row seeded from data/student-demo.json;
-- rows are also created lazily on first write (name NULL = unknown).
CREATE TABLE IF NOT EXISTS students (
    student_id              TEXT PRIMARY KEY,
    name                    TEXT,
    current_major           TEXT,
    concentration           TEXT,
    career_interest         TEXT,
    selected_degree_id      TEXT,
    include_summer_sessions INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- FC7: current + previous major/specialty combinations.
CREATE TABLE IF NOT EXISTS major_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    TEXT NOT NULL,
    major_name    TEXT NOT NULL,
    concentration TEXT,
    active        INTEGER NOT NULL DEFAULT 1,
    changed_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- FC8/FC11: catalog rows. course_id = 4-digit corpus id for catalog-backed
-- courses ("1105"), full code otherwise ("ENGL 1301", "CSE 2381").
CREATE TABLE IF NOT EXISTS courses (
    course_id    TEXT PRIMARY KEY,
    department   TEXT NOT NULL,
    number       TEXT,
    title        TEXT NOT NULL,
    description  TEXT,
    credit_hours INTEGER,
    course_code  TEXT,                -- provenance form, e.g. "CSE 1105"
    source       TEXT NOT NULL        -- 'corpus' | 'requirements'
);

-- FC11: prerequisite/corequisite references (populated only when data exists).
CREATE TABLE IF NOT EXISTS course_prerequisites (
    course_id          TEXT NOT NULL,
    required_course_id TEXT NOT NULL,
    kind               TEXT NOT NULL CHECK (kind IN ('prereq', 'coreq')),
    PRIMARY KEY (course_id, required_course_id)
);

-- FC12/FC31: scheduled sections (mock seed from data/sections-mock.json).
CREATE TABLE IF NOT EXISTS sections (
    section_id     TEXT PRIMARY KEY,
    course_id      TEXT NOT NULL REFERENCES courses(course_id),
    term           TEXT NOT NULL,
    instructor     TEXT,
    meeting_days   TEXT NOT NULL DEFAULT '[]',  -- JSON array of weekday names
    start_time     TEXT,
    end_time       TEXT,
    room_capacity  INTEGER,
    enrolled_count INTEGER
);

-- FC13/FC14/FC20/FC21 + §1 EnrollmentRecord fields.
CREATE TABLE IF NOT EXISTS student_classes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     TEXT NOT NULL,
    course_id      TEXT NOT NULL REFERENCES courses(course_id),
    status         TEXT NOT NULL DEFAULT 'not_taken'
                   CHECK (status IN ('not_taken', 'in_progress', 'taken', 'passed', 'failed')),
    bookmarked     INTEGER NOT NULL DEFAULT 0,
    grade          TEXT,
    semester_taken TEXT,
    added_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, course_id)
);

-- FC15/FC18: degree catalog (parsed from data/*requirements*.md frontmatter).
CREATE TABLE IF NOT EXISTS degrees (
    degree_id              TEXT PRIMARY KEY,
    major_name             TEXT NOT NULL,
    total_credits_required INTEGER,
    max_semester_credits   INTEGER,
    institution            TEXT,
    source_file            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS degree_requirement_blocks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    degree_id        TEXT NOT NULL REFERENCES degrees(degree_id),
    block_name       TEXT NOT NULL,
    kind             TEXT NOT NULL,   -- general_core | math_science | major_core | electives
    credits_required INTEGER,
    elective_bucket  TEXT,
    sort_order       INTEGER NOT NULL DEFAULT 0,
    UNIQUE (degree_id, block_name)
);

CREATE TABLE IF NOT EXISTS degree_requirement_courses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    degree_id     TEXT NOT NULL,
    block_id      INTEGER NOT NULL REFERENCES degree_requirement_blocks(id) ON DELETE CASCADE,
    course_code   TEXT NOT NULL,
    course_id     TEXT,                -- normalized when corpus-backed
    title         TEXT,
    credit_hours  INTEGER,
    option_group  TEXT
);

-- FC2/FC6 destinations: saved plans (engine writes land later; reads wired).
CREATE TABLE IF NOT EXISTS plans (
    plan_id          TEXT PRIMARY KEY,
    student_id       TEXT NOT NULL,
    degree_id        TEXT,
    target_major     TEXT,
    concentration    TEXT,
    includes_summer  INTEGER NOT NULL DEFAULT 0,
    is_active        INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- FC4/FC5: immutable version snapshots (JSON payload).
CREATE TABLE IF NOT EXISTS plan_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         TEXT NOT NULL REFERENCES plans(plan_id),
    version_number  INTEGER NOT NULL,
    payload         TEXT NOT NULL,
    note            TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (plan_id, version_number)
);

-- FC34: advising sessions + messages persist in SQLite, never app memory.
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id     TEXT PRIMARY KEY,
    student_id     TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES chat_sessions(session_id),
    student_id TEXT NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- FC23 groundwork: proposed actions awaiting explicit confirmation.
CREATE TABLE IF NOT EXISTS chat_pending_actions (
    action_id   TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES chat_sessions(session_id),
    student_id  TEXT NOT NULL,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}',
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'confirmed', 'cancelled')),
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sections_course ON sections(course_id, term);
CREATE INDEX IF NOT EXISTS idx_student_classes ON student_classes(student_id);
CREATE INDEX IF NOT EXISTS idx_block_courses ON degree_requirement_courses(block_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages ON chat_messages(session_id, id);