import type { Meta } from '@storybook/react-vite';
import ProgressBar from './ProgressBar';

const meta = {
  title: 'Components/shared/ProgressBar',
  component: ProgressBar,
} satisfies Meta<typeof ProgressBar>;

export default meta;

/** Single fill — per-semester credit cap display (FC32). */
export const Single = {
  args: { value: 15, max: 18, label: 'Semester credit hours of 18 cap' },
};

/** Stacked segments + legend — home degree progress (FC19). */
export const StackedWithLegend = {
  args: {
    segments: [
      { key: 'completed', label: 'Completed', value: 66, variant: 'completed' },
      { key: 'inprogress', label: 'In progress', value: 12, variant: 'in-progress' },
      { key: 'planned', label: 'Planned', value: 42, variant: 'planned' },
    ],
    showLegend: true,
    label: 'Degree progress: 66 of 120 credit hours',
  },
};

export const Empty = { args: { value: 0, max: 120, label: 'No progress yet' } };