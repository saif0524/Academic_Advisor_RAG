/**
 * Degree-plan API service (FC1, FC2, FC25) — MOCK implementation.
 *
 * This file stands in for the FastAPI plan endpoints (src/server/routers/plans.py,
 * proposed FC-new-rest-api — every plan route returns 501 `not_wired` today).
 * The request/response shapes mirror src/server/schemas/plans.py exactly:
 *
 *   getPlanOptions()                      → future GET /plans/options
 *   generatePlan(GeneratePlanRequest)     → future POST /plans/generate → PlanDetail
 *   getCourseCatalog()                    → future GET /courses (course metadata)
 *
 * When the backend is wired, replace the function bodies with
 * `request(...)` calls from ./client.js — callers keep the same signatures.
 *
 * Grounding notes:
 * - Course IDs and titles are REAL seed data from data/course-desc.jsonl.
 * - Credit hours, per-semester caps, and degree totals are MOCK metadata
 *   (in the real system they live in SQLite, FC33).
 * - Roadmaps cover CSE coursework only; the real DegreePlanGenerator
 *   (FC2/FC25, docs/2026-10-18-ai-advisor-domain-model.md §2) adds gen-ed,
 *   math, and physics work to reach the full degree total.
 * - The builder below is plain deterministic code — a mock of the engine's
 *   role. No LLM is involved, matching the deterministic-engine-first rule.
 * - There is no FC23 confirmation gate here: generating a plan is a preview
 *   and does not modify the student's record.
 */

const MOCK_LATENCY_MS = 700;

/**
 * Mock course catalog for the roadmap. IDs/titles mirror real seed records;
 * `creditHours` is mock metadata (SQLite owns it in the real system, FC33).
 */
const CATALOG = {
  1105: { id: '1105', title: 'INTRODUCTION TO COMPUTER SCIENCE AND ENGINEERING.', creditHours: 2 },
  1106: { id: '1106', title: 'INTRODUCTION TO COMPUTER SCIENCE AND ENGINEERING.', creditHours: 1 },
  1301: { id: '1301', title: 'COMPUTER LITERACY', creditHours: 3 },
  1310: { id: '1310', title: 'INTRODUCTION TO COMPUTERS & PROGRAMMING', creditHours: 3 },
  1311: { id: '1311', title: 'INTRODUCTION TO PROGRAMMING FOR ENGINEERS', creditHours: 3 },
  1325: { id: '1325', title: 'OBJECT-ORIENTED PROGRAMMING', creditHours: 3 },
  2100: { id: '2100', title: 'PRACTICAL COMPUTER HARDWARE/SOFTWARE SYSTEMS.', creditHours: 2 },
  2312: { id: '2312', title: 'COMPUTER ORGANIZATION & ASSEMBLY LANGUAGE PROGRAMMING', creditHours: 4 },
  2315: { id: '2315', title: 'DISCRETE STRUCTURES', creditHours: 3 },
  2440: { id: '2440', title: 'CIRCUIT ANALYSIS', creditHours: 3 },
  2441: { id: '2441', title: 'DIGITAL LOGIC DESIGN I', creditHours: 3 },
  3302: { id: '3302', title: 'PROGRAMMING LANGUAGES', creditHours: 3 },
  3310: { id: '3310', title: 'FUNDAMENTALS OF SOFTWARE ENGINEERING', creditHours: 3 },
  3311: { id: '3311', title: 'OBJECT-ORIENTED SOFTWARE ENGINEERING', creditHours: 3 },
  3314: { id: '3314', title: 'PROFESSIONAL PRACTICES', creditHours: 1 },
  3315: { id: '3315', title: 'THEORETICAL CONCEPTS IN COMPUTER SCIENCE AND ENGINEERING', creditHours: 3 },
  3318: { id: '3318', title: 'ALGORITHMS & DATA STRUCTURES', creditHours: 3 },
  3320: { id: '3320', title: 'OPERATING SYSTEMS', creditHours: 3 },
  3330: { id: '3330', title: 'DATABASE SYSTEMS AND FILE STRUCTURES', creditHours: 3 },
  3340: { id: '3340', title: 'INTRODUCTION TO HUMAN COMPUTER INTERACTION', creditHours: 3 },
  3341: { id: '3341', title: 'DIGITAL LOGIC DESIGN II', creditHours: 3 },
  3380: { id: '3380', title: 'LINEAR ALGEBRA FOR CSE', creditHours: 3 },
  3442: { id: '3442', title: 'EMBEDDED SYSTEMS I', creditHours: 3 },
  4308: { id: '4308', title: 'ARTIFICIAL INTELLIGENCE', creditHours: 3 },
  4309: { id: '4309', title: 'FUNDAMENTALS OF MACHINE LEARNING', creditHours: 3 },
  4311: { id: '4311', title: 'NEURAL NETWORKS AND DEEP LEARNING', creditHours: 3 },
  4316: { id: '4316', title: 'COMPUTER SYSTEM DESIGN PROJECT I', creditHours: 3 },
  4317: { id: '4317', title: 'COMPUTER SYSTEM DESIGN PROJECT II', creditHours: 3 },
  4321: { id: '4321', title: 'SOFTWARE TESTING & MAINTENANCE', creditHours: 3 },
  4322: { id: '4322', title: 'SOFTWARE PROJECT MANAGEMENT', creditHours: 3 },
  4361: { id: '4361', title: 'SOFTWARE DESIGN PATTERNS', creditHours: 3 },
  4380: { id: '4380', title: 'INFORMATION SECURITY', creditHours: 3 },
  4381: { id: '4381', title: 'INFORMATION SECURITY II', creditHours: 3 },
  4382: { id: '4382', title: 'SECURE PROGRAMMING', creditHours: 3 },
  4392: { id: '4392', title: 'SPECIAL TOPICS', creditHours: 3 },
};

