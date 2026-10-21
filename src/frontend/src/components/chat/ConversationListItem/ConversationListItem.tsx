import Button from '../../shared/Button/Button';
import type { Conversation } from '../../../api/types';
import './ConversationListItem.css';

interface ConversationListItemProps {
  item: Conversation;
  active?: boolean;
  onSelect?: (id: string) => void;
}

/**
 * One row of the previous-conversations list (FC34 persisted sessions).
 * Active conversation is highlighted; selecting loads the thread (FC27
 * context continuity). Purely presentational.
 */
export default function ConversationListItem({ item, active = false, onSelect }: ConversationListItemProps) {
  return (
    <li>
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
    </li>
  );
}