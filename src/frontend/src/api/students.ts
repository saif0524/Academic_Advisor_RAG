/**
 * Student profile & planning-preferences API service (FC36 pre-auth
 * baseline, FC1/FC7, FC25, FC32) — MOCK implementation standing in for the
 * students endpoints (src/server/routers/students.py, proposed
 * FC-new-rest-api — all student routes return 501 `not_wired` today).
 *
 * Shapes mirror the future HTTP contract:
 *   getStudentProfile()        → future GET /students/me → StudentProfile
 *   getPlanningPreferences()   → future GET /students/me/preferences
 *   savePlanningPreferences(p) → future PUT /students/me/preferences
 *
 * Grounding notes: the profile record is mock data for the demo student;
 * constraints it feeds (max credit hours per semester — FC32; include
 * summer — FC25) are inputs the deterministic engine consumes. No LLM.
 */

import { STUDENT_PROGRESS } from './catalog';
import type { PlanningPreferences, StudentProfile } from './types';

const MOCK_LATENCY_MS = 500;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const PREFS_FIXTURE: PlanningPreferences = {
  maxCreditsPerSemester: 18, // FC32 semester-cap preference
  includeSummer: false, // FC25 optional summer sessions
  preferredClassTimes: 'Any time',
};

export async function getStudentProfile(): Promise<StudentProfile> {
  await sleep(MOCK_LATENCY_MS);
  return {
    studentId: STUDENT_PROGRESS.studentId, // pre-authenticated session (FC36)
    studentIdLabel: '[ID]', // masked in the wireframe
    name: 'Jordan Lee',
    catalogYear: '2024-2025',
    standing: 'Junior',
    major: 'BS in Computer Science',
    concentration: 'Cybersecurity',
  };
}

export async function getPlanningPreferences(): Promise<PlanningPreferences> {
  await sleep(MOCK_LATENCY_MS);
  return { ...PREFS_FIXTURE };
}

export async function savePlanningPreferences(_preferences: PlanningPreferences): Promise<{ saved: boolean; savedAt: string }> {
  // The future PUT body mirrors the argument; the mock just acknowledges.
  await sleep(MOCK_LATENCY_MS);
  return { saved: true, savedAt: new Date().toISOString() };
}