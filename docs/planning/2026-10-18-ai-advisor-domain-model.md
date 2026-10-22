# Academic AI Advisor - Domain Model & Class Specifications

---

**Implementation notes (2026-10-22, agent plan context):** §3 student context
now includes the student's ACTIVE plan (FC6) — read from SQLite via
`AdvisorToolkit.plan_context` (not Chroma, FC33) in the `exact` route
(`params.topic="plan"`) and progress audits; recommendations skip planned
courses; the classifier receives `{major, has_active_plan}` as routing hints
(the §3 `context_state`, FC27). FC23 gained `plan_add_course` /
`plan_remove_course` / `plan_move_course` / `activate_plan`, prechecked by
`DegreePlanGenerator.review_plan_semesters` and saved as new plan versions.

**Implementation notes (2026-10-22, plan/account/dashboard end-to-end build):**
the §2 engine is COMPLETE — `DegreePlanGenerator` lives in
`src/core/engine/generator.py` (pure, entity-passed). Implemented adjustments
to the §2 outline: `generate_multi_year_plan(student, target_degree,
courses_by_id, include_summer, max_credits_per_sem, current_term)` takes the
catalog as a dict instead of a db-backed attribute (core stays offline) and
returns a `PlanGenerationResult` (plan + grounded `notes`: skipped completed
courses FC30, unresolvable requirement rows, dry elective buckets, unknown
credit hours). `review_plan_semesters` (FC29–FC32 verdicts over unsaved
drafts; blocking = FC30/FC32, warning = FC29) and `compare_plans` /
`simulate_major_switch` (FC26 set-arithmetic + trade-off lines) round out the
outline. Placement semantics: prereqs must land in an EARLIER semester than
dependents (FC29 planning form; same-semester placement defers), courses
level-sorted, Fall→Spring (+ optional Summer) sequence from the current term
(an in-progress semester anchors the roadmap; passed/taken work is never
re-planned). Server: plan write endpoints (generate/update/revert/compare)
plus `GET /plans/active`, `PATCH /plans/{id}/activate`, `POST /plans/review`,
`GET /plans/options` are wired — no more 501s in the plan zone; new plans
deactivate-then-activate (generate → edit → make active, per product
decision). Concentrations are not modeled in the degrees seed, so plan
options offer 'General' per major (honest default; requested values persist
as stored text). Planning preferences (FC25 summer toggle, FC32 cap input)
persist in `student_preferences` (migration 0002) and feed generation. The
agent gained the `plan_generation` intent: stub/LLM classifier routes
"generate a plan" phrasing to a plan node that calls
`AdvisorToolkit.generate_plan` (engine + persistence; target major resolved
from the message or the student's record; honest refusal when unresolved).
Frontend swap complete: plans/students/catalog/candidate mocks are now live
HTTP calls (`planDetailToActive` maps server detail → UI shape); pages gained
real loading/empty/error states; AccountPage's confirm path applies major
changes + auto-generates an inactive plan (FC23-style UI gate), and the
timeline saves engine-validated drafts (PATCH) with version history + revert.
Stories keep deterministic DI fixtures (`reviewFn` seam) and never hit HTTP.

---

**Implementation notes (2026-10-20, agent build):** the §2 engine is now
built in `src/core/engine/` — `CourseRecommendationValidator` (FC29–FC32)
as pure functions taking entities + the data they need as arguments (per the
monorepo dependency rule, no `sql_db` attribute in core), plus
`compute_degree_progress` (FC19/FC24 — the single implementation; the
student service and the agent tools both call it — a leftover duplicate in
the service was removed 2026-10-23); `check_fulfills_degree_requirement`
(§2 Req 4c) rides along informationally and never blocks eligibility.
`DegreePlanGenerator` (FC2/FC25/FC26) followed on 2026-10-22.
The §3 layer is live in `src/agent/` — `AIAdvisorAgent` (LangGraph
classify → route → tools → summarize; the four §3 `handle_*` functions are
groups of graph nodes), `ConversationSession` (history is the durable
context). Implemented adjustments: the LLM seam is
`ADVISOR_LLM_PROVIDER=ollama` (default `glm-5.3-flash:cloud` via local
ChatOllama; `stub` = deterministic rules/templates for offline tests) — and
on any model failure the classifier/summarizer DEGRADE to the deterministic
stub on the same payload (routing/wording only; data stays tool-gathered).
FC23 confirmation is a durable pause/resume: proposals persist in the
`chat_pending_actions` table and execute only on the next turn's
`confirmed_action_id`/`cancelled_action_id` (validated in the ChatService,
re-checked in the confirm node — restart-safe across HTTP requests; this
replaces an in-process `interrupt()`). FC27/FC28: history is read from
SQLite each turn (last 12 turns) and fed to the classifier; clarification is
bounded to one question per turn. No LangGraph checkpointer is installed —
the durable conversation state IS SQLite (FC34), intentionally diverging
from the skill's dev `MemorySaver` default.

**Implementation notes (2026-10-21, database build):** entities under
`src/core/entities/` follow §1/§2 as dataclasses, with these implemented
adjustments: `Student.current_major` is stored as the major_name string (the
`DegreeRequirement` object is loaded on demand) plus `selected_degree_id`; the
`Course.course_id` is the 4-digit corpus id for catalog-backed courses
(`"1105"`) and the full code (`"ENGL 1301"`) otherwise; `DegreeRequirement`
gains `blocks` (block-level requirement structure behind FC18/FC19).
`SQLDatabaseManager` migrations live in `src/database/sql/migrations/` (v1:
students/courses/sections/classes/degrees/requirements/plans/chat),
`vector/embeddings.py` is the pluggable embedding seam, and chat-history
embeddings (`save_chat_history_embeddings`) are intentionally deferred until a
feature needs them (FC34 persistence is SQL-side). The §2 engine
(`CourseRecommendationValidator`, `DegreePlanGenerator`) is not built yet.

---

## 1. Core Academic Domain Models

### Class Name: `Student`
**Inheritance:** `None` (Base Entity)
**Attributes:**
- `student_id`: String
- `name`: String
- `current_major`: DegreeRequirement
- `concentration`: String (e.g., "Cybersecurity", "Artificial Intelligence")
- `career_interest`: String
- `completed_courses`: List<EnrollmentRecord>
- `current_schedule`: SemesterPlan
- `active_degree_plan`: DegreePlan
- `include_summer_sessions`: Boolean

**Functions:**
- `has_passed_course(course_id: String) -> Boolean` (Supports Req 4b)
- `get_completed_credit_hours() -> Integer`
- `get_current_gpa() -> Float`
- `update_major(new_major: DegreeRequirement, new_concentration: String) -> None` (Supports Req 5)
- `enroll_in_section(section: CourseSection) -> Boolean` (Supports Req 3 - Adding classes)
- `drop_section(section_id: String) -> Boolean` (Supports Req 3 - Dropping classes)

---

### Class Name: `Course`
**Inheritance:** `None` (Base Entity)
**Attributes:**
- `course_id`: String (e.g., "CSE 4392")
- `title`: String
- `description`: String (Used for semantic/RAG queries in Req 3)
- `credit_hours`: Integer
- `prerequisites`: List<String> (List of prerequisite `course_id`s)
- `corequisites`: List<String>
- `offered_terms`: List<String> (e.g., ["Fall", "Spring", "Summer"])

**Functions:**
- `get_prerequisites() -> List<String>`
- `is_offered_in_term(term: String) -> Boolean`
- `to_document_chunk() -> String` (Formats course info for vector embedding in Req 7 & 8)

---

### Class Name: `CourseSection`
**Inheritance:** `Course` (or holds a reference to `Course`)
**Attributes:**
- `section_id`: String
- `course_id`: String
- `semester_term`: String (e.g., "Fall 2026")
- `instructor`: String
- `meeting_days`: List<String> (e.g., ["Monday", "Wednesday"])
- `start_time`: Time
- `end_time`: Time
- `room_capacity`: Integer
- `enrolled_count`: Integer

**Functions:**
- `has_time_conflict(other_section: CourseSection) -> Boolean` (Supports Req 4d)
- `has_open_seats() -> Boolean`
- `get_schedule_string() -> String`

---

### Class Name: `EnrollmentRecord`
**Inheritance:** `None`
**Attributes:**
- `student_id`: String
- `course_id`: String
- `semester_taken`: String
- `grade`: String (e.g., "A", "B", "C", "F", "W", "In Progress")
- `status`: String (e.g., "Completed", "Enrolled", "Dropped")

**Functions:**
- `is_passing_grade() -> Boolean` (Supports Req 4b)

---

### Class Name: `DegreeRequirement`
**Inheritance:** `None`
**Attributes:**
- `degree_id`: String
- `major_name`: String (e.g., "BS in Computer Science", "BS in Software Engineering")
- `concentration_name`: String (e.g., "Cybersecurity", "Artificial Intelligence")
- `total_credits_required`: Integer (Supports Req 4f)
- `max_semester_credits`: Integer (Supports Req 4e, e.g., 18 hours)
- `core_courses`: List<String> (Course IDs)
- `concentration_courses`: List<String> (Course IDs)
- `elective_rules`: Map<String, Integer> (e.g., {"Technical Electives": 9, "General Ed": 12})

**Functions:**
- `is_course_applicable(course_id: String) -> Boolean` (Supports Req 4c)
- `get_remaining_requirements(completed_courses: List<EnrollmentRecord>) -> List<String>` (Supports Req 3)
- `validate_degree_completion(plan: DegreePlan) -> Boolean` (Supports Req 2)

---

## 2. Degree Planning & Validation Models
*(Note: As stated in Section 3 of the prompt, LLMs struggle with strict constraint satisfaction. These classes act as the deterministic engine that works alongside the LLM).*

### Class Name: `SemesterPlan`
**Inheritance:** `None`
**Attributes:**
- `term`: String (e.g., "Spring", "Summer", "Fall")
- `year`: Integer
- `planned_courses`: List<Course>
- `scheduled_sections`: List<CourseSection> (Used for immediate/current semesters)
- `max_credit_limit`: Integer

**Functions:**
- `get_total_credits() -> Integer`
- `add_course(course: Course) -> Boolean`
- `remove_course(course_id: String) -> Boolean`
- `has_schedule_conflicts() -> Boolean` (Supports Req 4d)

---

### Class Name: `DegreePlan`
**Inheritance:** `None`
**Attributes:**
- `plan_id`: String
- `student_id`: String
- `target_degree`: DegreeRequirement
- `semesters`: List<SemesterPlan>
- `includes_summer`: Boolean (Supports Req 2)
- `creation_date`: DateTime

**Functions:**
- `get_total_planned_credits() -> Integer` (Supports Req 4f)
- `get_execution_status(completed_records: List<EnrollmentRecord>) -> Float` (Supports Req 3)
- `add_semester(semester: SemesterPlan) -> None`
- `export_to_ readable_format() -> String`

---

### Class Name: `CourseRecommendationValidator`
**Inheritance:** `None`
**Attributes:**
- `sql_db`: SQLDatabaseManager

**Functions:**
- `verify_all_constraints(student: Student, course: Course, section: CourseSection, semester: SemesterPlan) -> ValidationResult` (Master check for Req 4)
- `check_prerequisites_met(student: Student, course: Course) -> Boolean` (Req 4a)
- `check_not_already_passed(student: Student, course: Course) -> Boolean` (Req 4b)
- `check_fulfills_degree_req(degree: DegreeRequirement, course: Course) -> Boolean` (Req 4c)
- `check_no_schedule_conflict(semester: SemesterPlan, candidate_section: CourseSection) -> Boolean` (Req 4d)
- `check_within_semester_credit_limit(semester: SemesterPlan, course: Course, max_limit: Integer) -> Boolean` (Req 4e)
- `check_within_total_degree_credits(student: Student, plan: DegreePlan, course: Course) -> Boolean` (Req 4f)

---

### Class Name: `DegreePlanGenerator`
**Inheritance:** `None`
**Attributes:**
- `validator`: CourseRecommendationValidator
- `course_catalog`: List<Course>

**Functions:**
- `generate_multi_year_plan(student: Student, target_degree: DegreeRequirement, include_summer: Boolean, max_credits_per_sem: Integer) -> DegreePlan` (Supports Req 2 & Req 6 follow-ups)
- `compare_plans(existing_plan: DegreePlan, new_plan: DegreePlan) -> PlanComparisonResult` (Supports Req 5c)
- `simulate_major_switch(student: Student, new_degree: DegreeRequirement) -> Dict` (Calculates lost credits, new timeline, pros/cons for Req 5a, 5b, 5c)

---

## 3. AI, LangChain, & Conversation Layer

### Class Name: `ConversationSession`
**Inheritance:** `None`
**Attributes:**
- `session_id`: String
- `student_id`: String
- `chat_history`: List<ChatMessage> (Supports Req 6 & 7)
- `context_state`: Dict (Tracks temporary states, e.g., "currently discussing switching major to AI", "max_classes_next_sem": 3)

**Functions:**
- `add_user_message(message: String) -> None`
- `add_ai_message(message: String) -> None`
- `update_context_state(key: String, value: Any) -> None` (Supports Req 6 follow-up turns)
- `get_formatted_history() -> String`

---

### Class Name: `AIAdvisorAgent`
**Inheritance:** `None` (Wraps LangChain Agent / Chain)
**Attributes:**
- `llm`: BaseLanguageModel (LangChain LLM instance)
- `memory`: ConversationBufferMemory (LangChain memory component)
- `sql_manager`: SQLDatabaseManager
- `vector_manager`: VectorDatabaseManager
- `plan_generator`: DegreePlanGenerator
- `validator`: CourseRecommendationValidator
- `tools`: List<Tool> (LangChain tools bridging the LLM to the deterministic functions above)

**Functions:**
- `process_query(student_id: String, user_input: String) -> String` (Main entry point)
- `classify_query_intent(user_input: String) -> String` (Routes between exact SQL query, semantic RAG query, or degree generation - Req 3)
- `handle_exact_query(query: String) -> String` (Uses SQL Agent/Tools for schedules, status - Req 3)
- `handle_semantic_query(query: String) -> String` (Uses Vector DB for course content, career alignment, major pros/cons - Req 3 & 5b)
- `handle_plan_generation_request(student: Student, parameters: Dict) -> String` (Calls `DegreePlanGenerator` and summarizes with LLM - Req 2 & 5c)

---

## 4. Database Management Layer (Req 7 & 8)

### Class Name: `DatabaseManager` (Abstract Base Class)
**Inheritance:** `ABC` (Abstract Base Class)
**Attributes:**
- `connection_string`: String
- `is_connected`: Boolean

**Functions:**
- `connect() -> Boolean`
- `disconnect() -> None`
- `execute_query(query: Any) -> Any`

---

### Class Name: `SQLDatabaseManager`
**Inheritance:** `DatabaseManager`
**Attributes:**
- `db_engine`: Engine (e.g., SQLite, PostgreSQL, MySQL)

**Functions:**
- `get_student_record(student_id: String) -> Student`
- `get_course_schedule(term: String, course_id: String) -> List<CourseSection>`
- `get_enrollment_history(student_id: String) -> List<EnrollmentRecord>`
- `save_degree_plan(plan: DegreePlan) -> Boolean`
- `update_student_enrollment(student_id: String, section_id: String, action: String) -> Boolean`

---

### Class Name: `VectorDatabaseManager`
**Inheritance:** `DatabaseManager`
**Attributes:**
- `vector_store`: VectorStore (e.g., Chroma, Pinecone)
- `embedding_model`: Embeddings (e.g., OpenAIEmbeddings, HuggingFaceEmbeddings)

**Functions:**
- `ingest_documents(documents: List<Document>) -> None` (Ingests course catalog, degree PDFs, advising guidelines)
- `similarity_search(query: String, k: Integer) -> List<Document>` (Supports semantic queries in Req 3 & 5)
- `save_chat_history_embeddings(session: ConversationSession) -> None` (Supports Req 7 advising history)

---

## 5. User Interface Layer (Req 1 & 3)

### Class Name: `AdvisorUI`
**Inheritance:** `None` (Can be subclassed into `WebUI`, `DesktopGUI`, or `CLI`)
**Attributes:**
- `advisor_agent`: AIAdvisorAgent
- `active_student`: Student
- `current_session`: ConversationSession

**Functions:**
- `render_chat_interface() -> None`
- `display_degree_plan(plan: DegreePlan) -> None`
- `display_plan_comparison(comparison: PlanComparisonResult) -> None` (Supports Req 5c)
- `open_inquiry_dialog_box(inquiry_type: String) -> Dict` (Supports Req 3 Note: dialog boxes for structured inquiries)
- `capture_prompt_query() -> String` (Supports Req 3 Note: free-text prompt queries)