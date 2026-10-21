import { expect, userEvent } from 'storybook/test';
import PlanGenerator from './PlanGenerator';

/* Instant fixtures (data mirrors src/api/plans.js — real seed ids/titles,
   mock credit metadata). Stories never hit the real API; the injected
   loadDependencies / generatePlanFn props are the page's DI seams. */
const OPTIONS_FIXTURE = {
  majors: [
    { name: 'BS in Computer Science', concentrations: ['Cybersecurity', 'Artificial Intelligence'] },
    {
      name: 'BS in Software Engineering',
      concentrations: ['Cybersecurity', 'Artificial Intelligence'],
    },
  ],
};

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
  2312: { id: '2312', title: 'COMPUTER ORGANIZATION & ASSEMBLY LANGUAGE PROGRAMMING', creditHours: 4 },
  2441: { id: '2441', title: 'DIGITAL LOGIC DESIGN I', creditHours: 3 },
  3380: { id: '3380', title: 'LINEAR ALGEBRA FOR CSE', creditHours: 3 },
  4308: { id: '4308', title: 'ARTIFICIAL INTELLIGENCE', creditHours: 3 },
  4309: { id: '4309', title: 'FUNDAMENTALS OF MACHINE LEARNING', creditHours: 3 },
  4311: { id: '4311', title: 'NEURAL NETWORKS AND DEEP LEARNING', creditHours: 3 },
};

const PLAN_FIXTURE = {
  plan_id: 'story-plan-0001',
  student_id: 'stu-0001',
  target_major: 'BS in Computer Science',
  concentration: 'Cybersecurity',
  includes_summer: false,
  semester_count: 4,
  created_at: '2026-02-14T10:00:00.000Z',
  semesters: [
    { term: 'Fall', year: 2026, courses: ['1105', '1311'], credits: 5 },
    { term: 'Spring', year: 2027, courses: ['2440', '2315'], credits: 6 },
    { term: 'Fall', year: 2027, courses: ['2312', '3380'], credits: 7 },
    { term: 'Spring', year: 2028, courses: ['4311', '3318', '3320'], credits: 9 },
  ],
};

const INSTANT_LOAD = async () => ({ options: OPTIONS_FIXTURE, catalog: CATALOG_FIXTURE });

const meta = {
  title: 'Pages/PlanGenerator',
  component: PlanGenerator,
};

export default meta;

export const Loading = {
  args: {
    onNavigateBack: () => {},
    loadDependencies: () => new Promise(() => {}),
  },
};

export const LoadError = {
  args: {
    onNavigateBack: () => {},
    loadDependencies: () => Promise.reject(new Error('mock load failure')),
  },
};

export const ReadyToGenerate = {
  args: {
    onNavigateBack: () => {},
    loadDependencies: INSTANT_LOAD,
    generatePlanFn: async () => PLAN_FIXTURE,
  },
};

export const Generating = {
  args: {
    onNavigateBack: () => {},
    loadDependencies: INSTANT_LOAD,
    generatePlanFn: () => new Promise(() => {}), // generation never completes → stuck
  },
  /* Drives the real flow: pick major + specialization (button stays disabled
     until both are set — one of each, FC1), then Generate. */
  play: async ({ canvas }) => {
    await userEvent.selectOptions(await canvas.findByLabelText('Major'), 'BS in Computer Science');
    await userEvent.selectOptions(
      await canvas.findByLabelText(/specialization/i),
      'Cybersecurity',
    );
    await userEvent.click(await canvas.findByRole('button', { name: /generate plan/i }));
    await expect(await canvas.findByText(/Generating your plan/i)).toBeVisible();
  },
};

export const PlanGenerated = {
  args: {
    onNavigateBack: () => {},
    loadDependencies: INSTANT_LOAD,
    generatePlanFn: async () => PLAN_FIXTURE,
  },
  play: async ({ canvas }) => {
    await userEvent.selectOptions(await canvas.findByLabelText('Major'), 'BS in Computer Science');
    await userEvent.selectOptions(
      await canvas.findByLabelText(/specialization/i),
      'Cybersecurity',
    );
    await userEvent.click(await canvas.findByRole('button', { name: /generate plan/i }));
    const roadmap = await canvas.findByText(/BS in Computer Science — Cybersecurity/);
    await expect(roadmap).toBeVisible();
    await expect(await canvas.findByText(/Fall 2026/)).toBeVisible();
  },
};

export const GenerateError = {
  args: {
    onNavigateBack: () => {},
    loadDependencies: INSTANT_LOAD,
    generatePlanFn: () => Promise.reject(new Error('mock generation failure')),
  },
  play: async ({ canvas }) => {
    await userEvent.selectOptions(await canvas.findByLabelText('Major'), 'BS in Computer Science');
    await userEvent.selectOptions(
      await canvas.findByLabelText(/specialization/i),
      'Cybersecurity',
    );
    await userEvent.click(await canvas.findByRole('button', { name: /generate plan/i }));
    await expect(await canvas.findByText(/Plan generation failed/i)).toBeVisible();
  },
};