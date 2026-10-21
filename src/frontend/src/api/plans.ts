/**
 * Degree-plan API service (FC1, FC2, FC3, FC7, FC19, FC25, FC26) — MOCK
 * implementation standing in for the FastAPI plan endpoints
 * (src/server/routers/plans.py, proposed FC-new-rest-api — plan routes
 * return 501 `not_wired` today). Request/response shapes mirror
 * src/server/schemas/plans.py:
 *
 *   getPlanOptions()        → future GET /plans/options
 *   generatePlan(request)   → future POST /plans/generate → PlanDetail
 *   getActivePlan()         → future GET /plans/active
 *   reviewPlanDraft(sems)   → future POST /plans/review (engine verdicts)
 *   savePlanDraft()         → future POST /plans/{id}/save
 *   compareProgramChange(r) → future POST /plans/compare (FC26)
 *   confirmProgramChange()  → future PATCH /students/me/degree (FC23 gate)
 *   getCourseCatalog()      → future GET /courses (course metadata)
 *
 * When the backend is wired, replace the function bodies with
 * `request(...)` calls from ./client — callers keep the same signatures.
 *
 * Grounding rules:
 * - Course ids/titles come from api/catalog (real seed records,
 *   data/course-desc.jsonl); credit hours and degree totals are MOCK
 *   metadata (SQLite owns them, FC33).
 * - Roadmaps cover CSE coursework only; the real DegreePlanGenerator
 *   (FC2/FC25, docs/planning/2026-10-18-ai-advisor-domain-model.md §2)
 *   adds gen-ed, math, and physics work to reach the degree total.
 * - The builders below are plain deterministic code — mocks of the engine's
 *   role (FC29–FC32 verdict display included). No LLM is involved, matching
 *   the deterministic-engine-first rule.
 * - Generating/generating-comparing are previews (no record changes), so no
 *   FC23 gate; confirmProgramChange is the gate the UI calls only after an
 *   explicit confirmation dialog.
 */

import { COURSES as CATALOG, PREREQ_FIXTURE, STUDENT_PROGRESS, CREDIT_CAP } from './catalog';
import type {
  GeneratePlanRequest,
  PlanDetail,
  PlanIssue,
  PlanOption,
  PlanReview,
  ProgramComparison,
  Semester,
  ActivePlanData,
  CourseCatalog,
} from './types';

const MOCK_LATENCY_MS = 700;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** Plan options the future backend derives from degree data (FC1, FC15–FC16). */
const PLAN_OPTIONS: { majors: PlanOption[] } = {
  majors: [
    { name: 'BS in Computer Science', concentrations: ['Cybersecurity', 'Artificial Intelligence'] },
    { name: 'BS in Software Engineering', concentrations: ['Cybersecurity', 'Artificial Intelligence'] },
  ],
};

/**
 * Deterministic roadmap sequences (plain-code mock of the FC2/FC25 engine).
 * `[E]` marks slots where concentration electives are injected by buildPlan;
 * keep every semester under the per-semester credit cap (mock cap: 15, FC32)
 * so no rendered output exceeds what the real engine could produce.
 */
const ROADMAPS: Record<string, Array<{ term: string; year: number; summer: boolean; courseIds: string[] }>> = {
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
const CONCENTRATION_ELECTIVES: Record<string, string[]> = {
  'Artificial Intelligence': ['4308', '4309', '4311'],
  Cybersecurity: ['4380', '4382', '4381'],
};

/**
 * Deterministic roadmap builder — the mock of `DegreePlanGenerator.
 * generate_multi_year_plan` (FC2, FC25): plain code, no LLM. Semester-by
 * -semester layout, optional summer sessions (kept only when requested), and
 * concentration electives injected into the `[E]` slots. Unknown
 * major/concentration → null, so callers render an explicit not-found error
 * instead of a silently degraded plan.
 */
function buildPlan({ majorName, concentration, includeSummer = false }: GeneratePlanRequest): PlanDetail | null {
  const sequence = ROADMAPS[majorName];
  const isValidPair = PLAN_OPTIONS.majors.some(
    (option) => option.name === majorName && option.concentrations.includes(concentration),
  );
  if (!sequence || !isValidPair) return null;
  const electives = CONCENTRATION_ELECTIVES[concentration] ?? [];
  let electiveIndex = 0;
  const semesters: PlanDetail['semesters'] = [];
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
      .filter((id): id is string => id !== null);
    electiveIndex += consumed;
    if (courses.length === 0) continue; // never render an empty semester
    const credits = courses.reduce((sum, id) => sum + (CATALOG[id]?.creditHours ?? 0), 0);
    semesters.push({ term: entry.term, year: entry.year, courses, credits });
  }
  return {
    plan_id: 'mock-plan-0001',
    student_id: STUDENT_PROGRESS.studentId, // pre-authenticated session placeholder (FC36)
    target_major: majorName,
    concentration,
    includes_summer: includeSummer,
    semester_count: semesters.length,
    created_at: new Date().toISOString(),
    semesters,
  };
}

