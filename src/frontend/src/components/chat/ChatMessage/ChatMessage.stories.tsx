import type { Meta } from '@storybook/react-vite';
import ChatMessage from './ChatMessage';

const meta = {
  title: 'Components/chat/ChatMessage',
  component: ChatMessage,
  args: {
    message: { id: 'm1', role: 'user' as const, text: 'Can I graduate earlier if I take summer classes?' },
  },
} satisfies Meta<typeof ChatMessage>;

export default meta;

export const User = {};

export const Advisor = {
  args: {
    message: {
      id: 'm2',
      role: 'advisor' as const,
      text: 'Not by a full semester. CSE 4316 and CSE 4317 must be taken in consecutive long semesters, so Spring 2028 is your earliest finish.',
    },
  },
};

/** FC23 proposal embedded in an advisor turn, awaiting decision. */
export const WithPendingAction = {
  args: {
    message: {
      id: 'm6',
      role: 'advisor' as const,
      text: 'Keep CSE 4380, CSE 4382, and CSE 3330 in Spring 2027. Want me to add CSE 4309 to fill the freed hours?',
      action: {
        summary: 'Add CSE 4309 Fundamentals of Machine Learning to Spring 2027',
        detail: 'Fits at 15 of 18 credit hours.',
      },
    },
    actionStatus: 'pending' as const,
  },
};

export const WithConfirmedAction = {
  args: {
    message: {
      id: 'm6',
      role: 'advisor' as const,
      text: 'Done — CSE 4309 is staged for Spring 2027 (demo).',
      action: { summary: 'Add CSE 4309 Fundamentals of Machine Learning to Spring 2027' },
    },
    actionStatus: 'confirmed' as const,
    actionBusy: true,
  },
};

export const WithDeclinedAction = {
  args: {
    message: {
      id: 'm6',
      role: 'advisor' as const,
      text: 'No changes made — CSE 4309 stays off your plan.',
      action: { summary: 'Add CSE 4309 Fundamentals of Machine Learning to Spring 2027' },
    },
    actionStatus: 'declined' as const,
  },
};