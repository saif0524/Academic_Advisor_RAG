import type { Meta } from '@storybook/react-vite';
import SemesterDetail from './SemesterDetail';
import type { CourseSuggestion, SemesterHydrated } from '../../../api/types';

/** Real seed courses; warnings are mock FC29 verdicts. */
const COURSES_FIXTURE = [
  { id: '4380', title: 'INFORMATION SECURITY', creditHours: 3, meeting: 'TuTh 11:00–12:20' },
  { id: '4382', title: 'SECURE PROGRAMMING', creditHours: 3, meeting: 'MW 2:30–3:50' },
  { id: '3330', title: 'DATABASE SYSTEMS AND FILE STRUCTURES', creditHours: 3, meeting: 'MW 11:30–12:50' },
  {
    id: '4381',
    title: 'INFORMATION SECURITY II',
    creditHours: 3,
    meeting: 'MW 10:00–11:20',
    warning: 'CSE 4381 needs CSE 4380 in an earlier semester',
  },
] satisfies SemesterHydrated['courses'];

const SEMESTER_FIXTURE: SemesterHydrated = {
  id: 's27',
  term: 'Spring',
  year: 2027,
  status: 'planned',
  courseIds: ['4380', '4382', '3330', '4381'],
  credits: 12,
  courses: COURSES_FIXTURE,
};

const ADD_COURSE_SEAM = {
  searchTerm: '',
  onSearchChange: () => {},
  candidates: [
    { id: '4308', title: 'ARTIFICIAL INTELLIGENCE', creditHours: 3, meeting: 'MW 1:00–2:20', badge: 'Prerequisites met', badgeVariant: 'success' as const, conflict: null },
    { id: '4344', title: 'COMPUTER NETWORK ORGANIZATION', creditHours: 3, meeting: 'MW 2:30–3:50', badge: 'Conflicts with CSE 4382', badgeVariant: 'danger' as const, conflict: 'Conflicts with CSE 4382' },
  ] satisfies CourseSuggestion[],
  onPickCourse: () => {},
};

const meta = {
  title: 'Components/planner/SemesterDetail',
  component: SemesterDetail,
  args: {
    semester: SEMESTER_FIXTURE,
    creditCap: 18,
    check: { status: 'ok', issues: [], semesterIssues: { s27: [] } },
    onRemoveCourse: () => {},
    ...ADD_COURSE_SEAM,
  },
} satisfies Meta<typeof SemesterDetail>;

export default meta;

export const Default = {};

/** Wireframe 03 — flagged courses surface the engine warnings. */
export const WithIssue = {
  args: {
    check: {
      status: 'issues' as const,
      issues: ['CSE 4381 needs CSE 4380 in an earlier semester'],
      semesterIssues: {
        s27: [],
        f27: [{ course: '4381', text: 'CSE 4381 needs CSE 4380 in an earlier semester' }],
      },
    },
    semester: {
      ...SEMESTER_FIXTURE,
      id: 'f27',
      courses: [COURSES_FIXTURE[3]],
      credits: 3,
    } satisfies SemesterHydrated,
  },
};

/** Wireframe 02 — optional summer with no courses keeps the add-search. */
export const EmptyOptional = {
  args: {
    semester: {
      id: 'su27',
      term: 'Summer',
      year: 2027,
      status: 'optional' as const,
      courseIds: [],
      credits: 0,
      courses: [],
    } satisfies SemesterHydrated,
  },
};

export const NoSelection = { args: { semester: null } };
export const Loading = { args: { semester: null, loading: true } };
export const ErrorState = { args: { semester: null, error: 'advisor API unreachable' } };