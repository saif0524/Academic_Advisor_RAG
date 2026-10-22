import { useMemo, useState } from 'react';
import Button from '../../shared/Button/Button';
import Icon from '../../shared/Icon/Icon';
import SearchInput from '../../shared/SearchInput/SearchInput';
import ConversationListItem from '../ConversationListItem/ConversationListItem';
import type { Conversation } from '../../../api/types';
import './ConversationHistory.css';

/** Conversation date (ISO) → human group label, newest-first semantics. */
function groupLabel(dateIso: string): string {
  const date = new Date(dateIso);
  if (Number.isNaN(date.getTime())) return 'Earlier';
  const today = new Date();
  const dayMs = 24 * 60 * 60 * 1000;
  const dayDiff = Math.floor((today.setHours(0, 0, 0, 0) - date.setHours(0, 0, 0, 0)) / dayMs);
  if (dayDiff <= 0) return 'Today';
  if (dayDiff === 1) return 'Yesterday';
  if (dayDiff < 7) return 'This week';
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

interface ConversationHistoryProps {
  conversations: Conversation[] | null;
  activeId: string | null;
  onSelect?: (id: string) => void;
  loading?: boolean;
  error?: string | null;
  /** Return to the active conversation. */
  onBack?: () => void;
}

/**
 * Previous conversations panel (wireframe 06; FC34 persisted sessions):
 * search field + grouping by date. Selecting a conversation loads its thread
 * (FC27 continuity). Filtering is client-side over the loaded list.
 */
export default function ConversationHistory({
  conversations,
  activeId,
  onSelect,
  loading = false,
  error = null,
  onBack,
}: ConversationHistoryProps) {
  const [query, setQuery] = useState('');

  const groups = useMemo(() => {
    // Derived value: filtered conversations grouped by date label. Empty
    // list stays empty — nothing invented.
    const trimmed = query.trim().toLowerCase();
    const filtered = (conversations ?? []).filter(
      (item) =>
        trimmed === '' ||
        item.title.toLowerCase().includes(trimmed) ||
        (item.snippet ?? '').toLowerCase().includes(trimmed),
    );
    if (filtered.length === 0) return [] as Array<[string, Conversation[]]>;
    const grouped = new Map<string, Conversation[]>();
    for (const item of filtered) {
      const label = groupLabel(item.date);
      if (!grouped.has(label)) grouped.set(label, []);
      grouped.get(label)?.push(item);
    }
    return [...grouped.entries()];
  }, [conversations, query]);

  return (
    <div className="conversation-history">
      <div className="conversation-history-topbar">
        <Button variant="ghost" iconOnly onClick={onBack} aria-label="Back to the conversation">
          <Icon name="chevronRight" size={14} />
        </Button>
        <h3 className="conversation-history-title">Previous conversations</h3>
      </div>
      <SearchInput
        value={query}
        onChange={setQuery}
        placeholder="Search conversations"
        label="Search previous conversations"
      />
      {loading ? <p className="conversation-history-state">Loading conversations…</p> : null}
      {error ? (
        <p className="conversation-history-state conversation-history-state--error">
          Could not load conversations: {error}
        </p>
      ) : null}
      {!loading && !error && conversations !== null && groups.length === 0 ? (
        <p className="conversation-history-state">No conversations match your search.</p>
      ) : null}
      {groups.map(([label, items]) => (
        <section key={label} className="conversation-history-group" aria-label={label}>
          <h4 className="conversation-history-group-label">{label}</h4>
          <ul className="conversation-history-list">
            {items.map((item) => (
              <ConversationListItem key={item.id} item={item} active={item.id === activeId} onSelect={onSelect} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}