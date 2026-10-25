# Functional Requirements: Academic AI Advisor

---

## 1. Degree Plan / Major (Specialty)

| ID | Title | Additional Notes |
| --- | --- | --- |
| **FC1** | Users shall be able to specify their major and specification | • A user can only have one major and one specialization<br>• Specializations are concentration tracks stored in the degree JSON (`concentrations`; BS CS: AI, Cybersecurity, Data Science, Game Development & Graphics; BS SE: AI, Cybersecurity, Cloud & Data Systems) plus an always-offered `General` (no track). A track's 9 credit hours replace the same number of technical-elective hours; unknown tracks are refused with the real options |
| **FC2** | Users shall be able to generate a degree plan based off their selected major and specification | |
| **FC3** | Users shall be able to edit an existing degree plan | |
| **FC4** | Users shall be able to view previous versions of any given degree plan | |
| **FC5** | Users should be able to revert to a previous version of a degree plan | |
| **FC6** | Users can view and generate multiple degree plans per major and specification combination | • Exactly one plan is active per student<br>• Any plan change makes the changed plan active by default: generating a plan (UI or assistant), saving an edit (FC3), or reverting a version (FC5); other plans stay on record and can be re-activated explicitly<br>• The profile follows the active plan: activating a plan (generate, edit, revert, "Make active") sets the student's major, concentration (FC1) and tracked degree (FC17) to the plan's, keeping history (FC7); the UI confirms "saved as your active plan" and names any profile change<br>• In chat, a plan for the student's current major/track generates immediately; a plan for a different major or concentration would change the account, so it becomes the FC23 change-major/concentration confirmation card (confirming regenerates the plan) |
| **FC7** | Users can view current and previous major / specialty combinations | |
| **FC25** | System shall generate multi-year degree plans as semester-by-semester roadmaps | • Roadmap covers all semesters required for degree completion [2]<br>• Supports optional summer sessions upon user request [2] |
| **FC26**  | System shall generate side-by-side plan comparisons when changing majors or concentrations | • Compares existing plan directly with the newly proposed plan [5]<br>• Outlines trade-offs, advantages, and disadvantages of the proposed change [5] |

---

## 2. Course Discovery

| ID | Title | Additional Notes |
| --- | --- | --- |
| **FC8** | Users can search for available courses by course name or instructor | |
| **FC9** | Users can submit natural language search queries to discover classes | Perform semantic search against course description text |
| **FC10** | Users can filter classes by department, semester offered | |
| **FC11** | Users can view class title, description, instructor, sections, credit hours, department, pre-requisites, co-requisites, and related degrees | |
| **FC12** | Users can view class sections on class detail pages. Sections include date times, days of the week and instructors | |
| **FC13** | Users can bookmark courses | |
| **FC14** | Users shall be able to add classes to their profile | All added classes will default to a Not taken state.<br>Added classes will be saved to users profile |

---

## 3. Degree Requirements

| ID | Title | Additional Notes |
| --- | --- | --- |
| **FC15** | Users can explore degrees offered across departments | |
| **FC16** | Users are only able to select degrees that are aligned to their major | |
| **FC17** | Users can only select one degree at a time | |
| **FC18** | Users shall be able to view all requirements for any given degree | |
| **FC19** | Users shall be able to track current progress towards only the selected degree | |

---

## 4. Class Management

| ID | Title | Additional Notes |
| --- | --- | --- |
| **FC20** | Users shall be able to remove classes from their accounts | |
| **FC21** | Users shall be able to change the status of classes added to their profile | • Not taken<br>• In Progress<br>• Taken / Passed / Failed |

---

## 5. Assistant & Advisory Engine

| ID | Title | Additional Notes |
| --- | --- | --- |
| **FC22** | Users shall be able to speak with an AI assistant to ask questions about degree plans, degrees, classes, professors, classes taken, degree progress and any other relevant data relating to classes | • The assistant reads the student's ACTIVE degree plan (FC6) from SQLite (FC33) — never Chroma; with no active plan it says so rather than describing a draft<br>• Course recommendations skip courses already on the active plan |
| **FC23** | With user approval, assistant shall be able to take actions on the users behalf | • Adding classes<br>• Changing class status<br>• Changing major<br>• Changing concentration — a confirmed major/concentration change also regenerates the degree plan for the new major/track via the engine (FC2), which becomes the active plan (FC6); the confirmation card states this up front<br>• Changing degrees<br>• Editing the active degree plan (add / remove / move a course between semesters — FC3) and making a generated plan active (FC6); engine-prechecked (FC30/FC32), saved as a new plan version (FC4) |
| **FC24** | Users shall be able to request an audit for ability to take a class, or request status regarding degree requirements | |
| **FC27** | System shall maintain conversation state across dialogue turns | • Enables contextual follow-up questions (e.g., "What if I take 3 classes next semester instead?") without repeating prior context [6] |
| **FC28** | Assistant shall engage users in multi-turn guidance for major/plan changes | • Interactively clarifies student needs before confirming major, concentration, or degree modifications [5]<br>• Clarifies only missing parameters: once an action is fully specified it goes straight to the FC23 confirmation card instead of a yes/no question, so a bare "yes" never has to be re-derived from history |
| **FC42** | Users shall be able to explore and brainstorm academic options with the assistant | • Open-ended questions ("what majors/concentrations exist?", "I like AI and security — what could I do?") are answered by an assistant that may call any **read-only** lookup (SQLite degrees/concentrations/requirements/courses/sections/records/active plan; Chroma course + catalog search) repeatedly, within a fixed budget (6 tool calls per turn), and may reason, compare, and give opinions — non-deterministic by design<br>• A short follow-up reply ("yes please") to the advisor's own offer continues the conversation with its history (FC27) instead of being treated as a new lookup<br>• Every course, degree, or concentration it names must come from a lookup result; course ids not in the catalog are removed from the answer, never presented as real<br>• Every real course id in the answer is run through `CourseRecommendationValidator` (FC29–FC32) and its checks are shown with the turn (FC39)<br>• It cannot change anything: actions still require the FC23 confirmation card |

