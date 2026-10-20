import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { SessionProvider } from './state/SessionContext.jsx';
import Dashboard from './pages/Dashboard.jsx';

/* AdvisorUI entry (domain model §5, FC36): the agent server injects a
   pre-authenticated student, so there is no auth UI — pages mount directly
   under the app-wide session provider. Page components under src/pages/ are
   the composition roots; no top-level App shell until features need one. */
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SessionProvider>
      <Dashboard />
    </SessionProvider>
  </StrictMode>,
);