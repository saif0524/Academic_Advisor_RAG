import type { Meta, StoryObj } from '@storybook/react-vite';
import MajorSpecSelector from './MajorSpecSelector';
import { expect, fireEvent } from 'storybook/test';

const OPTIONS_FIXTURE = {
  majors: [
    { name: 'BS in Computer Science', concentrations: ['Cybersecurity', 'Artificial Intelligence'] },
    { name: 'BS in Software Engineering', concentrations: ['Cybersecurity', 'Artificial Intelligence'] },
  ],
};

const meta = {
  title: 'Components/planner/MajorSpecSelector',
  component: MajorSpecSelector,
  args: {
    options: OPTIONS_FIXTURE,
    major: '',
    concentration: '',
    includeSummer: false,
    onSelectionChange: () => {},
    onGenerate: () => {},
    canGenerate: false,
    disabled: false,
  },
} satisfies Meta<typeof MajorSpecSelector>;

export default meta;

export const Default: StoryObj<typeof MajorSpecSelector> = {};

export const Ready: StoryObj<typeof MajorSpecSelector> = {
  args: {
    major: 'BS in Computer Science',
    concentration: 'Cybersecurity',
    canGenerate: true,
  },
};

export const Disabled: StoryObj<typeof MajorSpecSelector> = { args: { disabled: true } };
export const NoOptions: StoryObj<typeof MajorSpecSelector> = { args: { options: null } };

/** Selecting a major enables the generate action (FC1/FC2 form contract). */
export const SelectsMajor: StoryObj<typeof MajorSpecSelector> = {
  play: async ({ canvas }) => {
    fireEvent.change(canvas.getByLabelText('Major'), { target: { value: 'BS in Computer Science' } });
    await expect(canvas.getByRole('button', { name: 'Generate plan' })).toBeVisible();
  },
};