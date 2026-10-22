import { request } from './client';

/** FC21 statuses — exactly the backend's enum (server/schemas/classes.py). */
export type ClassStatus = 'not_taken' | 'in_progress' | 'taken' | 'passed' | 'failed';
export type ClassStatusMap = Record<string, ClassStatus>;

/** Profile classes by course id (FC14/FC21) → GET /classes. */
export async function listClassStatuses(): Promise<ClassStatusMap> {
  const body = await request<{ results: Array<{ course_id: string; status: ClassStatus }> }>('/classes');
  return Object.fromEntries((body.results ?? []).map((c) => [c.course_id, c.status]));
}

/**
 * Change a class's status (FC21) — a direct user action, so no FC23
 * confirmation. POST first (idempotent: an existing class is untouched;
 * unknown catalog ids 404), then PATCH the status.
 */
export async function setClassStatus(courseId: string, status: ClassStatus): Promise<ClassStatus> {
  await request('/classes', { method: 'POST', body: { course_id: courseId } });
  const updated = await request<{ status: ClassStatus }>(`/classes/${encodeURIComponent(courseId)}`, {
    method: 'PATCH',
    body: { status },
  });
  return updated.status;
}
