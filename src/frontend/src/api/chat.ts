/**
 * Advisor-chat API service — LIVE implementations (FC22–FC24, FC27, FC34).
 *
 * Backed by the FastAPI chat surface (src/server/routers/chat.py):
 *   getConversations()          → GET  /chat/sessions
 *   getMessages(id)             → GET  /chat/messages?session_id={id}
 *   sendMessage(text, session)  → POST /chat/messages
 *   respondToProposal(id, dec)  → POST /chat/messages (+confirmed/cancelled)
 *
 * Both surfaces (this drawer AND the search page's answer card) call the
 * SAME agent — one advisor, one grounded-answers pipeline (FC22).
 * FC23 confirm-before-acting: server proposals only become applied actions
 * through an explicit decision request carrying the action id.
 */

import { request } from './client';
import type {
  ChatMessage,
  Conversation,
  ProposalDecision,
  ProposalResponse,
} from './types';

/** Server shapes (src/server/schemas/chat.py) — mirrors of the Pydantic DTOs. */
interface ChatSessionsResponse {
  results: { session_id: string; title: string; created_at: string | null; last_active_at: string | null }[];
  count: number;
}
interface ChatHistoryResponse {
  session_id: string;
  student_id: string;
  messages: { role: 'user' | 'assistant'; content: string; created_at: string | null }[];
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

/** Send a user message; resolves with the advisor turn (FC22; FC27/FC34
    continuity). `conversationId` selects the thread when the drawer is in a
    restored conversation; omitted → the student's active session. */
export async function sendMessage(text: string, conversationId?: string): Promise<ChatMessage> {
  const sessionTarget = conversationId ?? activeSessionId ?? undefined;
  const response = await request<ChatMessageReplyDto>('/chat/messages', {
    method: 'POST',
    body: { message: text, session_id: sessionTarget },
  });
  if (response.session_id) activeSessionId = response.session_id;
  return {
    id: `advisor-${Date.now()}`,
    role: 'advisor',
    text: response.reply,
    action: response.pending_action
      ? { summary: response.pending_action.description, actionId: response.pending_action.action_id }
      : undefined,
  };
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