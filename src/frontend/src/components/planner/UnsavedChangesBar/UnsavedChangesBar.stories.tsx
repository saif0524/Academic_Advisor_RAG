import type { Meta } from '@storybook/react-vite';
import UnsavedChangesBar from './UnsavedChangesBar';

const meta = {
  title: 'Components/planner/UnsavedChangesBar',
  component: UnsavedChangesBar,
  args: { onDiscard: () => {}, onSave: () => {} },
} satisfies Meta<typeof UnsavedChangesBar>;

export default meta;

export const Default = {};
export const WithCount = { args: { changesCount: 2 } };
export const Busy = { args: { busy: true } };