/**
 * Advisor-chat API service — LIVE implementations (FC22–FC24, FC27, FC34).
 *
 * Backed by the FastAPI chat surface (src/server/routers/chat.py):
 *   getConversations()          → GET  /chat/sessions
 *   getMessages(id)             → GET  /chat/messages?session_id={id}
 *   deleteConversation(id)      → DELETE /chat/sessions/{id}
 *   sendMessage(text, session)  → POST /chat/messages
 *   respondToProposal(id, dec)  → POST /chat/messages (+confirmed/cancelled)
 *
 * Both surfaces (this drawer AND the search page's answer card) call the
 * SAME agent — one advisor, one grounded-answers pipeline (FC22).
 * FC23 confirm-before-acting: server proposals only become applied actions
 * through an explicit decision request carrying the action id.
 */

import { request, streamRequest } from './client';
import type {
  ChatMessage,
  Conversation,
  ProposalDecision,
  ProposalResponse,
  StreamCheck,
} from './types';

/** Server shapes (src/server/schemas/chat.py) — mirrors of the Pydantic DTOs. */
interface ChatSessionsResponse {
  results: { session_id: string; title: string; created_at: string | null; last_active_at: string | null }[];
  count: number;
}
interface ChatHistoryResponse {
  session_id: string;
  student_id: string;
  messages: {
    role: 'user' | 'assistant';
    content: string;
    created_at: string | null;
    /** Checks that ran for this advisor turn (FC39), when the server recorded them. */
    checks?: {
      type: 'check' | 'step'; course: string | null; check_id: string | null;
      description: string; passed: boolean | null; reason: string | null;
    }[] | null;
  }[];
}
interface PendingActionDto {
  action_id: string;
  action_type: string;
  description: string;
}
interface ChatMessageReplyDto {
  session_id: string;
  student_id: string;
  reply: string;
  pending_action?: PendingActionDto | null;
}

/** The session the drawer is actively conversing in (module state — the
    server continues the student's active session when omitted (FC27/FC34)). */
let activeSessionId: string | null = null;

/** The session the drawer is conversing in (used to label exports), or null. */
export function getActiveSessionId(): string | null {
  return activeSessionId;
}

/** Conversation list grouped by date in the UI (FC34). */
export async function getConversations(): Promise<Conversation[]> {
  const response = await request<ChatSessionsResponse>('/chat/sessions');
  return response.results.map((row) => ({
    id: row.session_id,
    title: row.title,
    date: (row.last_active_at ?? row.created_at ?? '').slice(0, 10),
    snippet: undefined,
  }));
}

/** Permanently delete one conversation (DELETE /chat/sessions/{id}, FC41). */
export async function deleteConversation(conversationId: string): Promise<void> {
  await request<void>(`/chat/sessions/${encodeURIComponent(conversationId)}`, { method: 'DELETE' });
  if (activeSessionId === conversationId) activeSessionId = null;
}

/** Start a new empty conversation and make it the send target (POST /chat/sessions). */
export async function createConversation(): Promise<string> {
  const response = await request<ChatHistoryResponse>('/chat/sessions', { method: 'POST' });
  activeSessionId = response.session_id;
  return response.session_id;
}

/** Load one conversation's turns (FC34) and remember it as the send target.
    An empty id means "the student's active session" (server-side FC27/FC34).
    The server's OPEN pending proposal (FC23) rides back on the last advisor
    turn so the confirmation card survives reloads. */
export async function getMessages(conversationId: string): Promise<ChatMessage[]> {
  const path = conversationId
    ? `/chat/messages?session_id=${encodeURIComponent(conversationId)}`
    : '/chat/messages';
  const response = await request<ChatHistoryResponse & { pending_action?: PendingActionDto | null }>(path);
  activeSessionId = conversationId || response.session_id;
  const messages: ChatMessage[] = response.messages.map((row, index) => ({
    id: `m${index}`,
    role: row.role === 'user' ? 'user' : 'advisor',
    text: row.content,
    createdAt: row.created_at ?? undefined,
    checks: row.checks?.length
      ? row.checks.map((c) => ({
          kind: c.type, course: c.course, checkId: c.check_id ?? '',
          description: c.description, passed: c.passed, reason: c.reason,
        }))
      : undefined,
  }));
  if (response.pending_action) {
    const pending: ChatMessage['action'] = {
      summary: response.pending_action.description,
      actionId: response.pending_action.action_id,
    };
    const lastAdvisor = [...messages].reverse().find((m) => m.role === 'advisor');
    if (lastAdvisor) {
      lastAdvisor.action = lastAdvisor.action ?? pending;
    } else {
      messages.push({ id: `m${messages.length}`, role: 'advisor', text: '', action: pending });
    }
  }
  return messages;
}

/** Streamed turn events (POST /chat/messages/stream, FC39). */
type StreamEvent =
  | { type: 'check'; course: string | null; check_id: string; description: string;
      passed: boolean | null; reason: string | null }
  | { type: 'step'; description: string }
  | { type: 'token'; text: string }
  | { type: 'done'; reply: string; pending_action?: PendingActionDto | null; session_id?: string }
  | { type: 'error'; message: string };

/** Send a user message over the event stream (FC22, FC39). `onProgress`
    receives the advisor turn-so-far — deterministic checks as they run, then
    the answer text as it is written. Resolves with the final advisor turn
    (FC27/FC34 continuity; `conversationId` omitted → the active session). */
export async function sendMessage(
  text: string,
  conversationId?: string,
  onProgress?: (partial: ChatMessage) => void,
): Promise<ChatMessage> {
  const sessionTarget = conversationId ?? activeSessionId ?? undefined;
  const id = `advisor-${Date.now()}`;
  const checks: StreamCheck[] = [];
  let answer = '';
  let final: ChatMessage | null = null;
  await streamRequest<StreamEvent>(
    '/chat/messages/stream',
    { message: text, session_id: sessionTarget },
    (event) => {
      if (event.type === 'check') {
        checks.push({ kind: 'check', course: event.course, checkId: event.check_id,
          description: event.description, passed: event.passed, reason: event.reason });
      } else if (event.type === 'step') {
        checks.push({ kind: 'step', course: null, checkId: '', description: event.description,
          passed: null, reason: null });
      } else if (event.type === 'token') {
        answer += event.text;
      } else if (event.type === 'error') {
        throw new Error(event.message);
      } else {
        if (event.session_id) activeSessionId = event.session_id;
        final = {
          id, role: 'advisor', text: event.reply, checks: [...checks],
          action: event.pending_action
            ? { summary: event.pending_action.description, actionId: event.pending_action.action_id }
            : undefined,
        };
        return;
      }
      onProgress?.({ id, role: 'advisor', text: answer, checks: [...checks] });
    },
  );
  if (!final) throw new Error('The advisor stream ended before a reply arrived.');
  return final;
}

/** FC23 gate — the deterministic side "acts" only on an explicit decision.
    The decision travels as its own turn; the executor replies either way. */
export async function respondToProposal(
  actionId: string,
  decision: ProposalDecision,
  conversationId?: string,
): Promise<ProposalResponse> {
  const sessionTarget = conversationId ?? activeSessionId ?? undefined;
  const response = await request<ChatMessageReplyDto>('/chat/messages', {
    method: 'POST',
    body: {
      message: decision === 'confirmed' ? 'Confirmed' : 'Cancelled',
      session_id: sessionTarget,
      ...(decision === 'confirmed'
        ? { confirmed_action_id: actionId }
        : { cancelled_action_id: actionId }),
    },
  });
  if (response.session_id) activeSessionId = response.session_id;
  return { messageId: actionId, decision, reply: response.reply };
}