import { useEffect, useRef } from 'react';
import ChatMessage from '../ChatMessage/ChatMessage';
import type { ChatMessage as ChatMessageType, ProposalDecision } from '../../../api/types';
import type { ProposalStatus } from '../ActionConfirmationCard/ActionConfirmationCard';
import './ChatMessageList.css';

export interface MessageProposal {
  messageId: string;
  status: ProposalStatus;
  busy: boolean;
}

interface ChatMessageListProps {
  messages: ChatMessageType[] | null;
  /** Decision state for the message carrying `action`. */
  proposal?: MessageProposal | null;
  onConfirmAction?: () => void;
  onDeclineAction?: (decision: ProposalDecision) => void;
  emptyText?: string;
}

/**
 * Scrollable advisor-thread body (FC22 conversation rendering, FC27 turns).
 * Auto-scrolls to the newest message on change (useRef + useEffect with
 * correct deps). Renders the FC23 card inside advisor turns via ChatMessage.
 */
export default function ChatMessageList({
  messages,
  proposal = null,
  onConfirmAction,
  onDeclineAction,
  emptyText = 'No messages yet — say hello below.',
}: ChatMessageListProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // External system: browser scroll position. Dep = message count.
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages?.length]);

  if (!messages || messages.length === 0) {
    return <p className="chat-message-list-empty">{emptyText}</p>;
  }
  return (
    <div className="chat-message-list" aria-label="Conversation">
      {messages.map((message) => {
        const isProposal = Boolean(message.action);
        const isOwnProposal = isProposal && proposal?.messageId === message.id;
        return (
          <ChatMessage
            key={message.id}
            message={message}
            actionStatus={isOwnProposal ? proposal.status : undefined}
            actionBusy={isOwnProposal ? proposal.busy : false}
            onConfirmAction={isOwnProposal ? onConfirmAction : undefined}
            onDeclineAction={isOwnProposal ? () => onDeclineAction?.('declined') : undefined}
          />
        );
      })}
      <div ref={endRef} aria-hidden="true" />
    </div>
  );
}