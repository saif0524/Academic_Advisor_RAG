/**
 * Course-discovery API service — LIVE implementations (wireframe 04):
 * FC22 answer + FC9 semantic results + FC24/FC29–FC32 verdict badges, all
 * backed by the FastAPI surface (src/server; one agent powering both the
 * search page and the chat drawer).
 *
 *   searchLive(query)     → POST /chat/messages (FC22 answer, persisted FC34)
 *                         + GET  /courses/search/semantic (FC9 → Chroma)
 *                         + POST /audits/course-check per result (FC24 verdicts)
 *   getCourseDetailLive() → GET /courses/{course_id} (FC11/FC12)
 *
 * Empty lookups stay explicit — nothing is ever invented client-side.
 */

import { request } from './client';
import { sendMessage } from './chat';
import type { CourseDetail, CourseFlag, SearchResponse } from './types';

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

/** FC24/FC29–FC32 verdict → result-card badges (labels mirror the mock eras). */
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

/**
 * One search box, two behaviors over live endpoints (FC33 routing server-
 * side): the FC22 answer is the SAME advisor agent behind the chat drawer;
 * results come from semantic search (FC9) when the engine can ground them.
 */
export async function searchLive(query: string): Promise<SearchResponse> {
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

/** Course detail (FC11/FC12): catalog fields + sections (FC12) and the
    student's own per-prerequisite statuses (FC21 facts, not constraint math). */
export async function getCourseDetailLive(courseId: string): Promise<CourseDetail | null> {
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