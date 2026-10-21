import type { Meta } from '@storybook/react-vite';
import ActionConfirmationCard from './ActionConfirmationCard';

const meta = {
  title: 'Components/chat/ActionConfirmationCard',
  component: ActionConfirmationCard,
  args: {
    action: {
      summary: 'Add CSE 4309 Fundamentals of Machine Learning to Spring 2027',
      detail: 'Fits at 15 of 18 credit hours; no prerequisite records to satisfy (FC29).',
    },
    status: 'pending' as const,
    onConfirm: () => {},
    onDecline: () => {},
  },
} satisfies Meta<typeof ActionConfirmationCard>;

export default meta;

export const Pending = {};
export const Busy = { args: { busy: true } };
export const Confirmed = { args: { status: 'confirmed' as const, busy: true } };
export const Declined = { args: { status: 'declined' as const } };