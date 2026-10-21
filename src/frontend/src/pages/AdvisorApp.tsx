import { useState } from 'react';
import type { PageId } from '../components/shared/AppSidebar/AppSidebar';
import ChatPanel from '../components/chat/ChatPanel/ChatPanel';
import Dashboard from './Dashboard';
import TimelinePage from './TimelinePage';
import CourseSearch from './CourseSearch';
import AccountPage from './AccountPage';

/**
 * App composition root (no router — single-page state): owns the active-page
 * state and the advisor-chat drawer state so the drawer persists across page
 * switches (wireframes 01–06). Pages receive the shared wiring via props —
 * pages are thin shells; content components do the work.
 * Props: none (main.tsx mounts this under SessionProvider, FC36).
 */
export default function AdvisorApp() {
  const [page, setPage] = useState<PageId>('home');
  const [chatOpen, setChatOpen] = useState(false);
  const toggleChat = () => setChatOpen((open) => !open);
  const navigate = (next: PageId) => {
    setPage(next);
    setChatOpen(false);
  };

  /* The panel instance persists across page swaps (same slot node type and
     position) — conversation state survives navigation (FC27/FC34 demo). */
  const chatSlot = <ChatPanel onClose={() => setChatOpen(false)} />;

  const shellProps = { onNavigate: navigate, chatOpen, onToggleChat: toggleChat, chatSlot };

  return (
    <>
      {page === 'home' && <Dashboard active="home" {...shellProps} />}
      {page === 'timeline' && <TimelinePage active="timeline" {...shellProps} />}
      {page === 'search' && <CourseSearch active="search" {...shellProps} />}
      {page === 'account' && <AccountPage active="account" {...shellProps} />}
    </>
  );
}