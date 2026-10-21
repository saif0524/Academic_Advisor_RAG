/**
 * Course discovery API service (FC8–FC12, FC29–FC32 verdict displays) —
 * MOCK implementation standing in for the courses endpoints
 * (src/server/routers/courses.py, proposed FC-new-rest-api; keyword search →
 * SQLite FC33, natural-language search → Chroma FC9/FC33).
 *
 * Shapes mirror the future HTTP contract:
 *   searchCourses(query)    → future GET /courses/search?q=… → SearchResponse
 *   getCourseSuggestions(…) → future GET /courses/suggestions?term=…
 *   getCourseDetail(id)     → future GET /courses/{id} (+ sections FC12)
 *
 * Grounding notes:
 * - Course ids/titles/descriptions come from api/catalog (real seed records
 *   from data/course-desc.jsonl).
 * - Meeting strings / flags are mock metadata (SQLite + the deterministic
 *   validator own them; FC12/FC29–FC32). Student-context badges
 *   ("Prereq in progress", "Needs CSE 4380 first", "Conflicts with…") are
 *   mock verdicts of FC29/FC30/FC31 checks — display only, no client-side
 *   constraint math in components.
 * - Query matching below is plain deterministic keyword matching — a mock of
 *   the search endpoints' role, not the LLM.
 */

import { request } from './client';
import { COURSES, PREREQ_FIXTURE, STUDENT_PROGRESS, getMeeting, getCourse } from './catalog';
import type {
  CourseDetail,
  CourseFlag,
  CourseSuggestion,
  SearchResponse,
} from './types';

const MOCK_LATENCY_MS = 500;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** Mock section line for a course (FC12), or null when none is on record. */
function meetingLine(id: string): string | null {
  const meeting = getMeeting(id);
  return meeting ? `3 hrs · ${meeting}` : null;
}

/**
 * FC29/FC30 verdict badges for a candidate course, given the mock student
 * context (completed/in-progress sets from api/catalog).
 */
export function verdictFlagsFor(courseId: string): CourseFlag[] {
  const prereqs = PREREQ_FIXTURE[courseId] ?? [];
  if (prereqs.length === 0) {
    return [{ label: 'Prerequisites met', variant: 'success' }];
  }
  return prereqs.map((prereqId): CourseFlag => {
    if (STUDENT_PROGRESS.completedCourseIds.includes(prereqId)) {
      return { label: 'Prerequisites met', variant: 'success' }; // FC29 pass
    }
    if (STUDENT_PROGRESS.inProgressCourseIds.includes(prereqId)) {
      return { label: `Prereq in progress (CSE ${prereqId})`, variant: 'warning' }; // FC30 not yet passed
    }
    return { label: `Needs CSE ${prereqId} first`, variant: 'warning' }; // FC29 fail
  });
}

interface ResultSource { term: string }

const RESULT_COURSES: Record<string, ResultSource> = {
  '4380': { term: 'Spring 2027' },
  '4382': { term: 'Spring 2027' },
  '4381': { term: 'Fall 2027' },
  '4308': { term: 'Fall 2027' },
  '4344': { term: 'Spring 2027' },
  '4309': { term: 'Spring 2027' },
};

/** The advisor-answer text for a query, or null when none matches canned NL. */
function advisorAnswer(q: string): string | null {
  if (q.includes('cover') || q.includes('4380')) {
    return (
      'CSE 4380 — Information Security is a hands-on introduction to security: system ' +
      'security, buffer overflows, cryptography basics, firewalls and intrusion detection. ' +
      'It is the prerequisite for CSE 4381, which your plan needs in Fall 2027.'
    );
  }
  if (q.includes('security') || q.includes('elective')) {
    return (
      'Two cybersecurity electives fit your plan toward the Cybersecurity concentration. ' +
      'CSE 4380 Information Security is the strongest pick — it is the prerequisite for ' +
      'CSE 4381, which your plan needs in Fall 2027.'
    );
  }
  if (q.includes('next semester') || q.includes('take') || q.includes('spring')) {
    return (
      'For Spring 2027, your plan already has CSE 4380, CSE 4382, CSE 3330, and CSE 3315 — ' +
      '12 of 18 credit hours. CSE 4309 or CSE 4333 would fill your remaining hours; CSE 4344 ' +
      'conflicts with your CSE 4382 meeting time.'
    );
  }
  return null;
}

function resultFor(courseId: string) {
  const course = getCourse(courseId);
  if (!course) return null; // never invent details for unknown ids (grounded UI)
  const flags = verdictFlagsFor(courseId).slice();
  // FC31 mock verdict — a deliberate schedule-conflict demo for CSE 4344.
  if (courseId === '4344') {
    flags.unshift({ label: 'Conflicts with CSE 4382', variant: 'danger' });
  }
  return {
    id: courseId,
    title: course.title,
    creditHours: course.creditHours,
    meeting: meetingLine(courseId),
    description: course.description ?? 'No description on record.',
    term: RESULT_COURSES[courseId]?.term ?? null,
    flags,
  };
}

