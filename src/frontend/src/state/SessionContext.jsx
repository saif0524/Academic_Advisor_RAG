import { createContext, useContext, useMemo, useState } from 'react';

/**
 * App-wide session state (FC36 — auth is out of scope, so there is no login
 * flow: the agent server supplies the pre-authenticated student and this
 * context just holds it for any subtree that needs `session.studentId` etc.).
 * Provider and hook are exported from the same file per the react-component
 * skill; built-in state only (no Redux/Zustand).
 */
const SessionContext = createContext(null);

/**
 * Current session context: { session, setSession }.
 * @returns {{ session: object | null, setSession: (session: object) => void }}
 */
export function useSession() {
  const context = useContext(SessionContext);
  if (context === null) {
    throw new Error('useSession must be used within <SessionProvider>');
  }
  return context;
}

/** Provides the app-wide session to its subtree. Props: children. */
export function SessionProvider({ children }) {
  const [session, setSession] = useState(null);
  const value = useMemo(() => ({ session, setSession }), [session]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}