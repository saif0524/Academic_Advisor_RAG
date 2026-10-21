import type { Meta, StoryObj } from '@storybook/react-vite';
import Dashboard from './Dashboard';
import { expect, userEvent } from 'storybook/test';

/* Instant fixtures (real seed records from api/catalog + plans) — stories
   never hit the real api (mock latency would slow review). */
const FIXTURES = {
  plan: {
    plan_id: 'plan-0001',
    student_id: 'stu-0001',
    program: { majorName: 'BS in Computer Science', concentration: 'Cybersecurity', catalogYear: '2024-2025' },
    progress: { completed: 66, inProgress: 12, planned: 42, total: 120 },
    currentTerm: 'Fall 2026',
    onTrackNote: 'On track — graduate Spring 2028',
    semesters: [
      { id: 'f26', term: 'Fall', year: 2026, status: 'in-progress' as const, courseIds: ['3310', '3320', '3318', '3380'], credits: 12 },
      { id: 's27', term: 'Spring', year: 2027, status: 'planned' as const, courseIds: ['4380', '4382', '3330', '3315'], credits: 12 },
      { id: 'su27', term: 'Summer', year: 2027, status: 'optional' as const, courseIds: [], credits: 0 },
      { id: 'f27', term: 'Fall', year: 2027, status: 'planned' as const, courseIds: ['4316', '4381', '4308', '4321'], credits: 12 },
      { id: 's28', term: 'Spring', year: 2028, status: 'planned' as const, courseIds: ['4317', '3341', '4392', '3340'], credits: 12 },
    ],
    check: { status: 'ok' as const, issues: [], semesterIssues: {} },
  },
  catalog: {
    '3310': { id: '3310', title: 'FUNDAMENTALS OF SOFTWARE ENGINEERING', creditHours: 3 },
    '3320': { id: '3320', title: 'OPERATING SYSTEMS', creditHours: 3 },
    '3318': { id: '3318', title: 'ALGORITHMS & DATA STRUCTURES', creditHours: 3 },
    '3380': { id: '3380', title: 'LINEAR ALGEBRA FOR CSE', creditHours: 3 },
    '4380': { id: '4380', title: 'INFORMATION SECURITY', creditHours: 3 },
    '4382': { id: '4382', title: 'SECURE PROGRAMMING', creditHours: 3 },
    '3330': { id: '3330', title: 'DATABASE SYSTEMS AND FILE STRUCTURES', creditHours: 3 },
    '3315': { id: '3315', title: 'THEORETICAL CONCEPTS IN COMPUTER SCIENCE AND ENGINEERING', creditHours: 3 },
    '4316': { id: '4316', title: 'COMPUTER SYSTEM DESIGN PROJECT I', creditHours: 3 },
    '4381': { id: '4381', title: 'INFORMATION SECURITY II', creditHours: 3 },
    '4308': { id: '4308', title: 'ARTIFICIAL INTELLIGENCE', creditHours: 3 },
    '4321': { id: '4321', title: 'SOFTWARE TESTING & MAINTENANCE', creditHours: 3 },
    '4317': { id: '4317', title: 'COMPUTER SYSTEM DESIGN PROJECT II', creditHours: 3 },
    '3341': { id: '3341', title: 'DIGITAL LOGIC DESIGN II', creditHours: 3 },
    '4392': { id: '4392', title: 'SPECIAL TOPICS', creditHours: 3 },
    '3340': { id: '3340', title: 'INTRODUCTION TO HUMAN COMPUTER INTERACTION', creditHours: 3 },
  },
};

const SEAMS = {
  loadDependencies: () => Promise.resolve(FIXTURES),
};

const meta = {
  title: 'Pages/Dashboard',
  component: Dashboard,
  args: SEAMS,
} satisfies Meta<typeof Dashboard>;

export default meta;

export const Default: StoryObj<typeof Dashboard> = {};

/** Wireframe 02's home → timeline path: the Edit action navigates. */
export const OpensPlanner: StoryObj<typeof Dashboard> = {
  play: async ({ canvas }) => {
    await userEvent.click(canvas.getByRole('button', { name: /new plan/i }));
    await expect(await canvas.findByText(/Generate Degree Plan/i)).toBeVisible();
  },
};

export const LoadError: StoryObj<typeof Dashboard> = {
  args: { loadDependencies: () => Promise.reject(new Error('advisor API unreachable')) },
};