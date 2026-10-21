import type { Meta } from '@storybook/react-vite';
import PlanGenerator from './PlanGenerator';
import type { CourseCatalog, PlanDetail } from '../api/types';
import { expect, fireEvent } from 'storybook/test';

const CATALOG_FIXTURE: CourseCatalog = {
  '1105': { id: '1105', title: 'INTRODUCTION TO COMPUTER SCIENCE AND ENGINEERING.', creditHours: 2 },
  '1311': { id: '1311', title: 'INTRODUCTION TO PROGRAMMING FOR ENGINEERS', creditHours: 3 },
  '2440': { id: '2440', title: 'CIRCUIT ANALYSIS', creditHours: 3 },
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

const OPTIONS_FIXTURE = {
  majors: [
    { name: 'BS in Computer Science', concentrations: ['Cybersecurity', 'Artificial Intelligence'] },
    { name: 'BS in Software Engineering', concentrations: ['Cybersecurity', 'Artificial Intelligence'] },
  ],
};

const SEAMS = {
  loadDependencies: () => Promise.resolve({ options: OPTIONS_FIXTURE, catalog: CATALOG_FIXTURE }),
  generatePlanFn: () => Promise.resolve(PLAN_FIXTURE),
};

const meta = {
  title: 'Pages/PlanGenerator',
  component: PlanGenerator,
  args: { onNavigateBack: () => {}, ...SEAMS },
} satisfies Meta<typeof PlanGenerator>;

export default meta;

export const Default = {};

export const GenerateFlow = {
  play: async ({ canvas, userEvent }: { canvas: any; userEvent: any }) => {
    fireEvent.change(canvas.getByLabelText('Major'), { target: { value: 'BS in Computer Science' } });
    fireEvent.change(canvas.getByLabelText('Concentration'), { target: { value: 'Cybersecurity' } });
    await userEvent.click(canvas.getByRole('button', { name: 'Generate plan' }));
    await expect(await canvas.findByText(/semester-by-semester roadmap/i)).toBeVisible();
  },
};

export const LoadError = {
  args: {
    loadDependencies: () => Promise.reject(new Error('advisor API unreachable')),
    generatePlanFn: () => Promise.resolve(null),
  },
};

export const NoPlanForPair = {
  args: {
    loadDependencies: () => Promise.resolve({ options: OPTIONS_FIXTURE, catalog: CATALOG_FIXTURE }),
    generatePlanFn: () => Promise.resolve(null),
  },
  play: async ({ canvas, userEvent }: { canvas: any; userEvent: any }) => {
    fireEvent.change(canvas.getByLabelText('Major'), { target: { value: 'BS in Computer Science' } });
    fireEvent.change(canvas.getByLabelText('Concentration'), { target: { value: 'Cybersecurity' } });
    await userEvent.click(canvas.getByRole('button', { name: 'Generate plan' }));
    await expect(await canvas.findByText(/No plan could be generated/i)).toBeVisible();
  },
};