import type { ReactNode } from 'react';
import AppSidebar from '../AppSidebar/AppSidebar';
import type { PageId } from '../AppSidebar/AppSidebar';
import Icon from '../Icon/Icon';
import './AppShell.css';

interface AppShellProps {
  active: PageId;
  onNavigate?: (page: PageId) => void;
  chatOpen?: boolean;
  onToggleChat?: () => void;
  /** Drawer content (e.g. a ChatPanel from chat/) — shared/ must not import
      domain components, so pages compose the node and pass it in. */
  chatSlot?: ReactNode;
  children?: ReactNode;
  studentName?: string;
}

/**
 * Shared layout: sidebar + content region + right-side advisor-chat drawer
 * (wireframes 01–06; FC22/FC35). The drawer renders `chatSlot` only while
 * open. The floating "Advisor" pill toggles the drawer. Navigation and
 * drawer state are controlled from the app root so the drawer persists
 * across page switches.
 */
export default function AppShell({
  active,
  onNavigate,
  chatOpen = false,
  onToggleChat,
  chatSlot = null,
  children,
  studentName,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <AppSidebar active={active} onNavigate={onNavigate} studentName={studentName} />
      <main className="app-shell-content">{children}</main>
      <aside
        className={`app-shell-drawer${chatOpen ? ' app-shell-drawer--open' : ''}`}
        aria-label="Advisor chat"
        aria-hidden={!chatOpen}
      >
        <div className="app-shell-drawer-inner">{chatOpen ? chatSlot : null}</div>
      </aside>
      <button
        type="button"
        className={`app-shell-advisor-pill${chatOpen ? ' app-shell-advisor-pill--open' : ''}`}
        onClick={onToggleChat}
        aria-expanded={chatOpen}
      >
        <Icon name={chatOpen ? 'close' : 'chat'} size={16} />
        Advisor
      </button>
    </div>
  );
}