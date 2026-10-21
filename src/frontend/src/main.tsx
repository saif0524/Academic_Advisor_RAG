import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { SessionProvider } from './state/SessionContext';
import AdvisorApp from './pages/AdvisorApp';

/* AdvisorUI entry (domain model §5, FC36): the agent server injects a
   pre-authenticated student, so there is no auth UI — the app composition
   root mounts directly under the app-wide session provider. AdvisorApp owns
   the page state (no router — single-page state) and the advisor-chat drawer
   state so the drawer persists across page switches. */
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SessionProvider>
      <AdvisorApp />
    </SessionProvider>
  </StrictMode>,
);