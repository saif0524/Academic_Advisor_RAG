import type { Meta } from '@storybook/react-vite';
import PlanComparisonTable from './PlanComparisonTable';
import type { ProgramComparison } from '../../../api/types';

const COMPARISON_FIXTURE: ProgramComparison = {
  current: {
    degree: 'BS in Computer Science',
    concentration: 'Cybersecurity',
    hoursThatCount: '81 of 81',
    hoursRemaining: '39',
    graduation: 'Spring 2028',
  },
  proposed: {
    degree: 'BS in Software Engineering',
    concentration: 'Artificial Intelligence',
    hoursThatCount: '72 of 81',
    hoursRemaining: '48',
    graduation: 'Fall 2028',
  },
  notes: [
    'Estimates from your degree audit — the advisor walks through pros and cons before you commit.',
    'Two CSE concentration courses would no longer count toward the new degree.',
    'CSE 4380 stays in Spring 2027 either way — CSE 4381 later in the plan needs it in an earlier semester.',
  ],
};

const meta = {
  title: 'Components/planner/PlanComparisonTable',
  component: PlanComparisonTable,
  args: { comparison: COMPARISON_FIXTURE },
} satisfies Meta<typeof PlanComparisonTable>;

export default meta;

export const Default = {};
export const NoComparison = { args: { comparison: null } };
export const Loading = { args: { comparison: null, loading: true } };
export const ErrorState = { args: { comparison: null, error: 'advisor API unreachable' } };