/* ─── Active plan, draft review, and program-change services ───────────────
   Wireframe surfaces 01/02/03/05. All verdict computation below is plain
   deterministic code standing in for CourseRecommendationValidator (FC29–
   FC32) — never the LLM. */

const mkSemester = (id: string, term: string, year: number, status: Semester['status'], courseIds: string[]): Semester => ({
  id,
  term,
  year,
  status,
  courseIds,
  credits: courseIds.reduce((sum, cid) => sum + (CATALOG[cid]?.creditHours ?? 0), 0),
});

/** Active plan fixture (CSE coursework only — the engine adds gen-ed hours,
    which is why the planned count exceeds the visible CSE semesters). */
const ACTIVE_PLAN: ActivePlanData = {
  plan_id: 'plan-0001',
  student_id: STUDENT_PROGRESS.studentId, // pre-authenticated session (FC36)
  program: { majorName: 'BS in Computer Science', concentration: 'Cybersecurity', catalogYear: '2024-2025' },
  progress: { completed: 66, inProgress: 12, planned: 42, total: 120 },
  currentTerm: 'Fall 2026',
  onTrackNote: 'On track — graduate Spring 2028',
  semesters: [
    mkSemester('f26', 'Fall', 2026, 'in-progress', ['3310', '3320', '3318', '3380']),
    mkSemester('s27', 'Spring', 2027, 'planned', ['4380', '4382', '3330', '3315']),
    mkSemester('su27', 'Summer', 2027, 'optional', []),
    mkSemester('f27', 'Fall', 2027, 'planned', ['4316', '4381', '4308', '4321']),
    mkSemester('s28', 'Spring', 2028, 'planned', ['4317', '3341', '4392', '3340']),
  ],
  // `check` is attached by getActivePlan below (mirrors the engine round-trip).
  check: { status: 'ok', issues: [], semesterIssues: {} },
};

/**
 * Deterministic draft review — the UI-mock of the validator verdicts the
 * renderer displays (FC29 prerequisites, FC32 per-semester cap). Prereq
 * satisfaction counts earlier *planned* semesters the same way the engine's
 * plan view does; in-progress courses count as satisfied in the banner but
 * surface as "in progress" warnings on candidate lists (courses.ts).
 */
export function reviewPlanDraft(semesters: Array<Pick<Semester, 'id' | 'term' | 'year' | 'courseIds' | 'credits'>>): PlanReview {
  const issues: string[] = [];
  const semesterIssues: Record<string, PlanIssue[]> = {};
  const satisfiedSoFar = new Set<string>([
    ...STUDENT_PROGRESS.completedCourseIds,
    ...STUDENT_PROGRESS.inProgressCourseIds,
  ]);
  for (const semester of semesters) {
    const semIssues: PlanIssue[] = [];
    // FC32 — per-semester credit cap.
    if ((semester.credits ?? 0) > CREDIT_CAP) {
      const capText = `${semester.term} ${semester.year} exceeds the ${CREDIT_CAP}-hour semester cap`;
      semIssues.push({ course: null, text: capText });
      issues.push(capText);
    }
    for (const courseId of semester.courseIds ?? []) {
      for (const prereqId of PREREQ_FIXTURE[courseId] ?? []) {
        // FC29 — prerequisite satisfaction in an earlier semester.
        if (!satisfiedSoFar.has(prereqId)) {
          const text = `CSE ${courseId} needs CSE ${prereqId} in an earlier semester`;
          semIssues.push({ course: courseId, text });
          issues.push(text);
        }
      }
    }
    semesterIssues[semester.id] = semIssues;
    for (const courseId of semester.courseIds ?? []) satisfiedSoFar.add(courseId);
  }
  return { status: issues.length === 0 ? 'ok' : 'issues', issues, semesterIssues };
}

