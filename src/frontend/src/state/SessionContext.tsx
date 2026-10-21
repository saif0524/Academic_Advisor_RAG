import { createContext, useContext, useMemo, useState } from 'react';

/** Pre-authenticated session data the agent server injects (FC36 — no auth
    flow in scope; this context just holds it for subtrees that need it). */
export interface Session {
  studentId: string;
}

/**
 * App-wide session state (FC36): provider and hook are exported from the
 * same file per the react-component skill; built-in state only.
 */
const SessionContext = createContext<{ session: Session | null; setSession: (session: Session) => void } | null>(null);

/** Current session context: { session, setSession }. */
export function useSession(): { session: Session | null; setSession: (session: Session) => void } {
  const context = useContext(SessionContext);
  if (context === null) {
    throw new Error('useSession must be used within <SessionProvider>');
  }
  return context;
}

/** Provides the app-wide session to its subtree. Props: children. */
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const value = useMemo(() => ({ session, setSession }), [session]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}