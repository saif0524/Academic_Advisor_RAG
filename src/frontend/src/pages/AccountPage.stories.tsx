import type { Meta, StoryObj } from '@storybook/react-vite';
import AccountPage from './AccountPage';
import type { PlanningPreferences, StudentProfile } from '../api/types';
import { expect, fireEvent, userEvent } from 'storybook/test';

const PROFILE_FIXTURE: StudentProfile = {
  studentId: 'stu-0001',
  studentIdLabel: '[ID]',
  name: 'Jordan Lee',
  catalogYear: '2024-2025',
  standing: 'Junior',
  major: 'BS in Computer Science',
  concentration: 'Cybersecurity',
};

const PREFS_FIXTURE: PlanningPreferences = {
  maxCreditsPerSemester: 18,
  includeSummer: false,
  preferredClassTimes: 'Any time',
};

const SEAMS = {
  loadDependencies: () => Promise.resolve({ profile: PROFILE_FIXTURE, preferences: PREFS_FIXTURE }),
  compareFn: () =>
    Promise.resolve({
      current: {
        degree: 'BS in Computer Science',
        concentration: 'Cybersecurity',
        hoursThatCount: '81 of 81',
        hoursRemaining: '39',
        graduation: 'Spring 2028',
      },
      proposed: {
        degree: 'BS in Software Engineering',
        concentration: 'Artificial Intelligence',
        hoursThatCount: '72 of 81',
        hoursRemaining: '48',
        graduation: 'Fall 2028',
      },
      notes: [
        'Estimates from your degree audit — the advisor walks through pros and cons before you commit.',
        'Two CSE concentration courses would no longer count toward the new degree.',
      ],
    }),
  confirmFn: () => Promise.resolve({ applied: true }),
  savePreferencesFn: () => Promise.resolve({ saved: true, savedAt: new Date().toISOString() }),
};

const meta = {
  title: 'Pages/AccountPage',
  component: AccountPage,
  args: SEAMS,
} satisfies Meta<typeof AccountPage>;

export default meta;

export const Default: StoryObj<typeof AccountPage> = {};

/** Wireframe 05 flow: pick a new program → comparison → FC23 confirm gate. */
export const ChangeProgramFlow: StoryObj<typeof AccountPage> = {
  play: async ({ canvas }) => {
    fireEvent.change(canvas.getByLabelText('New major'), { target: { value: 'BS in Software Engineering' } });
    fireEvent.change(canvas.getByLabelText('Concentration'), { target: { value: 'Artificial Intelligence' } });
    await expect(await canvas.findByText(/Plan comparison/i)).toBeVisible();
    await userEvent.click(canvas.getByRole('button', { name: /Confirm program change…/i }));
    await expect(await canvas.findByRole('dialog')).toBeVisible();
    await userEvent.click(canvas.getByRole('button', { name: 'Confirm program change' }));
    await expect(await canvas.findByText(/Program change applied \(demo\)/i)).toBeVisible();
  },
};

export const CancelNeverCommits: StoryObj<typeof AccountPage> = {
  play: async ({ canvas }) => {
    fireEvent.change(canvas.getByLabelText('New major'), { target: { value: 'BS in Software Engineering' } });
    fireEvent.change(canvas.getByLabelText('Concentration'), { target: { value: 'Artificial Intelligence' } });
    await userEvent.click(canvas.getByRole('button', { name: 'Cancel' }));
    await expect(
      await canvas.findByText('Pick a new major and concentration above to compare degree plans.'),
    ).toBeVisible();
  },
};

export const LoadError: StoryObj<typeof AccountPage> = {
  args: { loadDependencies: () => Promise.reject(new Error('advisor API unreachable')) },
};