/**
 * The student's active degree plan (FC1/FC7/FC19/FC25) with the current
 * engine verdict attached (FC29–FC32 display fields). Resolves null when no
 * plan is on record — callers render an explicit empty state; nothing is
 * invented here.
 */
export async function getActivePlan(): Promise<ActivePlanData | null> {
  await sleep(MOCK_LATENCY_MS);
  const plan: ActivePlanData = { ...ACTIVE_PLAN, semesters: ACTIVE_PLAN.semesters.map((s) => ({ ...s })) };
  return { ...plan, check: reviewPlanDraft(plan.semesters) };
}

/** Save an edited plan (FC3). Mock of the save endpoint. */
export async function savePlanDraft(): Promise<{ saved: boolean; savedAt: string }> {
  await sleep(MOCK_LATENCY_MS);
  return { saved: true, savedAt: new Date().toISOString() };
}

/**
 * Side-by-side comparison for a prospective major/concentration change
 * (FC26) — rows and trade-off notes as the domain model's
 * PlanComparisonResult outlines. Pair validity mirrors PLAN_OPTIONS (FC1).
 * Resolves null for invalid pairs — callers render an explicit not-found.
 */
export async function compareProgramChange({ majorName, concentration }: GeneratePlanRequest): Promise<ProgramComparison | null> {
  await sleep(MOCK_LATENCY_MS);
  const validPair = PLAN_OPTIONS.majors.some(
    (option) => option.name === majorName && option.concentrations.includes(concentration),
  );
  if (!validPair) return null;
  return {
    current: {
      degree: ACTIVE_PLAN.program.majorName,
      concentration: ACTIVE_PLAN.program.concentration,
      hoursThatCount: '81 of 81',
      hoursRemaining: '39',
      graduation: 'Spring 2028',
    },
    proposed: {
      degree: majorName,
      concentration,
      hoursThatCount: '72 of 81',
      hoursRemaining: '48',
      graduation: 'Fall 2028',
    },
    // FC26 — outlined trade-offs (advising narrative from the degree audit).
    notes: [
      'Estimates from your degree audit — the advisor walks through pros and cons before you commit.',
      'Two CSE concentration courses would no longer count toward the new degree.',
      'CSE 4380 stays in Spring 2027 either way — CSE 4381 later in the plan needs it in an earlier semester.',
    ],
  };
}

/**
 * Apply an explicitly confirmed program change (FC23). The UI must show and
 * receive confirmation before calling this — mock resolves as applied.
 */
export async function confirmProgramChange(): Promise<{ applied: boolean }> {
  await sleep(MOCK_LATENCY_MS);
  return { applied: true };
}

/** Fetch the generate-plan form inputs (FC1): majors and their concentrations. */
export async function getPlanOptions(): Promise<{ majors: PlanOption[] }> {
  await sleep(MOCK_LATENCY_MS);
  return PLAN_OPTIONS;
}

/** Generate a degree plan for a major + specialization (FC1, FC2, FC25).
    Resolves null for an unknown major/concentration pair (explicit empty). */
export async function generatePlan(request: GeneratePlanRequest): Promise<PlanDetail | null> {
  await sleep(MOCK_LATENCY_MS);
  return buildPlan(request);
}

/** Course metadata lookup (id → record) used to render course chips from
    course-id lists. Real implementation uses the courses endpoints (FC11 —
    titles come from SQLite/Chroma, FC33). */
export async function getCourseCatalog(): Promise<CourseCatalog> {
  await sleep(MOCK_LATENCY_MS);
  return CATALOG;
}