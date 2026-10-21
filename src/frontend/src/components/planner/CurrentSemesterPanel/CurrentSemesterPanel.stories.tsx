import type { Meta } from '@storybook/react-vite';
import CurrentSemesterPanel from './CurrentSemesterPanel';

const COURSES_FIXTURE = [
  { id: '3310', title: 'FUNDAMENTALS OF SOFTWARE ENGINEERING', creditHours: 3, status: 'in-progress' as const },
  { id: '3320', title: 'OPERATING SYSTEMS', creditHours: 3, status: 'in-progress' as const },
  { id: '3318', title: 'ALGORITHMS & DATA STRUCTURES', creditHours: 3, status: 'in-progress' as const },
  { id: '3380', title: 'LINEAR ALGEBRA FOR CSE', creditHours: 3, status: 'in-progress' as const },
];

const meta = {
  title: 'Components/planner/CurrentSemesterPanel',
  component: CurrentSemesterPanel,
  args: { term: 'Fall 2026', courses: COURSES_FIXTURE },
} satisfies Meta<typeof CurrentSemesterPanel>;

export default meta;

export const Default = {};
export const Loading = { args: { courses: null, loading: true } };
export const ErrorState = { args: { courses: null, error: 'advisor API unreachable' } };
export const Empty = { args: { courses: [] } };

/** Unknown id → id alone, no invented title (grounded-UI rule). */
export const UnknownCourse = {
  args: { courses: [...COURSES_FIXTURE.slice(0, 2), { id: '9999', status: 'in-progress' as const }] },
};