/** The canned natural-language fallback result set (wireframe 04 stories). */
const DEFAULT_RESULT_IDS = ['4380', '4382', '4381', '4308', '4344'];

/**
 * One search box, two behaviors (wireframe 04): a keyword match over the
 * seed catalog (FC8 — future SQLite path) and canned natural-language
 * queries that return an advisor answer plus matching courses (FC9 — future
 * Chroma path). Empty query → explicit empty result, nothing invented.
 */
export async function searchCourses(query: string): Promise<SearchResponse> {
  await sleep(MOCK_LATENCY_MS);
  const trimmed = (query ?? '').trim();
  if (trimmed === '') {
    return { answer: null, courses: [] };
  }
  const q = trimmed.toLowerCase();
  const cannedAnswer = advisorAnswer(q);
  // Route by data type (FC33 mock): numeric queries are exact-ish catalog
  // lookups (future SQLite, FC8); everything else matches title/description
  // text (future Chroma semantic path, FC9) with the canned result set as
  // the NL fallback so the wireframe story always has grounded courses.
  let ids: string[];
  if (/^\d{2,4}$/.test(q)) {
    ids = Object.keys(COURSES).filter((id) => id.startsWith(q));
  } else {
    ids = Object.keys(COURSES).filter(
      (id) =>
        COURSES[id].title.toLowerCase().includes(q) ||
        (COURSES[id].description ?? '').toLowerCase().includes(q),
    );
    if (ids.length === 0) ids = DEFAULT_RESULT_IDS;
  }
  const courses = ids
    .slice(0, 8)
    .map(resultFor)
    .filter((course): course is NonNullable<ReturnType<typeof resultFor>> => course !== null);
  const effectiveAnswer = cannedAnswer
    ? { text: cannedAnswer }
    : {
        text:
          'I matched your query against the CSE course catalog and your active plan. ' +
          'Ask about a course (e.g., "What does CSE 4380 cover?") or your schedule in plain language.',
      };
  return { answer: { ...effectiveAnswer, matchCount: courses.length }, courses };
}

/**
 * Candidate suggestions for the timeline "Add a course" search (FC8 + FC29
 * mock badges). Excludes courses already planned in the given semester
 * draft; verdicts come from verdictFlagsFor. Candidates exist only for the
 * Spring 2027 fixture — other terms resolve to an explicit empty list.
 */
/**
 * Candidate suggestions for the timeline "Add a course" search (FC8) — LIVE:
 * keyword search against GET /courses (SQLite, FC33). Candidates already in
 * the draft are filtered out. Prerequisite/eligibility verdicts are NOT
 * computed here — the plan-check banner grades the whole draft through
 * POST /plans/review (FC29–FC32); badges stay neutral until then.
 */
export async function getCourseSuggestions(_termId: string, alreadyPlannedIds: string[] = [], query = ''): Promise<CourseSuggestion[]> {
  const path = query
    ? `/courses?q=${encodeURIComponent(query)}`
    : '/courses';
  const body = await request<{ results: Array<{ course_id: string; title: string; credit_hours: number | null }> }>(path);
  return body.results
    .filter((course) => !alreadyPlannedIds.includes(course.course_id))
    .slice(0, 12)
    .map((course): CourseSuggestion => ({
      id: course.course_id,
      title: course.title,
      creditHours: course.credit_hours ?? 0,
      meeting: null, // sections live behind GET /courses/{id}/sections (FC12)
      badge: 'Add to plan',
      badgeVariant: 'neutral',
      conflict: null,
    }));
}

/**
 * Course detail for the Details dialog (FC11 fields; sections FC12).
 * Prerequisite records come from PREREQ_FIXTURE — courses with no record
 * keep an empty list (the UI shows an explicit "no records" note instead of
 * a fabricated list).
 */
export async function getCourseDetail(courseId: string): Promise<CourseDetail | null> {
  await sleep(MOCK_LATENCY_MS);
  const course = getCourse(courseId);
  if (!course) return null;
  const prereqIds = PREREQ_FIXTURE[courseId] ?? [];
  return {
    id: courseId,
    title: course.title,
    description: course.description ?? 'No description on record.',
    creditHours: course.creditHours,
    meeting: meetingLine(courseId),
    prereqs: prereqIds.map((pid) => {
      const prereqCourse = getCourse(pid);
      const status: 'met' | 'in-progress' | 'missing' =
        STUDENT_PROGRESS.inProgressCourseIds.includes(pid)
          ? 'in-progress'
          : STUDENT_PROGRESS.completedCourseIds.includes(pid)
            ? 'met'
            : 'missing';
      return { id: pid, title: prereqCourse?.title ?? null, status }; // FC29/FC30 mock verdict
    }),
  };
}