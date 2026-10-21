import type { Meta } from '@storybook/react-vite';
import ConversationListItem from './ConversationListItem';
import type { Conversation } from '../../../api/types';

const ITEMS_FIXTURE: Conversation[] = [
  { id: 'conv-1', title: 'Graduating early with summer classes', date: 'Today', snippet: 'Can I graduate earlier if I take summer classes?' },
  { id: 'conv-2', title: 'Security electives for Spring 2027', date: 'Today', snippet: 'Two fit your schedule — prereqs and conflicts…' },
  { id: 'conv-3', title: 'What does CSE 4380 cover?', date: 'Yesterday', snippet: 'Hands-on security intro; prerequisite for CSE 4381…' },
];

const meta = {
  title: 'Components/chat/ConversationListItem',
  component: ConversationListItem,
  args: { item: ITEMS_FIXTURE[0], active: false, onSelect: () => {} },
} satisfies Meta<typeof ConversationListItem>;

export default meta;

export const Default = {};
export const Active = { args: { active: true } };
export const WithoutSnippet = {
  args: { item: { id: 'x', title: 'Untitled conversation', date: 'Oct 12' } as Conversation },
};