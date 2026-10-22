/**
 * Course API (FC8–FC12):
 *   searchCourses(query)      → POST /chat/messages + GET /courses/search/semantic + POST /audits/course-check
 *   getCourseDetail(id)       → GET /courses/{id}
 *   getCourseSuggestions(...) → GET /courses?q=  (timeline "Add a course")
 */

import { request } from './client';
import { sendMessage } from './chat';
import type { CourseDetail, CourseFlag, CourseSuggestion, SearchResponse } from './types';

interface SemanticSearchResponse {
  results: { course_id: string; title: string; description: string | null; credit_hours: number | null }[];
  count: number;
  source: 'chroma' | 'sql';
}
interface CourseAuditResponse {
  student_id: string;
  course_id: string;
  eligible: boolean | null;
  checks: { check_id: string; description: string; passed: boolean | null; reason: string | null }[];
}
interface CourseClassRecord {
  course_id: string;
  status: string;
}
interface ClassesListResponse {
  results: CourseClassRecord[];
}
interface ServerCourseDetail {
  course_id: string;
  title: string;
  description: string | null;
  credit_hours: number | null;
  prerequisites: string[];
  corequisites: string[];
  sections: {
    section_id: string;
    course_id: string;
    term: string;
    instructor: string | null;
    meeting_days: string[];
    start_time: string | null;
    end_time: string | null;
  }[];
}

/** Turn engine audit checks (FC29–FC32) into result-card badges. */
function flagsFromAudit(audit: CourseAuditResponse): CourseFlag[] {
  const flags: CourseFlag[] = [];
  for (const check of audit.checks) {
    if (check.check_id === 'FC29') {
      const missing = (check.reason ?? '').startsWith('Not satisfied');
      flags.push(
        missing
          ? { label: check.reason ? check.reason.replace('Not satisfied: ', 'Needs ') : 'Prerequisites missing', variant: 'warning' }
          : { label: 'Prerequisites met', variant: 'success' },
      );
    } else if (check.check_id === 'FC30' && check.passed === false) {
      flags.push({ label: 'Already completed', variant: 'warning' });
    } else if (check.check_id === 'FC31' && check.passed === false) {
      flags.push({ label: 'Schedule conflict', variant: 'danger' });
    } else if (check.check_id === 'FC32' && check.passed === false) {
      flags.push({ label: 'Over the credit cap', variant: 'warning' });
    } else if (check.check_id === 'FC4c' && check.passed === false) {
      flags.push({ label: "Doesn't count for this degree", variant: 'neutral' });
    }
  }
  return flags;
}

/** Search page: advisor answer (FC22) + semantic results (FC9) with audit badges (FC24). */
export async function searchCourses(query: string): Promise<SearchResponse> {
  const trimmed = (query ?? '').trim();
  if (trimmed === '') {
    return { answer: null, courses: [] };
  }
  const [answerTurn, semantic] = await Promise.all([
    sendMessage(trimmed),
    request<SemanticSearchResponse>(
      `/courses/search/semantic?q=${encodeURIComponent(trimmed)}`,
    ),
  ]);

  const courses = await Promise.all(
    semantic.results.map(async (hit): Promise<SearchResponse['courses'][number]> => {
      let flags: CourseFlag[] = [];
      try {
        // FC24 verdicts per result — deterministic engine output (FC29–FC32)
        const audit = await request<CourseAuditResponse>('/audits/course-check', {
          method: 'POST',
          body: { course_id: hit.course_id },
        });
        flags = flagsFromAudit(audit);
      } catch {
        // honest: no verdict badges when the audit surface is unavailable
        flags = [];
      }
      return {
        id: hit.course_id,
        title: hit.title,
        creditHours: hit.credit_hours ?? 0,
        meeting: null,
        description: hit.description ?? 'No description on record.',
        term: null,
        flags,
      };
    }),
  );

  return {
    answer: { text: answerTurn.text, matchCount: courses.length },
    courses,
  };
}

/** Course detail (FC11/FC12) plus the student's status for each prerequisite. */
export async function getCourseDetail(courseId: string): Promise<CourseDetail | null> {
  const detail = await request<ServerCourseDetail>(`/courses/${encodeURIComponent(courseId)}`);
  let classStatuses: CourseClassRecord[] = [];
  try {
    classStatuses = (await request<ClassesListResponse>('/classes')).results ?? [];
  } catch {
    // profile data unavailable → prerequisite statuses render as 'missing'
  }
  const statusOf = (prereqId: string): CourseDetail['prereqs'][number]['status'] =>
    classStatuses.some((c) => c.course_id === prereqId && (c.status === 'passed' || c.status === 'taken'))
      ? 'met'
      : classStatuses.some((c) => c.course_id === prereqId && c.status === 'in_progress')
        ? 'in-progress'
        : 'missing';

  const section = detail.sections[0] ?? null;
  const meeting = section
    ? `${section.meeting_days.join('/') || 'TBD'} ${section.start_time ?? 'TBD'}–${section.end_time ?? 'TBD'}`
    : null;
  return {
    id: detail.course_id,
    title: detail.title,
    description: detail.description ?? 'No description on record.',
    creditHours: detail.credit_hours ?? 0,
    meeting,
    prereqs: detail.prerequisites.map((prereqId) => ({ id: prereqId, title: null, status: statusOf(prereqId) })),
  };
}

/** Keyword candidates for the timeline "Add a course" search (FC8). Eligibility
    is checked later for the whole draft by POST /plans/review (FC29–FC32). */
export async function getCourseSuggestions(_termId: string, alreadyPlannedIds: string[] = [], query = ''): Promise<CourseSuggestion[]> {
  const path = query ? `/courses?q=${encodeURIComponent(query)}` : '/courses';
  const body = await request<{ results: Array<{ course_id: string; title: string; credit_hours: number | null }> }>(path);
  return body.results
    .filter((course) => !alreadyPlannedIds.includes(course.course_id))
    .slice(0, 12)
    .map((course): CourseSuggestion => ({
      id: course.course_id,
      title: course.title,
      creditHours: course.credit_hours ?? 0,
      meeting: null,
      badge: 'Add to plan',
      badgeVariant: 'neutral',
      conflict: null,
    }));
}
