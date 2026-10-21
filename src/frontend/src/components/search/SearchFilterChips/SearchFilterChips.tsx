import Badge from '../../shared/Badge/Badge';
import './SearchFilterChips.css';

export interface SearchFilter {
  id: string;
  label: string;
  count?: number;
}

interface SearchFilterChipsProps {
  filters?: SearchFilter[];
  /** Active filter ids (on = pressed). */
  activeIds?: string[];
  onToggle?: (id: string, nextActive: boolean) => void;
}

/**
 * Toggleable filter chips (wireframe 04; FC10 filters — semester offered,
 * applies to degree, schedule compatibility). Pressed state is visual +
 * accessible; the parent owns the active set and re-queries.
 */
export default function SearchFilterChips({ filters, activeIds = [], onToggle }: SearchFilterChipsProps) {
  if (!filters?.length) return null;
  return (
    <div className="search-filter-chips" role="group" aria-label="Search filters">
      {filters.map((filter) => {
        const active = activeIds.includes(filter.id);
        return (
          <button
            key={filter.id}
            type="button"
            className={`search-filter-chip${active ? ' search-filter-chip--active' : ''}`}
            aria-pressed={active}
            onClick={() => onToggle?.(filter.id, !active)}
          >
            <Badge variant={active ? 'primary' : 'neutral'}>{filter.label}</Badge>
            {typeof filter.count === 'number' ? (
              <span className="search-filter-chip-count">{filter.count}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}