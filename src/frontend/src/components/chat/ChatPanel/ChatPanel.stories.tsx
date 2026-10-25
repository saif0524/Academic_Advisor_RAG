import type { Meta, StoryObj } from '@storybook/react-vite';
import ChatPanel from './ChatPanel';
import type { ChatMessage, Conversation, ProposalDecision } from '../../../api/types';
import { expect, userEvent } from 'storybook/test';

/** Instant fixtures — stories never hit the real api defaults. The message
    thread demonstrates FC27 continuity; the last advisor turn carries the
    FC23 proposal in pending state. */
const MESSAGES_FIXTURE: ChatMessage[] = [
  { id: 'm1', role: 'user', text: 'Can I graduate earlier if I take summer classes?' },
  {
    id: 'm2',
    role: 'advisor',
    text: 'Not by a full semester. CSE 4316 and CSE 4317 must be taken in consecutive long semesters, so Spring 2028 is your earliest finish.',
  },
  {
    id: 'm6',
    role: 'advisor',
    text: 'Want me to add CSE 4309 to fill the freed hours?',
    action: {
      summary: 'Add CSE 4309 Fundamentals of Machine Learning to Spring 2027',
      detail: 'Fits at 15 of 18 credit hours.',
    },
  },
];

const CONVERSATIONS_FIXTURE: Conversation[] = [
  { id: 'conv-1', title: 'Graduating early with summer classes', date: '2026-10-20', snippet: 'Can I graduate earlier…' },
  { id: 'conv-2', title: 'Security electives for Spring 2027', date: '2026-10-20', snippet: 'Two fit your schedule…' },
  { id: 'conv-3', title: 'What does CSE 4380 cover?', date: '2026-10-19', snippet: 'Hands-on security intro…' },
];

const SEAMS = {
  loadConversations: () => Promise.resolve(CONVERSATIONS_FIXTURE),
  loadMessages: () => Promise.resolve(MESSAGES_FIXTURE),
  sendMessage: (text: string) =>
    Promise.resolve({ id: 'reply', role: 'advisor' as const, text: `Demo reply to: "${text}"` }),
  respondToProposal: (messageId: string, decision: ProposalDecision) =>
    Promise.resolve({
      messageId,
      decision,
      reply:
        decision === 'confirmed'
          ? 'Done — CSE 4309 is staged for Spring 2027 (demo). Save the plan on the Timeline to keep it.'
          : 'No changes made — CSE 4309 stays off your plan.',
    }),
};

const meta = {
  title: 'Components/chat/ChatPanel',
  component: ChatPanel,
  args: { onClose: () => {}, ...SEAMS },
} satisfies Meta<typeof ChatPanel>;

export default meta;

export const ConversationView: StoryObj<typeof ChatPanel> = {};

export const HistoryMode: StoryObj<typeof ChatPanel> = {
  play: async ({ canvas }) => {
    await userEvent.click(canvas.getByRole('button', { name: /previous chats/i }));
    await canvas.findByText('What does CSE 4380 cover?');
  },
};

/** FC23 gate: Confirm resolves the proposal and appends the advisor turn. */
export const ConfirmProposal: StoryObj<typeof ChatPanel> = {
  play: async ({ canvas }) => {
    const confirm = await canvas.findByRole('button', { name: 'Confirm' });
    await userEvent.click(confirm);
    await expect(await canvas.findByText(/Done — CSE 4309/s)).toBeVisible();
  },
};

export const DeclineProposal: StoryObj<typeof ChatPanel> = {
  play: async ({ canvas }) => {
    const decline = await canvas.findByRole('button', { name: 'No thanks' });
    await userEvent.click(decline);
    await expect(await canvas.findByText(/No changes made/s)).toBeVisible();
  },
};

/** Send flow: type + Enter appends the user turn, then the canned reply. */
export const SendMessage: StoryObj<typeof ChatPanel> = {
  play: async ({ canvas }) => {
    await userEvent.type(canvas.getByLabelText('Message to the advisor'), 'What does CSE 4380 cover?');
    await userEvent.keyboard('{Enter}');
    await expect(await canvas.findByText(/Demo reply to/)).toBeVisible();
  },
};

/** Export: the Markdown transcript carries each advisor turn's check statuses
    (✅ passed · ❌ failed · ❔ skipped). The spy replaces the browser download. */
export const ExportTranscript: StoryObj<typeof ChatPanel> = {
  args: {
    loadMessages: () => Promise.resolve<ChatMessage[]>([
      { id: 'e1', role: 'user', text: 'Can I take CSE 4308 next semester?' },
      {
        id: 'e2',
        role: 'advisor',
        text: 'Not yet — CSE 3318 is a prerequisite you have not completed.',
        checks: [
          { kind: 'step', course: null, checkId: '', description: 'Looked up CSE 4308 in SQLite', passed: null, reason: null },
          { kind: 'check', course: '4308', checkId: 'FC29', description: 'Prerequisites satisfied', passed: false, reason: 'Not satisfied: 3318' },
          { kind: 'check', course: '4308', checkId: 'FC30', description: 'Not already passed', passed: true, reason: 'No passing record' },
          { kind: 'check', course: '4308', checkId: 'FC31', description: 'No schedule conflict', passed: null, reason: 'Skipped: no specific section was given' },
        ],
      },
    ]),
    saveExport: (filename: string, markdown: string) => {
      document.body.dataset.exportName = filename;
      document.body.dataset.exportBody = markdown;
    },
  },
  play: async ({ canvas }) => {
    await userEvent.click(await canvas.findByRole('button', { name: /export this chat/i }));
    await expect(document.body.dataset.exportName).toMatch(/^advisor-chat-.*\.md$/);
    const body = document.body.dataset.exportBody ?? '';
    await expect(body).toContain('❌ failed');
    await expect(body).toContain('✅ passed');
    await expect(body).toContain('❔ skipped');
    await expect(body).toContain('Not satisfied: 3318');
  },
};

export const LoadError: StoryObj<typeof ChatPanel> = {
  args: {
    loadMessages: () => Promise.reject(new Error('advisor API unreachable')),
    loadConversations: () => Promise.reject(new Error('advisor API unreachable')),
  },
};