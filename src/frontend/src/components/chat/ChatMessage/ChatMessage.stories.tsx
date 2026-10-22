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

/** Advisor reply with markdown + single-newline breaks (FC27 plan shifts). */
export const AdvisorMarkdown = {
  args: {
    message: {
      id: 'm2b',
      role: 'advisor' as const,
      text:
        'That works, and graduation doesn\'t move. **Two courses shift** into later semesters:\n\n' +
        '- Spring 2027: 15 hrs \u2192 **9 hrs**\n' +
        '- Fall 2027: 12 hrs \u2192 **15 hrs**\n\n' +
        'CSE 4380 stays in Spring.\nCSE 4385 requires it in Fall 2027.',
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
/** FC39: deterministic checks streamed in while the answer is still being written. */
export const AdvisorWithChecks = {
  args: {
    message: {
      id: 'm3',
      role: 'advisor' as const,
      text: '',
      checks: [
        { kind: 'step' as const, course: null, checkId: '', description: 'SQLite: read your enrollment records (7 classes)', passed: null, reason: null },
        { kind: 'check' as const, course: '4380', checkId: 'FC29', description: 'Prerequisites met', passed: true, reason: null },
        { kind: 'check' as const, course: '4380', checkId: 'FC30', description: 'Not already passed', passed: true, reason: null },
        { kind: 'check' as const, course: '4385', checkId: 'FC29', description: 'Prerequisites met', passed: false, reason: 'Missing CSE 4380' },
      ],
    },
  },
};
