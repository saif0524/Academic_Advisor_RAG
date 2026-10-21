/**
 * Advisor-chat API service (FC22–FC24, FC27–FC28, FC34) — MOCK
 * implementation standing in for the chat endpoints
 * (src/server/routers/chat.py, proposed FC-new-rest-api).
 *
 * Shapes mirror the future HTTP contract:
 *   getConversations()          → future GET /chat/conversations
 *   getMessages(id)             → future GET /chat/conversations/{id}/messages
 *   sendMessage(text)           → future POST /chat/conversations/{id}/messages
 *   respondToProposal(id, ok)   → future POST /chat/proposals/{id}/decision
 *
 * Grounding notes (important):
 * - Replies are CANNED, deterministic text derived only from the shared
 *   fixtures (active plan, seed catalog) — there is NO live LLM/agent yet.
 *   A real agent (FC22) classifies intent, then routes SQLite/Chroma/engine
 *   lookups; the mock just keeps the UI honest about scope.
 * - FC23 confirm-before-acting: proposals only become applied actions after
 *   the user returns an explicit `decision` via respondToProposal — the mock
 *   mirrors the interrupt-based gate the agent will enforce.
 * - Conversation history persistence (FC34) is mocked in-memory fixtures.
 */

import type {
  ChatMessage,
  Conversation,
  ProposalDecision,
  ProposalResponse,
} from './types';

const MOCK_LATENCY_MS = 600;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const CANNED_REPLIES: Record<string, string> = {
  summer:
    'Not by a full semester. CSE 4316 and CSE 4317 must be taken in consecutive long ' +
    'semesters, so Spring 2028 is your earliest finish. A summer course would lighten ' +
    'Fall 2027 and Spring 2028 to 9 hrs each.',
  threeClasses:
    'That works, and graduation doesn\'t move. One course shifts later:\n' +
    'Spring 2027  12 hrs → 9 hrs\n' +
    'Summer 2027  —  → 3 hrs\n' +
    'Fall 2027    12 hrs → 12 hrs\n' +
    'CSE 4380 stays in Spring 2027 — CSE 4381 in Fall 2027 needs it in an earlier semester.',
  drop:
    'Watch the prereq chain: CSE 4382 — Secure Programming (Spring 2027) lists CSE 3320 ' +
    'as a prerequisite, and you are taking it this semester. If you drop it, CSE 4382 ' +
    'would need a plan adjustment.',
  courseCover:
    'CSE 4380 — Information Security is a hands-on introduction to security: system ' +
    'security, buffer overflows, cryptography basics, firewalls and intrusion detection. ' +
    'It is the prerequisite for CSE 4381, which your plan needs in Fall 2027.',
  fallback:
    'Demo replies only — the advisor agent is not wired yet (no LLM behind this panel). ' +
    'I can echo your plan and the CSE catalog fixtures: try "What about taking 3 classes ' +
    'next semester instead?" or "What does CSE 4380 cover?".',
};

function replyFor(text: string): string {
  const q = (text ?? '').toLowerCase();
  if (q.includes('summer') || q.includes('graduate earlier')) return CANNED_REPLIES.summer;
  if (q.includes('3 classes') || q.includes('three classes') || q.includes('instead')) {
    return CANNED_REPLIES.threeClasses;
  }
  if (q.includes('drop')) return CANNED_REPLIES.drop;
  if (q.includes('4380') || q.includes('cover')) return CANNED_REPLIES.courseCover;
  return CANNED_REPLIES.fallback;
}

/** Conversation list grouped by date in the UI (FC34). */
export async function getConversations(): Promise<Conversation[]> {
  await sleep(MOCK_LATENCY_MS);
  return [
    { id: 'conv-1', title: 'Graduating early with summer classes', date: '2026-10-20', snippet: 'Can I graduate earlier if I take summer classes?' },
    { id: 'conv-2', title: 'Which security electives fit Spring 2027?', date: '2026-10-20', snippet: 'Two fit your schedule — details on prereqs and conflicts…' },
    { id: 'conv-3', title: 'What does CSE 4380 cover?', date: '2026-10-19', snippet: 'Hands-on security intro; prerequisite for CSE 4381…' },
    { id: 'conv-4', title: 'Dropping CSE 3320 — impact on prereqs', date: '2026-10-14', snippet: 'CSE 4382 would need a plan adjustment…' },
    { id: 'conv-5', title: 'Switching to Software Engineering?', date: '2026-10-12', snippet: 'We compared both plans side by side (FC26)…' },
  ];
}

/** The active thread — demonstrates multi-turn continuity (FC27) and the
    FC23 action proposal awaiting an explicit decision. */
export async function getMessages(conversationId: string): Promise<ChatMessage[]> {
  await sleep(MOCK_LATENCY_MS);
  if (conversationId !== 'conv-1') {
    return [
      { id: `${conversationId}-u1`, role: 'user', text: '(Earlier conversation restored from history — FC34.)' },
      { id: `${conversationId}-a1`, role: 'advisor', text: 'This is the saved transcript for that conversation.' },
    ];
  }
  return [
    { id: 'm1', role: 'user', text: 'Can I graduate earlier if I take summer classes?' },
    { id: 'm2', role: 'advisor', text: CANNED_REPLIES.summer },
    { id: 'm3', role: 'user', text: 'What about taking 3 classes next semester instead?' },
    { id: 'm4', role: 'advisor', text: CANNED_REPLIES.threeClasses },
    { id: 'm5', role: 'user', text: 'Which 3 should I keep? Any time conflicts?' },
    {
      id: 'm6',
      role: 'advisor',
      text: 'Keep CSE 4380, CSE 4382, and CSE 3330 in Spring 2027 — no meeting-time ' +
        'overlaps on record. Want me to add CSE 4309 to fill the freed hours?',
      action: {
        summary: 'Add CSE 4309 Fundamentals of Machine Learning to Spring 2027',
        detail: 'Fits at 15 of 18 credit hours; no prerequisite records to satisfy (FC29).',
      },
    },
  ];
}

/** FC23 gate — the deterministic side "acts" only on an explicit decision. */
export async function respondToProposal(messageId: string, decision: ProposalDecision): Promise<ProposalResponse> {
  await sleep(MOCK_LATENCY_MS);
  const reply =
    decision === 'confirmed'
      ? 'Done — CSE 4309 is staged for Spring 2027 (demo). Save the plan on the Timeline to keep it.'
      : 'No changes made — CSE 4309 stays off your plan.';
  return { messageId, decision, reply };
}

/** Send a user message; resolves with the canned advisor turn (FC22 mock,
    FC27 conversation state). */
export async function sendMessage(text: string): Promise<ChatMessage> {
  await sleep(MOCK_LATENCY_MS);
  return {
    id: `m${Date.now()}`,
    role: 'advisor',
    text: replyFor(text),
  };
}