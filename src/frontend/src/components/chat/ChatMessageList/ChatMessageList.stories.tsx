import type { Meta } from '@storybook/react-vite';
import ChatMessageList from './ChatMessageList';
import type { ChatMessage } from '../../../api/types';

const THREAD_FIXTURE: ChatMessage[] = [
  { id: 'm1', role: 'user', text: 'Can I graduate earlier if I take summer classes?' },
  {
    id: 'm2',
    role: 'advisor',
    text: 'Not by a full semester. CSE 4316 and CSE 4317 must be taken in consecutive long semesters, so Spring 2028 is your earliest finish.',
  },
  { id: 'm3', role: 'user', text: 'What about taking 3 classes next semester instead?' },
  {
    id: 'm6',
    role: 'advisor',
    text: 'Keep CSE 4380, CSE 4382, and CSE 3330 in Spring 2027. Want me to add CSE 4309 to fill the freed hours?',
    action: {
      summary: 'Add CSE 4309 Fundamentals of Machine Learning to Spring 2027',
      detail: 'Fits at 15 of 18 credit hours.',
    },
  },
];

const meta = {
  title: 'Components/chat/ChatMessageList',
  component: ChatMessageList,
  args: {
    messages: THREAD_FIXTURE,
    proposal: { messageId: 'm6', status: 'pending', busy: false },
    onConfirmAction: () => {},
    onDeclineAction: () => {},
  },
} satisfies Meta<typeof ChatMessageList>;

export default meta;

export const Default = {};
export const Empty = { args: { messages: [] } };
export const NoProposal = { args: { proposal: null } };