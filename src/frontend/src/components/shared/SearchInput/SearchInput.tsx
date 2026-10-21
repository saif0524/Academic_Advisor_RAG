import { useId, useState } from 'react';
import Icon from '../Icon/Icon';
import Badge from '../Badge/Badge';
import type { VerdictVariant } from '../../../api/types';
import './SearchInput.css';

export interface SearchSuggestion {
  id: string;
  primary: string;
  secondary?: string | null;
  badge?: string;
  badgeVariant?: VerdictVariant;
}

interface SearchInputProps {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
  /** Combobox suggestions; [] renders the explicit no-results row. Omit to
      render a plain search field (e.g. conversation search). */
  suggestions?: SearchSuggestion[];
  onSelect?: (id: string) => void;
  /** sr-only field label. */
  label?: string;
  noResultsText?: string;
}

/**
 * Shared primitive: search input with an optional combobox suggestion list
 * (FC8 course search on the timeline "Add a course", FC34 conversation
 * search). List opens on focus when there are suggestions, closes on Escape
 * or pick. Purely presentational — the parent owns the query and results.
 */
export default function SearchInput({
  value,
  onChange,
  placeholder,
  suggestions,
  onSelect,
  label,
  noResultsText = 'No matches.',
}: SearchInputProps) {
  const fieldId = useId();
  const [isOpen, setIsOpen] = useState(false);

  const trimmed = value.trim();
  const listOpen = isOpen && trimmed !== '' && suggestions !== undefined;
  const hasSuggestions = (suggestions?.length ?? 0) > 0;

  return (
    <div className="search-input">
      <div className="search-input-box">
        <Icon name="search" size={16} />
        <input
          id={fieldId}
          className="search-input-field"
          type="text"
          value={value}
          placeholder={placeholder}
          aria-label={label}
          onChange={(event) => onChange(event.target.value)}
          onFocus={() => setIsOpen(true)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') setIsOpen(false);
          }}
        />
      </div>
      {listOpen && (
        <ul className="search-input-list" role="listbox" aria-label={label ?? 'Suggestions'}>
          {hasSuggestions
            ? (suggestions ?? []).map((suggestion) => (
                <li key={suggestion.id} role="option" aria-selected="false">
                  <button
                    type="button"
                    className="search-input-option"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => {
                      onSelect?.(suggestion.id);
                      setIsOpen(false);
                    }}
                  >
                    <span className="search-input-option-id">{suggestion.id}</span>
                    <span className="search-input-option-text">
                      {suggestion.primary}
                      {suggestion.secondary ? (
                        <span className="search-input-option-secondary">{suggestion.secondary}</span>
                      ) : null}
                    </span>
                    {suggestion.badge ? (
                      <Badge variant={suggestion.badgeVariant ?? 'success'}>{suggestion.badge}</Badge>
                    ) : null}
                  </button>
                </li>
              ))
            : (
                <li className="search-input-empty" role="option" aria-selected="false">
                  {noResultsText}
                </li>
              )}
        </ul>
      )}
    </div>
  );
}