/** Plan options the future backend derives from degree data (FC1, FC15–FC16). */
const PLAN_OPTIONS = {
  majors: [
    {
      name: 'BS in Computer Science',
      concentrations: ['Cybersecurity', 'Artificial Intelligence'],
    },
    {
      name: 'BS in Software Engineering',
      concentrations: ['Cybersecurity', 'Artificial Intelligence'],
    },
  ],
};

/**
 * Deterministic roadmap sequences, one entry per semester. `[E]` marks the
 * slots where concentration electives (three per degree) are injected by
 * buildPlan. Each semester stays under the degree's per-semester credit cap
 * (mock cap: 15, FC32) so the rendered plan never shows output the real
 * engine could not produce.
 */
const ROADMAPS = {
  'BS in Computer Science': [
    { term: 'Fall', year: 2026, summer: false, courseIds: ['1105', '1311', '2440'] },
    { term: 'Spring', year: 2027, summer: false, courseIds: ['1106', '1325', '2315'] },
    { term: 'Summer', year: 2027, summer: true, courseIds: ['1301', '3314'] },
    { term: 'Fall', year: 2027, summer: false, courseIds: ['2312', '2441', '3380'] },
    { term: 'Spring', year: 2028, summer: false, courseIds: ['3315', '3318', '3340'] },
    { term: 'Fall', year: 2028, summer: false, courseIds: ['3302', '3320', '3330'] },
    { term: 'Spring', year: 2029, summer: false, courseIds: ['[E]', '3341', '3442'] },
    { term: 'Fall', year: 2029, summer: false, courseIds: ['[E]', '[E]', '4316'] },
    { term: 'Spring', year: 2030, summer: false, courseIds: ['4317', '4392'] },
  ],
  'BS in Software Engineering': [
    { term: 'Fall', year: 2026, summer: false, courseIds: ['1105', '1310', '1301'] },
    { term: 'Spring', year: 2027, summer: false, courseIds: ['1106', '1325', '2315', '2100'] },
    { term: 'Summer', year: 2027, summer: true, courseIds: ['2441', '3314'] },
    { term: 'Fall', year: 2027, summer: false, courseIds: ['2312', '3310', '3380'] },
    { term: 'Spring', year: 2028, summer: false, courseIds: ['2440', '3311', '3340'] },
    { term: 'Fall', year: 2028, summer: false, courseIds: ['3318', '3320', '4321'] },
    { term: 'Spring', year: 2029, summer: false, courseIds: ['[E]', '4361', '4322'] },
    { term: 'Fall', year: 2029, summer: false, courseIds: ['[E]', '[E]', '3330'] },
    { term: 'Spring', year: 2030, summer: false, courseIds: ['4316', '4317'] },
  ],
};

