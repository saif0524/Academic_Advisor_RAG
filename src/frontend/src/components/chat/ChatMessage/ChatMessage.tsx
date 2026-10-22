import ActionConfirmationCard from '../ActionConfirmationCard/ActionConfirmationCard';
import type { ProposalStatus } from '../ActionConfirmationCard/ActionConfirmationCard';
import type { ChatMessage } from '../../../api/types';
import Markdown from '../../shared/Markdown/Markdown';
import './ChatMessage.css';

interface ChatMessageProps {
  message: ChatMessage;
  /** Decision state for the message carrying `action`. */
  actionStatus?: ProposalStatus;
  onConfirmAction?: () => void;
  onDeclineAction?: () => void;
  actionBusy?: boolean;
}

/**
 * One chat bubble (FC22 wireframe conversation; FC35 prompt-based queries).
 * Advisor messages align left with an "Advisor" tag and render as markdown;
 * user messages align right as plain text.
 * When an advisor message carries a proposed action, the bubble renders the
 * FC23 ActionConfirmationCard — the decision state is owned by the ChatPanel
 * and passed down.
 */
export default function ChatMessage({
  message,
  actionStatus,
  onConfirmAction,
  onDeclineAction,
  actionBusy = false,
}: ChatMessageProps) {
  const isUser = message.role === 'user';
  return (
    <article className={`chat-message chat-message--${message.role}`}>
      {!isUser ? <span className="chat-message-author">Advisor</span> : null}
      <div className="chat-message-bubble">
        {isUser ? (
          <p className="chat-message-text">{message.text}</p>
        ) : (
          <Markdown className="chat-message-text chat-message-text--markdown" text={message.text} />
        )}
        {message.action ? (
          <ActionConfirmationCard
            action={message.action}
            status={actionStatus ?? 'pending'}
            onConfirm={onConfirmAction}
            onDecline={onDeclineAction}
            busy={actionBusy}
          />
        ) : null}
      </div>
    </article>
  );
}