import type { Meta } from '@storybook/react-vite';
import AppShell from './AppShell';
import ChatPanel from '../../chat/ChatPanel/ChatPanel';

const meta = {
  title: 'Components/shared/AppShell',
  component: AppShell,
  args: {
    active: 'home' as const,
    onNavigate: () => {},
  },
  argTypes: {
    active: { control: 'radio', options: ['home', 'timeline', 'search', 'account'] },
  },
} satisfies Meta<typeof AppShell>;

export default meta;

export const ShellOnly = {
  args: { children: <p style={{ margin: 0 }}>Page content mounts here.</p> },
};

/** Drawer open with the real chat panel (stories never hit the API — the
    panel receives instant fixtures via its DI seam props). */
export const ChatDrawerOpen = {
  args: {
    chatOpen: true,
    children: <p style={{ margin: 0 }}>Page content mounts here.</p>,
    chatSlot: (
      <ChatPanel
        onClose={() => {}}
        initialConversationId="conv-1"
        loadConversations={() =>
          Promise.resolve([
            { id: 'c1', title: 'Graduating early with summer classes', date: '2026-10-20', snippet: 'Can I graduate earlier if I take summer classes?' },
          ])
        }
        loadMessages={() =>
          Promise.resolve([
            { id: 'm1', role: 'user' as const, text: 'Can I graduate earlier if I take summer classes?' },
            {
              id: 'm2',
              role: 'advisor' as const,
              text: 'Not by a full semester. CSE 4316 and CSE 4317 must be taken in consecutive long semesters, so Spring 2028 is your earliest finish.',
            },
          ])
        }
      />
    ),
  },
};