/** Concentration elective pools (three courses each — real seed courses). */
const CONCENTRATION_ELECTIVES = {
  'Artificial Intelligence': ['4308', '4309', '4311'],
  Cybersecurity: ['4380', '4382', '4381'],
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Deterministic roadmap builder — the mock of `DegreePlanGenerator.
 * generate_multi_year_plan` (FC2, FC25): plain code, no LLM. Semester-by
 * -semester layout, optional summer sessions (kept only when requested), and
 * concentration electives injected into the `[E]` slots. The elective cursor
 * advances across semesters so each elective is used exactly once. Unknown
 * major/concentration → null, so callers render an explicit not-found error
 * instead of a silently degraded plan.
 */
function buildPlan({ majorName, concentration, includeSummer = false }) {
  const sequence = ROADMAPS[majorName];
  const isValidPair = PLAN_OPTIONS.majors.some(
    (option) => option.name === majorName && option.concentrations.includes(concentration),
  );
  if (!sequence || !isValidPair) return null;
  const electives = CONCENTRATION_ELECTIVES[concentration] ?? [];
  let electiveIndex = 0;
  const semesters = [];
  for (const entry of sequence) {
    if (entry.summer && !includeSummer) continue; // optional summer sessions (FC25)
    let consumed = 0;
    const courses = entry.courseIds
      .map((id) => {
        if (id !== '[E]') return id;
        const picked = electives[electiveIndex + consumed];
        if (picked === undefined) return null; // pool dry → slot dropped, nothing invented
        consumed += 1;
        return picked;
      })
      .filter((id) => id !== null);
    electiveIndex += consumed;
    if (courses.length === 0) continue; // never render an empty semester
    const credits = courses.reduce((sum, id) => sum + (CATALOG[id]?.creditHours ?? 0), 0);
    semesters.push({ term: entry.term, year: entry.year, courses, credits });
  }
  return {
    plan_id: 'mock-plan-0001',
    student_id: 'stu-0001', // pre-authenticated session placeholder (FC36)
    target_major: majorName,
    concentration,
    includes_summer: includeSummer,
    semester_count: semesters.length,
    created_at: new Date().toISOString(),
    semesters,
  };
}

/**
 * Fetch the generate-plan form inputs (FC1): majors and their concentrations.
 * @returns {Promise<{ majors: Array<{ name: string, concentrations: string[] }> }>}
 */
export async function getPlanOptions() {
  await sleep(MOCK_LATENCY_MS);
  return PLAN_OPTIONS;
}

/**
 * Generate a degree plan for a major + specialization (FC1, FC2, FC25).
 * @param {{ majorName: string, concentration: string, includeSummer?: boolean }} request
 *   — mirrors GeneratePlanRequest (src/server/schemas/plans.py).
 * @returns {Promise<object>} PlanDetail-shaped plan: summary fields plus the
 *   semester-by-semester roadmap (FC25). Resolves null for an unknown major.
 */
export async function generatePlan(request) {
  await sleep(MOCK_LATENCY_MS);
  return buildPlan(request);
}

/**
 * Course metadata lookup (id → { id, title, creditHours }) used to render
 * course chips from the plan's course-id list. Real implementation uses the
 * courses endpoints (FC11 — titles come from SQLite/Chroma, FC33).
 * @returns {Promise<Record<string, { id: string, title: string, creditHours: number }>>}
 */
export async function getCourseCatalog() {
  await sleep(MOCK_LATENCY_MS);
  return CATALOG;
}