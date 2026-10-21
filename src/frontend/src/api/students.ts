/**
 * Student profile & planning-preferences API service (FC36 pre-auth baseline,
 * FC1/FC7, FC25, FC32) — LIVE implementation over the FastAPI students
 * endpoints. All calls funnel through api/client (no inline fetch).
 *
 *   getStudentProfile()         → GET /students/me
 *   getPlanningPreferences()    → GET /students/me/preferences
 *   savePlanningPreferences(p)  → PUT /students/me/preferences
 *
 * No auth headers: authentication is out of scope (FC36); the server's
 * pre-auth fallback identity drives the demo student. Unknown profile
 * fields render as null → callers show explicit placeholders (grounded-UI
 * rule — no invented catalog years or standings).
 */

import { request, ApiError } from './client';
import type { PlanningPreferences, StudentProfile } from './types';
import type { DegreeProgressSummary } from './plans';

export async function getStudentProfile(): Promise<StudentProfile> {
  const body = await request<{
    student_id: string;
    name: string | null;
    current_major: string | null;
    concentration: string | null;
  }>('/students/me');
  return {
    studentId: body.student_id, // pre-authenticated session (FC36)
    studentIdLabel: '[ID]', // masked in the wireframe
    name: body.name,
    catalogYear: '—', // not on record in the seed data — honest unknown
    standing: '—',
    major: body.current_major,
    concentration: body.concentration,
  };
}

export async function getPlanningPreferences(): Promise<PlanningPreferences> {
  const body = await request<{
    max_credits_per_semester: number | null;
    include_summer: boolean;
    preferred_class_times: string | null;
  }>('/students/me/preferences');
  return {
    maxCreditsPerSemester: body.max_credits_per_semester ?? 18, // FC32 cap input
    includeSummer: body.include_summer, // FC25 optional summer toggle
    preferredClassTimes: body.preferred_class_times ?? 'Any time',
  };
}

export async function savePlanningPreferences(
  preferences: PlanningPreferences,
): Promise<{ saved: boolean; savedAt: string }> {
  await request<{ max_credits_per_semester: number | null }>('/students/me/preferences', {
    method: 'PUT',
    body: {
      max_credits_per_semester: preferences.maxCreditsPerSemester,
      include_summer: preferences.includeSummer,
      preferred_class_times: preferences.preferredClassTimes,
    },
  });
  return { saved: true, savedAt: new Date().toISOString() };
}

export { ApiError }; // re-export for plan flows that need 404-catching

/** FC19 progress toward the selected degree (deterministic counting server-side). */
export async function getDegreeProgress(): Promise<DegreeProgressSummary> {
  const body = await request<{
    degree_id: string | null;
    completion_percent: number | null;
    completed_hours: number | null;
    in_progress_hours: number | null;
    total_credits_required: number | null;
  }>('/students/me/degree/progress');
  return {
    completionPercent: body.completion_percent,
    completedHours: body.completed_hours,
    inProgressHours: body.in_progress_hours,
    totalCreditsRequired: body.total_credits_required,
  };
}