import type { Meta } from '@storybook/react-vite';
import PlanProgressHeader from './PlanProgressHeader';
import type { ActivePlanData } from '../../../api/types';

const PLAN_FIXTURE: ActivePlanData = {
  plan_id: 'plan-0001',
  student_id: 'stu-0001',
  program: { majorName: 'BS in Computer Science', concentration: 'Cybersecurity', catalogYear: '2024-2025' },
  progress: { completed: 66, inProgress: 12, planned: 42, total: 120 },
  onTrackNote: 'On track — graduate Spring 2028',
  currentTerm: 'Fall 2026',
  semesters: [],
  check: { status: 'ok', issues: [], semesterIssues: {} },
};

const meta = {
  title: 'Components/planner/PlanProgressHeader',
  component: PlanProgressHeader,
  args: {
    plan: PLAN_FIXTURE,
    termOptions: ['Fall 2026', 'Spring 2027', 'Summer 2027', 'Fall 2027', 'Spring 2028'],
    onTermChange: () => {},
  },
} satisfies Meta<typeof PlanProgressHeader>;

export default meta;

export const Default = {};
export const NoTermPicker = { args: { termOptions: undefined } };
export const Loading = { args: { plan: null, loading: true } };
export const ErrorState = { args: { plan: null, error: 'advisor API unreachable' } };
export const NoPlan = { args: { plan: null } };