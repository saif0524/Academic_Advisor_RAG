import type { Meta } from '@storybook/react-vite';
import ConfirmDialog from './ConfirmDialog';

const meta = {
  title: 'Components/shared/ConfirmDialog',
  component: ConfirmDialog,
  args: {
    open: true,
    title: 'Program change',
    body: (
      <>
        Switch to <strong>BS Software Engineering — Artificial Intelligence</strong>? 9 completed
        hours would no longer count toward the new degree, and expected graduation moves to Fall
        2028.
      </>
    ),
    confirmLabel: 'Confirm program change',
    cancelLabel: 'Cancel',
  },
} satisfies Meta<typeof ConfirmDialog>;

export default meta;

export const Default = {};

export const Destructive = {
  args: {
    title: 'Remove course',
    body: 'Remove CSE 4380 Information Security from your Spring 2027 draft?',
    confirmLabel: 'Remove course',
    danger: true,
  },
};

export const Busy = { args: { busy: true } };

export const Closed = { args: { open: false } };