---

## 6. Course Recommendation & Audit Safeguards

| ID | Title | Additional Notes |
| --- | --- | --- |
| **FC29** | System shall verify prerequisite satisfaction prior to recommending any course | • Ensures student has met all course prerequisites [4]<br>• Prerequisite edges are seeded from `data/prerequisites.json` (MOCK demo graph); plan generation pulls in a missing prerequisite and places it in an earlier semester |
| **FC30** | System shall prevent recommendation of previously passed courses | • Verifies student has not already completed/passed the course [4] |
| **FC31** | System shall verify schedule compatibility across course sections | • Detects and prevents day/time overlaps across selected section schedules [4] |
| **FC32** | System shall enforce credit hour maximum caps per semester and degree total | • Limits recommended credit hours to semester maximum limits [4]<br>• Ensures total credit hours do not exceed overall degree ceiling [4] |

---

## 7. Database Architecture, Interface & System Assumptions

| ID | Title | Additional Notes |
| --- | --- | --- |
| **FC33**  | System shall persist structured data in a SQL DBMS and unstructured data in a Vector DB | • SQL DB stores student records, course schedules, and enrollment info [6]<br>• Vector DB (Chroma, Pinecone, etc.) stores course descriptions, catalog embeddings, degree requirements [6] |
| **FC34** | System shall persist advising sessions and chat history in the database | • All chat logs and advising interactions saved across sessions [6, 7] |
| **FC35**  | System UI shall support prompt-based queries and structured dialog box inputs | • Accessible via Web UI, Desktop GUI, or CLI interface [1, 3] |
| **FC36** | System assumes pre-authenticated student sessions (Baseline Scope) | • Login/logout and security authentication rules are out of scope for assignment baseline [7] |
| **FC37** | System shall expose a REST API (FastAPI) between the client UI and the backend zones | • Router → service layering; agent, db managers, and pre-auth student (FC36) supplied by dependency injection<br>• Assistant-initiated actions require a confirmation flag in the request (FC23)<br>• Lookup misses return 404 `not_found` — never fabricated data |
| **FC38** | System shall be deployable and testable from a single Docker Compose command | • `docker compose up` builds and starts the API (FC37) and Web UI services; the LLM stays external and is configured through `ADVISOR_LLM_*` environment variables<br>• Seeds reload from `data/` on container startup (FC33); user-owned chat/plan data persists across container restarts (FC34)<br>• No authentication containers or secrets baked into images (FC36); lookups that come back empty surface as-is, never fabricated data |
| **FC39** | Assistant shall stream each turn: the deterministic checks as they run, then the answer text | • `POST /chat/messages/stream` returns newline-delimited JSON events: `check` (each FC29–FC32 validator result, plus plan-generation status), `token` (answer text), `done` (final reply + FC23 proposal), `error`<br>• Checks are emitted from the deterministic tool nodes, never by the LLM; check events always precede the answer tokens<br>• Same persistence (FC34) and FC23 confirm gating as `POST /chat/messages`; the non-streaming route remains<br>• The checks/steps that ran are stored with the advisor turn (`chat_messages.checks`, returned as `checks` by `GET /chat/messages`) |
| **FC40** | Users shall be able to export the open conversation as a Markdown file | • The chat drawer's **Export** button downloads `advisor-chat-<timestamp>.md` in the browser<br>• Every turn is included in order; each advisor turn lists the deterministic checks that ran with their status (✅ passed · ❌ failed · ❔ skipped) and reason, the data lookups, and any FC23 proposal awaiting confirmation<br>• Works for a freshly streamed turn and for a reloaded conversation (checks persist, FC34/FC39) |
| **FC41** | Users shall be able to delete a conversation from the chat history | • `DELETE /chat/sessions/{session_id}` → 204; removes the session, its messages and its pending actions (FC34 store)<br>• Unknown or another student's session → 404 `not_found`<br>• The history list shows a delete button per conversation (browser confirm first); deleting the open conversation falls back to the active/new session |
