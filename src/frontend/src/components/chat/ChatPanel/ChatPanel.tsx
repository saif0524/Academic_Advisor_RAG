import { useEffect, useState } from 'react';
import Button from '../../shared/Button/Button';
import Icon from '../../shared/Icon/Icon';
import ChatComposer from '../ChatComposer/ChatComposer';
import ChatMessageList from '../ChatMessageList/ChatMessageList';
import ConversationHistory from '../ConversationHistory/ConversationHistory';
import {
  getConversations as getConversationsViaApi,
  getMessages as getMessagesViaApi,
  respondToProposal as respondToProposalViaApi,
  sendMessage as sendMessageViaApi,
} from '../../../api/chat';
import type { ChatMessage, Conversation, ProposalDecision } from '../../../api/types';
import './ChatPanel.css';

export interface ChatSeams {
  /** DI seams defaulting to the api service (stories inject fixtures). */
  loadConversations?: () => Promise<Conversation[]>;
  loadMessages?: (conversationId: string) => Promise<ChatMessage[]>;
  sendMessage?: (text: string) => Promise<ChatMessage>;
  respondToProposal?: (messageId: string, decision: ProposalDecision) => Promise<{ messageId: string; decision: ProposalDecision; reply: string }>;
}

interface ChatPanelProps extends ChatSeams {
  /** Drawer dismiss (app shell owns the open state). */
  onClose?: () => void;
  initialConversationId?: string;
}

type ThreadState = {
  id: string;
  messages: ChatMessage[] | null;
  loading: boolean;
  error: string | null;
};

/**
 * Right-side advisor chat drawer (wireframes 04–06; FC22–FC24, FC27–FC28,
 * FC34–FC35). Conversation mode renders the thread + composer; history mode
 * lists previous conversations (FC34) and loads one (FC27 continuity). The
 * FC23 confirmation gate lives in the thread via ChatMessageList's proposal
 * state — actions only proceed after an explicit decision.
 *
 * Data comes through the api seam (mocked in api/chat — no live LLM until
 * the agent zone is wired). Stories inject instant fixtures via the DI props.
 */
export default function ChatPanel({
  onClose,
  loadConversations = getConversationsViaApi,
  loadMessages = getMessagesViaApi,
  sendMessage = sendMessageViaApi,
  respondToProposal = respondToProposalViaApi,
  initialConversationId = 'conv-1',
}: ChatPanelProps) {
  const [activeId, setActiveId] = useState(initialConversationId);
  const [mode, setMode] = useState<'conversation' | 'history'>('conversation');
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [conversationsError, setConversationsError] = useState<string | null>(null);

  /* Thread state keyed by activeId — the effect resynchronizes React state
     with the external api (cleanup guards out-of-order resolutions). */
  const [thread, setThread] = useState<ThreadState>({ id: activeId, messages: null, loading: true, error: null });
  const [sending, setSending] = useState(false);

  /* FC23 decision state for whichever message carries `action`. */
  const [proposal, setProposal] = useState<{ messageId: string; status: 'pending' | 'confirmed' | 'declined'; busy: boolean } | null>(null);

  useEffect(() => {
    // External system: the chat api seam. The selection handler (event)
    // resets/loading-gates sync state; this effect writes only post-await
    // and reruns only when the selected conversation (or DI seam) changes.
    let cancelled = false;
    const run = async () => {
      try {
        const loaded = await loadMessages(activeId);
        if (!cancelled) {
          setThread({ id: activeId, messages: loaded, loading: false, error: null });
          // FC23: a proposal in the restored thread starts pending and needs
          // the explicit decision; track it next to the decision state.
          const proposed = loaded.find((message) => Boolean(message.action));
          setProposal(proposed ? { messageId: proposed.id, status: 'pending', busy: false } : null);
        }
      } catch (error) {
        if (!cancelled) {
          setThread({
            id: activeId,
            messages: null,
            loading: false,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [activeId, loadMessages]);

  /* History list loads lazily, only when opened (FC34 list view). */
  const openHistory = async () => {
    setMode('history');
    if (conversations !== null) return;
    setConversationsError(null);
    try {
      setConversations(await loadConversations());
    } catch (error) {
      setConversationsError(error instanceof Error ? error.message : String(error));
    }
  };

  const handleSend = async (text: string) => {
    setSending(true);
    setThread((current) => ({
      ...current,
      messages: [...(current.messages ?? []), { id: `user-${Date.now()}`, role: 'user', text }],
    }));
    try {
      const reply = await sendMessage(text);
      setThread((current) => ({ ...current, messages: [...(current.messages ?? []), reply] }));
    } catch (error) {
      setThread((current) => ({ ...current, error: error instanceof Error ? error.message : String(error) }));
    } finally {
      setSending(false);
    }
  };

  /* FC23 gate: the deterministic side only "acts" on the explicit decision.
     The mock resolves with a follow-up advisor turn either way. */
  const decide = async (decision: ProposalDecision) => {
    if (!proposal) return;
    setProposal({ ...proposal, busy: true });
    try {
      const response = await respondToProposal(proposal.messageId, decision);
      setProposal({ messageId: proposal.messageId, status: decision, busy: false });
      setThread((current) => ({
        ...current,
        messages: [...(current.messages ?? []), { id: `reply-${Date.now()}`, role: 'advisor', text: response.reply }],
      }));
    } catch (error) {
      setProposal({ messageId: proposal.messageId, status: 'pending', busy: false });
      setThread((current) => ({ ...current, error: error instanceof Error ? error.message : String(error) }));
    }
  };

  return (
    <div className="chat-panel">
      <header className="chat-panel-header">
        <span className="chat-panel-brand">
          <Icon name="chat" size={16} />
          Advisor
        </span>
        <div className="chat-panel-header-actions">
          <Button variant="ghost" onClick={mode === 'conversation' ? openHistory : () => setMode('conversation')}>
            {mode === 'conversation' ? (
              <>
                <Icon name="list" size={14} /> Previous chats
              </>
            ) : (
              'Back to conversation'
            )}
          </Button>
          <Button variant="ghost" iconOnly onClick={onClose} aria-label="Close advisor chat">
            <Icon name="close" size={14} />
          </Button>
        </div>
      </header>

      {mode === 'history' ? (
        <ConversationHistory
          conversations={conversations}
          activeId={activeId}
          onSelect={(id) => {
            if (id !== activeId) {
              setActiveId(id);
              setThread({ id, messages: null, loading: true, error: null });
              setProposal(null);
            }
            setMode('conversation');
          }}
          loading={conversations === null && conversationsError === null}
          error={conversationsError}
          onBack={() => setMode('conversation')}
        />
      ) : (
        <div className="chat-panel-thread">
          {thread.loading ? (
            <p className="chat-panel-state" aria-busy="true">Loading the conversation…</p>
          ) : (
            <ChatMessageList
              messages={thread.messages}
              proposal={proposal}
              onConfirmAction={() => decide('confirmed')}
              onDeclineAction={() => decide('declined')}
            />
          )}
          {thread.error ? (
            <p className="chat-panel-state chat-panel-state--error" role="alert">
              The last turn failed: {thread.error}
            </p>
          ) : null}
          <ChatComposer onSend={handleSend} busy={sending} />
          <p className="chat-panel-note">Demo replies — no live advisor agent behind this panel yet.</p>
        </div>
      )}
    </div>
  );
}