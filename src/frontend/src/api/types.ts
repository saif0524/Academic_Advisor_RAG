/**
 * Shared domain-shape types for the frontend mock api seams (typed DTOs).
 * These mirror the future FastAPI Pydantic contracts (src/server/schemas/*,
 * proposed FC-new-rest-api) — hand-written until OpenAPI codegen lands.
 * Components import these with `import type` only (data, never functions).
 */

/* ─── Course catalog / discovery (FC8–FC12, FC33) ─────────────────────── */

export interface CourseRecord {
  id: string;
  title: string; // seed-corpus casing (uppercase); components title-case for display
  creditHours: number;
  description?: string;
}

export type CourseCatalog = Record<string, CourseRecord>;

/* Verdict badge variants mirror shared/Badge — kept structural so api and
   UI stay in sync without a shared-layer import. */
export type VerdictVariant = 'neutral' | 'primary' | 'info' | 'success' | 'warning' | 'danger';

export interface CourseFlag {
  label: string;
  variant: VerdictVariant;
}

export interface CourseResult {
  id: string;
  title: string;
  creditHours: number;
  meeting: string | null;
  description: string;
  term: string | null;
  flags: CourseFlag[];
}

export interface CourseAnswer {
  text: string;
  matchCount: number;
}

export interface SearchResponse {
  answer: CourseAnswer | null;
  courses: CourseResult[];
}

export interface CourseSuggestion {
  id: string;
  title: string;
  creditHours: number;
  meeting: string | null;
  badge: string;
  badgeVariant: VerdictVariant;
  conflict: string | null;
}

export interface CoursePrereqStatus {
  id: string;
  title: string | null;
  status: 'met' | 'in-progress' | 'missing'; // mock of FC29 verdicts
}

export interface CourseDetail {
  id: string;
  title: string;
  description: string;
  creditHours: number;
  meeting: string | null;
  prereqs: CoursePrereqStatus[];
}

/* ─── Degree plans (FC1–FC7, FC19, FC25–FC26, FC29–FC32) ──────────────── */

export type SemesterStatus = 'completed' | 'in-progress' | 'planned' | 'optional';

export interface Semester {
  id: string;
  term: string;
  year: number;
  status: SemesterStatus;
  courseIds: string[];
  credits: number;
}

/** Semester hydrated for UI rendering (catalog + meetings + engine warnings). */
export interface SemesterCourse {
  id: string;
  title: string | null; // null → render the id alone (grounded-UI rule)
  creditHours: number | null;
  meeting: string | null;
  warning?: string; // FC29 verdict text from the api layer
}

export interface SemesterSummary {
  id: string;
  term: string;
  year: number;
  status: SemesterStatus;
  credits: number;
  courseCount: number;
  issueCount: number;
}

export interface SemesterHydrated extends Semester {
  courses: SemesterCourse[];
}

export interface PlanIssue {
  course: string | null; // offending course id, when the issue is per-course
  text: string;
}

export interface PlanReview {
  status: 'ok' | 'issues';
  issues: string[];
  semesterIssues: Record<string, PlanIssue[]>; // api mock of engine verdicts (FC29/FC32)
}

export interface PlanProgram {
  majorName: string;
  concentration: string;
  catalogYear: string;
}

export interface PlanProgress {
  completed: number;
  inProgress: number;
  planned: number;
  total: number;
}

/** The student's active plan as the UI consumes it (getActivePlan). */
export interface ActivePlanData {
  plan_id: string;
  student_id: string;
  program: PlanProgram;
  progress: PlanProgress;
  currentTerm: string;
  onTrackNote: string;
  semesters: Semester[];
  check: PlanReview;
}

export interface PlanOption {
  name: string;
  concentrations: string[];
}

export interface GeneratePlanRequest {
  majorName: string;
  concentration: string;
  includeSummer?: boolean;
}

export interface PlanDetailSemester {
  term: string;
  year: number;
  courses: string[];
  credits: number;
}

export interface PlanDetail {
  plan_id: string;
  student_id: string;
  target_major: string;
  concentration: string;
  includes_summer: boolean;
  semester_count: number;
  created_at: string;
  semesters: PlanDetailSemester[];
}

export interface ComparisonRow {
  current: string;
  proposed: string;
}

export interface ProgramComparison {
  current: {
    degree: string;
    concentration: string;
    hoursThatCount: string;
    hoursRemaining: string;
    graduation: string;
  };
  proposed: {
    degree: string;
    concentration: string;
    hoursThatCount: string;
    hoursRemaining: string;
    graduation: string;
  };
  notes: string[]; // FC26 trade-offs
}

/* ─── Chat (FC22–FC24, FC27, FC34) ────────────────────────────────────── */

export interface Conversation {
  id: string;
  title: string;
  date: string; // ISO date used for grouping (FC34)
  snippet?: string;
}

export interface ProposedAction {
  summary: string;
  detail?: string;
  /** Server pending-action id (FC23) — decisions travel back with it. */
  actionId?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'advisor';
  text: string;
  action?: ProposedAction; // FC23 proposal awaiting explicit decision
}

export type ProposalDecision = 'confirmed' | 'declined';

export interface ProposalResponse {
  messageId: string;
  decision: ProposalDecision;
  reply: string;
}

/* ─── Student (FC36, FC25, FC32) ──────────────────────────────────────── */

export interface StudentProfile {
  studentId: string;
  studentIdLabel: string;
  name: string;
  catalogYear: string;
  standing: string;
  major: string;
  concentration: string;
}

export interface PlanningPreferences {
  maxCreditsPerSemester: number; // FC32 semester-cap preference
  includeSummer: boolean; // FC25 optional summer sessions
  preferredClassTimes: string;
}