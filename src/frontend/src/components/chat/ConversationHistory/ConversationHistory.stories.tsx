import type { Meta, StoryObj } from '@storybook/react-vite';
import ConversationHistory from './ConversationHistory';
import type { Conversation } from '../../../api/types';
import { userEvent } from 'storybook/test';

const CONVERSATIONS_FIXTURE: Conversation[] = [
  { id: 'conv-1', title: 'Graduating early with summer classes', date: '2026-10-20', snippet: 'Can I graduate earlier…' },
  { id: 'conv-2', title: 'Security electives for Spring 2027', date: '2026-10-20', snippet: 'Two fit your schedule…' },
  { id: 'conv-3', title: 'What does CSE 4380 cover?', date: '2026-10-19', snippet: 'Hands-on security intro…' },
  { id: 'conv-4', title: 'Dropping CSE 3320 — prereq impact', date: '2026-10-06', snippet: 'CSE 4382 would need a plan adjustment…' },
];

const meta = {
  title: 'Components/chat/ConversationHistory',
  component: ConversationHistory,
  args: {
    conversations: CONVERSATIONS_FIXTURE,
    activeId: 'conv-1',
    onSelect: () => {},
    onDelete: () => {},
    onBack: () => {},
  },
} satisfies Meta<typeof ConversationHistory>;

export default meta;

export const Default: StoryObj<typeof ConversationHistory> = {};

/** Search filters the loaded list client-side (FC34 lookup mock). */
export const Searching: StoryObj<typeof ConversationHistory> = {
  play: async ({ canvas }) => {
    await userEvent.type(canvas.getByLabelText('Search previous conversations'), 'cse 4380');
  },
};

/** Empty result set after a non-matching search (explicit empty state). */
export const NoMatches: StoryObj<typeof ConversationHistory> = {
  play: async ({ canvas }) => {
    await userEvent.type(canvas.getByLabelText('Search previous conversations'), 'zzz');
  },
};

export const Loading: StoryObj<typeof ConversationHistory> = { args: { conversations: null, loading: true } };
export const ErrorState: StoryObj<typeof ConversationHistory> = {
  args: { conversations: null, error: 'advisor API unreachable' },
};
export const Empty: StoryObj<typeof ConversationHistory> = { args: { conversations: [] } };