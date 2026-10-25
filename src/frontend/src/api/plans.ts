/**
 * Degree-plan API service (FC1–FC7, FC19, FC25–FC26, FC29–FC32) — LIVE
 * implementation over the FastAPI plan endpoints. Plan generation, editing,
 * reverting, and comparison all come from the deterministic engine behind
 * the server (DegreePlanGenerator); nothing here computes constraint
 * verdicts client-side. Flow (agreed): generate → edit → make active.
 *
 *   getPlanOptions()          → GET  /plans/options (FC1 majors list)
 *   generatePlan(request)     → POST /plans/generate → PlanDetail (preview)
 *   listPlans()               → GET  /plans (FC6)
 *   getActivePlan()           → GET  /plans/active (null when nothing active)
 *   activatePlan(planId)      → PATCH /plans/{id}/activate
 *   savePlanDraft(...)        → PATCH /plans/{id} (FC3; engine-validated)
 *   reviewPlanDraft(semesters)→ POST /plans/review (FC29–FC32 verdicts)
 *   listPlanVersions(planId)  → GET  /plans/{id}/versions (FC4)
 *   revertPlan(planId, v)     → POST /plans/{id}/revert (FC5)
 *   compareProgramChange(r)   → POST /plans/compare (FC26, deterministic)
 *   confirmProgramChange(m,c) → PATCH /students/me/major + auto-generate (FC23-style gate: UI confirm dialog precedes this call)
 *   getCourseCatalog()        → GET  /courses (course metadata for chips)
 */

import { request, ApiError } from './client';
import type {
  ActivePlanData,
  CourseCatalog,
  GeneratePlanRequest,
  PlanDetail,
  PlanListItem,
  PlanOption,
  PlanReview,
  PlanVersionInfo,
  ProgramComparison,
  Semester,
} from './types';

export async function getPlanOptions(): Promise<{ majors: PlanOption[] }> {
  return await request<{ majors: PlanOption[] }>('/plans/options');
}

/** Generate a degree plan for a major + specialization (FC1, FC2, FC25).
    The generated plan becomes the ACTIVE plan (FC6) and the profile follows
    it; `profile_updated` reports what changed (null = profile already matched). */
export async function generatePlan(
  request_payload: GeneratePlanRequest & { maxCreditsPerSemester?: number },
): Promise<PlanDetail> {
  return await request<PlanDetail>('/plans/generate', {
    method: 'POST',
    body: {
      major_name: request_payload.majorName,
      concentration: request_payload.concentration || 'General',
      include_summer: Boolean(request_payload.includeSummer),
      ...(request_payload.maxCreditsPerSemester
        ? { max_credits_per_semester: request_payload.maxCreditsPerSemester }
        : {}),
    },
  });
}

export async function listPlans(): Promise<PlanListItem[]> {
  const body = await request<{ results: PlanListItem[] }>('/plans');
  return body.results;
}

/** One plan detail (FC3 view) by id — used when no plan is active and the
    timeline falls back to the most recently generated one. */
export async function getPlanById(planId: string): Promise<PlanDetail> {
  return await request<PlanDetail>(`/plans/${planId}`);
}

/** The student's active plan (FC6) — null when nothing is active (404).
    `progress` (FC19 counting) hydrates the header numbers when given. */
