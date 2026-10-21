import type { Meta } from '@storybook/react-vite';
import SemesterCard from './SemesterCard';
import type { CourseCatalog } from '../../../api/types';

/** Real seed data (data/course-desc.jsonl) — never invented courses
    (grounded-UI rule). Credit hours are mock metadata from api/plans. */
const CATALOG_FIXTURE: CourseCatalog = {
  '3310': { id: '3310', title: 'FUNDAMENTALS OF SOFTWARE ENGINEERING', creditHours: 3 },
  '3320': { id: '3320', title: 'OPERATING SYSTEMS', creditHours: 3 },
  '3318': { id: '3318', title: 'ALGORITHMS & DATA STRUCTURES', creditHours: 3 },
  '3380': { id: '3380', title: 'LINEAR ALGEBRA FOR CSE', creditHours: 3 },
  '1301': { id: '1301', title: 'COMPUTER LITERACY', creditHours: 3 },
  '3314': { id: '3314', title: 'PROFESSIONAL PRACTICES', creditHours: 1 },
  '4380': { id: '4380', title: 'INFORMATION SECURITY', creditHours: 3 },
};

const meta = {
  title: 'Components/planner/SemesterCard',
  component: SemesterCard,
  args: {
    catalog: CATALOG_FIXTURE,
    semester: { term: 'Fall', year: 2026, courses: ['3310', '3320', '3318', '3380'], credits: 12 },
  },
} satisfies Meta<typeof SemesterCard>;

export default meta;

export const Default = {};

export const InProgress = { args: { status: 'in-progress' as const, onEdit: () => {} } };
export const Planned = { args: { status: 'planned' as const, onEdit: () => {} } };

/** Optional summer semester kept in the plan but empty (FC25) — dashed card. */
export const OptionalEmpty = {
  args: {
    status: 'optional' as const,
    semester: { term: 'Summer', year: 2027, courses: [], credits: 0 },
    emptyNote: 'Optional — not in your plan',
  },
};

export const Summer = {
  args: {
    status: 'planned' as const,
    semester: { term: 'Summer', year: 2027, courses: ['1301', '3314'], credits: 4 },
  },
};

/** A course id missing from the catalog renders the id only — no invented
    details (grounded-UI rule). */
export const UnknownCourse = {
  args: {
    semester: { term: 'Spring', year: 2029, courses: ['4380', '9999'], credits: 6 },
  },
};