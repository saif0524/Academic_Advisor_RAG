import SemesterCard from './SemesterCard';

/* Real seed data (data/course-desc.jsonl) — never invented courses
   (grounded-UI rule). Credit hours are mock metadata from api/plans.js. */
const CATALOG_FIXTURE = {
  1105: { id: '1105', title: 'INTRODUCTION TO COMPUTER SCIENCE AND ENGINEERING.', creditHours: 2 },
  1311: { id: '1311', title: 'INTRODUCTION TO PROGRAMMING FOR ENGINEERS', creditHours: 3 },
  2440: { id: '2440', title: 'CIRCUIT ANALYSIS', creditHours: 3 },
  1301: { id: '1301', title: 'COMPUTER LITERACY', creditHours: 3 },
  3314: { id: '3314', title: 'PROFESSIONAL PRACTICES', creditHours: 1 },
  4380: { id: '4380', title: 'INFORMATION SECURITY', creditHours: 3 },
};

const meta = {
  title: 'Components/planner/SemesterCard',
  component: SemesterCard,
  args: {
    catalog: CATALOG_FIXTURE,
    semester: {
      term: 'Fall',
      year: 2026,
      courses: ['1105', '1311', '2440'],
      credits: 8,
    },
  },
};

export default meta;

export const Default = {};

export const Summer = {
  args: {
    semester: { term: 'Summer', year: 2027, courses: ['1301', '3314'], credits: 4 },
  },
};

export const Empty = {
  args: { semester: { term: 'Spring', year: 2028, courses: [], credits: 0 } },
};

/* A course id missing from the catalog renders the id only — no invented
   details (grounded-UI rule). */
export const UnknownCourse = {
  args: {
    semester: {
      term: 'Spring',
      year: 2029,
      courses: ['4380', '9999'],
      credits: 6,
    },
  },
};