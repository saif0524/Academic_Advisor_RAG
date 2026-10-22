import type { Meta } from '@storybook/react-vite';
import PlanRoadmap from './PlanRoadmap';
import type { CourseCatalog, PlanDetail } from '../../../api/types';

/** Real seed data; credit hours are mock metadata. */
const CATALOG_FIXTURE: CourseCatalog = {
  '1105': { id: '1105', title: 'INTRODUCTION TO COMPUTER SCIENCE AND ENGINEERING.', creditHours: 2 },
  '1311': { id: '1311', title: 'INTRODUCTION TO PROGRAMMING FOR ENGINEERS', creditHours: 3 },
  '2440': { id: '2440', title: 'CIRCUIT ANALYSIS', creditHours: 3 },
  '2312': { id: '2312', title: 'COMPUTER ORGANIZATION & ASSEMBLY LANGUAGE PROGRAMMING', creditHours: 4 },
  '2315': { id: '2315', title: 'DISCRETE STRUCTURES', creditHours: 3 },
  '1301': { id: '1301', title: 'COMPUTER LITERACY', creditHours: 3 },
  '3314': { id: '3314', title: 'PROFESSIONAL PRACTICES', creditHours: 1 },
};

const PLAN_FIXTURE: PlanDetail = {
  plan_id: 'mock-plan-0001',
  student_id: 'stu-0001',
  target_major: 'BS in Computer Science',
  concentration: 'Cybersecurity',
  includes_summer: true,
  semester_count: 2,
  created_at: '2026-10-20T18:30:00.000Z',
  semesters: [
    { term: 'Fall', year: 2026, courses: ['1105', '1311', '2440'], credits: 8 },
    { term: 'Summer', year: 2027, courses: ['1301', '3314'], credits: 4 },
  ],
};

const meta = {
  title: 'Components/planner/PlanRoadmap',
  component: PlanRoadmap,
  args: { plan: PLAN_FIXTURE, catalog: CATALOG_FIXTURE, note: null },
} satisfies Meta<typeof PlanRoadmap>;

export default meta;

export const Default = {};
export const Editable = { args: { onEditSemester: () => {} } };
export const WithNote = { args: { note: 'Mock preview: CSE coursework only — the full plan adds general education, math, and physics.' } };
export const NoPlan = { args: { plan: null } };
export const EmptyPlan = {
  args: { plan: { ...PLAN_FIXTURE, semesters: [] } },
};