export async function getActivePlan(
  progress: DegreeProgressSummary | null = null,
): Promise<ActivePlanData | null> {
  try {
    const detail = await request<PlanDetail>('/plans/active');
    return planDetailToActive(detail, progress);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export async function activatePlan(planId: string): Promise<PlanDetail> {
  return await request<PlanDetail>(`/plans/${planId}/activate`, { method: 'PATCH' });
}

/** Save an edited plan (FC3) — the server validates the draft through the
    engine and versions it (FC4); 422 = blocking safeguard violation. */
export async function savePlanDraft(
  planId: string,
  semesters: Array<Pick<Semester, 'id' | 'term' | 'year' | 'courseIds' | 'credits'>>,
  includesSummer?: boolean,
): Promise<PlanDetail> {
  return await request<PlanDetail>(`/plans/${planId}`, {
    method: 'PATCH',
    body: {
      semesters: semesters.map((s) => ({
        term: s.term, year: s.year, courses: s.courseIds, credits: s.credits,
      })),
      ...(includesSummer === undefined ? {} : { includes_summer: includesSummer }),
    },
  });
}

/** FC29–FC32 verdicts for an unsaved draft (engine-side via POST /plans/review). */
export async function reviewPlanDraft(
  semesters: Array<Pick<Semester, 'id' | 'term' | 'year' | 'courseIds' | 'credits'>>,
): Promise<PlanReview> {
  const body = await request<{
    status: 'ok' | 'issues';
    issues: string[];
    semester_issues: Record<string, Array<{ code: string; course: string | null; text: string; severity: string }>>;
  }>('/plans/review', {
    method: 'POST',
    body: {
      semesters: semesters.map((s) => ({
        term: s.term, year: s.year, courses: s.courseIds, credits: s.credits,
      })),
    },
  });
  const semesterIssues: PlanReview['semesterIssues'] = {};
  for (const [key, issues] of Object.entries(body.semester_issues)) {
    semesterIssues[key] = issues.map((issue) => ({
      course: issue.course,
      text: issue.text,
      code: issue.code,
      severity: issue.severity === 'blocking' ? 'blocking' : 'warning',
    }));
  }
  return { status: body.status, issues: body.issues, semesterIssues };
}

export async function listPlanVersions(planId: string): Promise<PlanVersionInfo[]> {
  const body = await request<{ versions: PlanVersionInfo[] }>(`/plans/${planId}/versions`);
  return body.versions;
}

export async function revertPlan(planId: string, versionId: string): Promise<PlanDetail> {
  return await request<PlanDetail>(`/plans/${planId}/revert`, {
    method: 'POST',
    body: { version_id: versionId },
  });
}

/** Side-by-side comparison for a prospective major/concentration change
    (FC26) — rows and trade-off notes produced by the deterministic engine. */
export async function compareProgramChange({
  existingPlanId,
  majorName,
  concentration,
}: {
  existingPlanId: string;
  majorName: string;
  concentration?: string;
}): Promise<ProgramComparison> {
  const body = await request<{
    retained_courses: string[];
    lost_courses: string[];
    added_courses: string[];
    retained_hours: number | null;
    lost_hours: number | null;
    added_hours: number | null;
    graduation_estimate: string | null;
    advantages: string[];
    disadvantages: string[];
    target_major: string;
    target_concentration: string;
  }>('/plans/compare', {
    method: 'POST',
    body: {
      existing_plan_id: existingPlanId,
      target_major: majorName,
      target_concentration: concentration || 'General',
    },
  });
  const existingHours = (body.retained_hours ?? 0) + (body.lost_hours ?? 0);
  return {
    current: {
      degree: '(current plan)',
      concentration: '—',
      hoursThatCount: `${body.retained_hours ?? 0} of ${existingHours} planned hours carry over`,
      hoursRemaining: `${body.lost_hours ?? 0} hours would no longer count`,
      graduation: 'see current plan',
    },
    proposed: {
      degree: body.target_major,
      concentration: body.target_concentration,
      hoursThatCount: `${body.retained_hours ?? 0} planned hours carry over`,
      hoursRemaining: `${body.added_hours ?? 0} new hours required`,
      graduation: body.graduation_estimate ?? 'unknown timeline',
    },
    // FC26 — outlined trade-offs (engine-generated, LLM-free)
    notes: [...body.advantages, ...body.disadvantages],
  };
}

/** Apply an explicitly confirmed program change (FC23-style gate: the UI's
    ConfirmDialog runs BEFORE this). Applies the major/concentration (FC1,
    FC7 history) and auto-generates a fresh plan for the new degree — the
    plan is inactive until the student makes it active (agreed flow). */
export async function confirmProgramChange(
  majorName: string,
  concentration: string,
): Promise<{ applied: boolean; planId?: string | null }> {
  await request('/students/me/major', {
    method: 'PATCH',
    body: { major_name: majorName, concentration: concentration || 'General' },
  });
  try {
    const plan = await generatePlan({ majorName, concentration: concentration || 'General' });
    return { applied: true, planId: plan.plan_id };
  } catch {
    // Profile change applied; a fresh plan needs the student to generate it.
    return { applied: true };
  }
  return { applied: true };
}

/** Course metadata lookup (id → record) used to render course chips from
    course-id lists (titles/credits are SQLite truth, FC33; meetings are not
    included — sections live behind the courses detail endpoint, FC12). */
export async function getCourseCatalog(): Promise<CourseCatalog> {
  const body = await request<{
    results: Array<{ course_id: string; title: string; credit_hours: number | null }>;
  }>('/courses');
  const catalog: CourseCatalog = {};
  for (const course of body.results) {
    catalog[course.course_id] = {
      id: course.course_id,
      title: course.title,
      creditHours: course.credit_hours ?? 0,
    };
  }
  return catalog;
}

/* ------------------------------------------------------------ mapping */

export interface DegreeProgressSummary {
  completionPercent: number | null;
  completedHours: number | null;
  inProgressHours: number | null;
  totalCreditsRequired: number | null;
}

/** Map a server PlanDetail into the ActivePlanData shape the pages render
    (semester statuses derived from the plan's own term order — the first
    semester is the in-progress current term the engine seeded). */
export function planDetailToActive(
  detail: PlanDetail,
  progress: DegreeProgressSummary | null,
): ActivePlanData {
  const semesters: Semester[] = detail.semesters.map((s, index) => ({
    id: `${s.term.toLowerCase()}-${s.year}`,
    term: s.term,
    year: s.year,
    status: index === 0 ? ('in-progress' as const) : ('planned' as const),
    courseIds: [...s.courses],
    credits: s.credits ?? 0,
  }));
  const plannedCredits = semesters
    .slice(1)
    .reduce((sum, s) => sum + s.credits, 0);
  return {
    plan_id: detail.plan_id,
    student_id: detail.student_id,
    program: {
      majorName: detail.target_major,
      concentration: detail.concentration || '—',
      catalogYear: '—', // not modeled in the seed data — honest unknown
    },
    progress: {
      completed: progress?.completedHours ?? 0,
      inProgress: progress?.inProgressHours ?? 0,
      planned: plannedCredits,
      total: progress?.totalCreditsRequired
        ?? semesters.reduce((sum, s) => sum + s.credits, 0),
    },
    currentTerm: semesters[0] ? `${semesters[0].term} ${semesters[0].year}` : '',
    onTrackNote: progress?.completionPercent != null
      ? `${progress.completionPercent.toFixed(0)}% of the selected degree's requirements matched`
      : 'Plan generated by the deterministic engine — now your active plan',
    semesters,
    check: { status: 'ok', issues: [], semesterIssues: {} },
  };
}