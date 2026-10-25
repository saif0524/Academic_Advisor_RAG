import Button from '../../shared/Button/Button';
import Icon from '../../shared/Icon/Icon';
import type { Conversation } from '../../../api/types';
import './ConversationListItem.css';

interface ConversationListItemProps {
  item: Conversation;
  active?: boolean;
  onSelect?: (id: string) => void;
  /** Delete this conversation (FC41); the delete button renders only when provided. */
  onDelete?: (id: string) => void;
}

/**
 * One row of the previous-conversations list (FC34 persisted sessions).
 * Active conversation is highlighted; selecting loads the thread (FC27
 * context continuity). Purely presentational.
 */
export default function ConversationListItem({ item, active = false, onSelect, onDelete }: ConversationListItemProps) {
  return (
    <li className="conversation-list-row">
      <Button
        variant={active ? 'secondary' : 'ghost'}
        onClick={() => onSelect?.(item.id)}
        aria-label={`Open conversation: ${item.title}`}
      >
        <span className="conversation-list-item">
          <span className="conversation-list-item-title">{item.title}</span>
          {item.snippet ? <span className="conversation-list-item-snippet">{item.snippet}</span> : null}
          {item.date ? <time className="conversation-list-item-date">{item.date}</time> : null}
        </span>
      </Button>
      {onDelete ? (
        <Button variant="ghost" iconOnly onClick={() => onDelete(item.id)} aria-label={`Delete conversation: ${item.title}`}>
          <Icon name="trash" size={14} />
        </Button>
      ) : null}
    </li>
  );
}