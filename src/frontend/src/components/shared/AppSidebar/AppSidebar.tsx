import Icon from '../Icon/Icon';
import './AppSidebar.css';

export type PageId = 'home' | 'timeline' | 'search' | 'account';

/** Wireframe nav (01–06): advisor wordmark + four destinations + account. */
const NAV_ITEMS: Array<{ id: PageId; label: string; icon: Parameters<typeof Icon>[0]['name'] }> = [
  { id: 'home', label: 'Degree plan', icon: 'bookOpen' },
  { id: 'timeline', label: 'Timeline', icon: 'clock' },
  { id: 'search', label: 'Search', icon: 'search' },
  { id: 'account', label: 'Account', icon: 'user' },
];

interface AppSidebarProps {
  active: PageId;
  onNavigate?: (page: PageId) => void;
  /** Initials circle in the account block (FC36 pre-auth profile). */
  studentName?: string;
}

/**
 * Shared primitive: left navigation rail for every page (FC35 UI surface).
 * Active item highlighted; navigation is a controlled callback — no router
 * (single-page state).
 */
export default function AppSidebar({ active, onNavigate, studentName }: AppSidebarProps) {
  const initials =
    (studentName ?? 'A')
      .split(/\s+/)
      .map((part) => part[0] ?? '')
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase() || 'A';
  return (
    <nav className="app-sidebar" aria-label="Primary">
      <div className="app-sidebar-brand">
        <span className="app-sidebar-brand-icon" aria-hidden="true">
          <Icon name="cap" size={20} />
        </span>
        <span className="app-sidebar-brand-name">advisor</span>
      </div>
      <ul className="app-sidebar-list">
        {NAV_ITEMS.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className={`app-sidebar-item${active === item.id ? ' app-sidebar-item--active' : ''}`}
              aria-current={active === item.id ? 'page' : undefined}
              onClick={() => onNavigate?.(item.id)}
            >
              <Icon name={item.icon} size={18} />
              <span>{item.label}</span>
            </button>
          </li>
        ))}
      </ul>
      <div className="app-sidebar-account">
        <button
          type="button"
          className={`app-sidebar-item${active === 'account' ? ' app-sidebar-item--active' : ''}`}
          onClick={() => onNavigate?.('account')}
        >
          <span className="app-sidebar-avatar" aria-hidden="true">
            {initials}
          </span>
          <span>Account</span>
        </button>
      </div>
    </nav>
  );
}