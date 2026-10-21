import PlanRoadmap from './PlanRoadmap';

/* Fixture mirrors the mock contracts in src/api/plans.js (real seed course
   ids/titles; credit hours are mock metadata). */
const CATALOG_FIXTURE = {
  1105: { id: '1105', title: 'INTRODUCTION TO COMPUTER SCIENCE AND ENGINEERING.', creditHours: 2 },
  1311: { id: '1311', title: 'INTRODUCTION TO PROGRAMMING FOR ENGINEERS', creditHours: 3 },
  2440: { id: '2440', title: 'CIRCUIT ANALYSIS', creditHours: 3 },
  1301: { id: '1301', title: 'COMPUTER LITERACY', creditHours: 3 },
  3314: { id: '3314', title: 'PROFESSIONAL PRACTICES', creditHours: 1 },
  3341: { id: '3341', title: 'DIGITAL LOGIC DESIGN II', creditHours: 3 },
  2315: { id: '2315', title: 'DISCRETE STRUCTURES', creditHours: 3 },
  3318: { id: '3318', title: 'ALGORITHMS & DATA STRUCTURES', creditHours: 3 },
  3320: { id: '3320', title: 'OPERATING SYSTEMS', creditHours: 3 },
};

const PLAN_FIXTURE = {
  plan_id: 'story-plan-0001',
  student_id: 'stu-0001',
  target_major: 'BS in Computer Science',
  concentration: 'Cybersecurity',
  includes_summer: true,
  semester_count: 4,
  created_at: '2026-02-14T10:00:00.000Z',
  semesters: [
    { term: 'Fall', year: 2026, courses: ['1105', '1311'], credits: 5 },
    { term: 'Summer', year: 2027, courses: ['1301', '3314'], credits: 4 },
    { term: 'Spring', year: 2028, courses: ['2315', '3341'], credits: 6 },
    { term: 'Fall', year: 2028, courses: ['3318', '3320'], credits: 6 },
  ],
};

const NOTE = 'Mock preview: CSE coursework only — the full plan adds general education, math, and physics to the degree total.';

const meta = {
  title: 'Components/planner/PlanRoadmap',
  component: PlanRoadmap,
  args: {
    plan: PLAN_FIXTURE,
    catalog: CATALOG_FIXTURE,
    note: NOTE,
  },
};

export default meta;

export const Default = {};

export const WithoutSummer = {
  args: {
    plan: {
      ...PLAN_FIXTURE,
      includes_summer: false,
      semester_count: 3,
      semesters: PLAN_FIXTURE.semesters.filter((semester) => semester.term !== 'Summer'),
    },
  },
};

export const Empty = {
  args: { plan: { ...PLAN_FIXTURE, semester_count: 0, semesters: [] } },
};