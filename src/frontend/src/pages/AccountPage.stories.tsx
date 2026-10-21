import type { Meta, StoryObj } from '@storybook/react-vite';
import AccountPage from './AccountPage';
import type { PlanningPreferences, StudentProfile } from '../api/types';
import { expect, fireEvent, userEvent } from 'storybook/test';

const PROFILE_FIXTURE: StudentProfile = {
  studentId: 'stu-0001',
  studentIdLabel: '[ID]',
  name: 'Demo Student',
  catalogYear: '—',
  standing: '—',
  major: 'Bachelor of Science in Computer Science',
  concentration: 'Artificial Intelligence',
};

const PREFS_FIXTURE: PlanningPreferences = {
  maxCreditsPerSemester: 18,
  includeSummer: false,
  preferredClassTimes: 'Any time',
};

const OPTIONS_FIXTURE = {
  majors: [
    { name: 'Bachelor of Science in Computer Science', concentrations: ['General'] },
    { name: 'Bachelor of Science in Software Engineering', concentrations: ['General'] },
  ],
};

const SEAMS = {
  loadDependencies: () =>
    Promise.resolve({
      profile: PROFILE_FIXTURE,
      preferences: PREFS_FIXTURE,
      options: OPTIONS_FIXTURE,
      comparePlanId: 'plan-0001',
    }),
  compareFn: () =>
    Promise.resolve({
      current: {
        degree: 'Bachelor of Science in Computer Science',
        concentration: 'Artificial Intelligence',
        hoursThatCount: '54 of 81 planned hours carry over',
        hoursRemaining: '27 hours would no longer count',
        graduation: 'see current plan',
      },
      proposed: {
        degree: 'Bachelor of Science in Software Engineering',
        concentration: 'General',
        hoursThatCount: '54 planned hours carry over',
        hoursRemaining: '33 new hours required',
        graduation: 'Spring 2028',
      },
      notes: [
        '8 planned course(s) carry over (54 hours).',
        '5 planned course(s) would no longer count (27 hours).',
      ],
    }),
  confirmFn: (_major: string, _concentration: string) => Promise.resolve({ applied: true }),
  savePreferencesFn: () => Promise.resolve({ saved: true, savedAt: new Date().toISOString() }),
};

const meta = {
  title: 'Pages/AccountPage',
  component: AccountPage,
  args: SEAMS,
} satisfies Meta<typeof AccountPage>;

export default meta;

export const Default: StoryObj<typeof AccountPage> = {};

/** Wireframe 05 flow: pick a new program → comparison → confirm gate. */
export const ChangeProgramFlow: StoryObj<typeof AccountPage> = {
  play: async ({ canvas }) => {
    fireEvent.change(canvas.getByLabelText('New major'), { target: { value: 'Bachelor of Science in Software Engineering' } });
    fireEvent.change(canvas.getByLabelText('Concentration'), { target: { value: 'General' } });
    await expect(await canvas.findByText(/Plan comparison/i)).toBeVisible();
    await userEvent.click(canvas.getByRole('button', { name: /Confirm program change…/i }));
    await expect(await canvas.findByRole('dialog')).toBeVisible();
    await userEvent.click(canvas.getByRole('button', { name: 'Confirm program change' }));
    await expect(await canvas.findByText(/Program change applied/i)).toBeVisible();
  },
};

export const CancelNeverCommits: StoryObj<typeof AccountPage> = {
  play: async ({ canvas }) => {
    fireEvent.change(canvas.getByLabelText('New major'), { target: { value: 'Bachelor of Science in Software Engineering' } });
    fireEvent.change(canvas.getByLabelText('Concentration'), { target: { value: 'General' } });
    await userEvent.click(canvas.getByRole('button', { name: 'Cancel' }));
    await expect(
      await canvas.findByText('Pick a new major and concentration above to compare degree plans.'),
    ).toBeVisible();
  },
};

export const LoadError: StoryObj<typeof AccountPage> = {
  args: { loadDependencies: () => Promise.reject(new Error('advisor API unreachable')) },
};