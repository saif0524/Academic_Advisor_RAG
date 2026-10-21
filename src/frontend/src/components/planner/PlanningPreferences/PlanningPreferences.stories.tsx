import type { Meta, StoryObj } from '@storybook/react-vite';
import PlanningPreferences from './PlanningPreferences';
import { userEvent } from 'storybook/test';
import type { PlanningPreferences as PlanningPreferencesData } from '../../../api/types';

const PREFS_FIXTURE: PlanningPreferencesData = {
  maxCreditsPerSemester: 18,
  includeSummer: false,
  preferredClassTimes: 'Any time',
};

const meta = {
  title: 'Components/planner/PlanningPreferences',
  component: PlanningPreferences,
  args: {
    preferences: PREFS_FIXTURE,
    onSave: async () => {},
    saving: false,
    saveError: null,
  },
} satisfies Meta<typeof PlanningPreferences>;

export default meta;

export const Default: StoryObj<typeof PlanningPreferences> = {};
export const SummerOn: StoryObj<typeof PlanningPreferences> = {
  args: { preferences: { ...PREFS_FIXTURE, includeSummer: true } },
};
export const Saving: StoryObj<typeof PlanningPreferences> = { args: { saving: true } };
export const SaveError: StoryObj<typeof PlanningPreferences> = { args: { saveError: 'advisor API unreachable' } };
export const NoPreferences: StoryObj<typeof PlanningPreferences> = { args: { preferences: null } };

/** Interactive toggle — checkbox flips the include-summer draft (FC25). */
export const ToggleSummer: StoryObj<typeof PlanningPreferences> = {
  play: async ({ canvas }) => {
    await userEvent.click(canvas.getByLabelText('Include summer sessions'));
  },
};