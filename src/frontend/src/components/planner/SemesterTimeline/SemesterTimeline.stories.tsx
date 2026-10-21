import type { Meta } from '@storybook/react-vite';
import SemesterTimeline from './SemesterTimeline';
import type { SemesterSummary } from '../../../api/types';

const SEMESTERS_FIXTURE: SemesterSummary[] = [
  { id: 'f26', term: 'Fall', year: 2026, status: 'in-progress', credits: 12, courseCount: 4, issueCount: 0 },
  { id: 's27', term: 'Spring', year: 2027, status: 'planned', credits: 12, courseCount: 4, issueCount: 0 },
  { id: 'su27', term: 'Summer', year: 2027, status: 'optional', credits: 0, courseCount: 0, issueCount: 0 },
  { id: 'f27', term: 'Fall', year: 2027, status: 'planned', credits: 12, courseCount: 4, issueCount: 1 },
  { id: 's28', term: 'Spring', year: 2028, status: 'planned', credits: 12, courseCount: 4, issueCount: 1 },
];

const meta = {
  title: 'Components/planner/SemesterTimeline',
  component: SemesterTimeline,
  args: { semesters: SEMESTERS_FIXTURE, selectedId: 's27', onSelect: () => {} },
} satisfies Meta<typeof SemesterTimeline>;

export default meta;

export const Default = {};
export const NoSelection = { args: { selectedId: null } };

/** Wireframe 03: unsaved removal flags later semesters (engine verdicts). */
export const WithIssues = { args: { selectedId: 'f27' } };

export const Loading = { args: { semesters: null, loading: true } };
export const ErrorState = { args: { semesters: null, error: 'advisor API unreachable' } };
export const Empty = { args: { semesters: [] } };