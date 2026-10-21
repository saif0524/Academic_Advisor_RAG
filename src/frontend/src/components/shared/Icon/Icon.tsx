import type { ReactNode } from 'react';
import './Icon.css';

/* Inline SVG glyph set (stroke-based, currentColor). Shared primitive used
   across planner/search/chat/shared surfaces — no course or degree semantics
   here, just glyphs. */

export type IconName =
  | 'search' | 'plus' | 'close' | 'check' | 'checkCircle' | 'warning' | 'info'
  | 'edit' | 'chevronDown' | 'chevronRight' | 'calendar' | 'clock' | 'send'
  | 'user' | 'cap' | 'chat' | 'bookOpen' | 'list';

const GLYPHS: Record<IconName, ReactNode> = {
  search: (<><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></>),
  plus: <path d="M12 5v14M5 12h14" />,
  close: <path d="M18 6 6 18M6 6l12 12" />,
  check: <path d="m4 12 5 5L20 6" />,
  checkCircle: (<><circle cx="12" cy="12" r="9" /><path d="m8 12 3 3 5-5" /></>),
  warning: (<><path d="M12 3 2.5 20h19L12 3Z" /><path d="M12 9v5" /><path d="M12 17.5h.01" /></>),
  info: (<><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 7.5h.01" /></>),
  edit: (<><path d="M4 20h4L19.5 8.5a2.12 2.12 0 0 0-3-3L5 17v3Z" /><path d="m13.5 6.5 3 3" /></>),
  chevronDown: <path d="m6 9 6 6 6-6" />,
  chevronRight: <path d="m9 6 6 6-6 6" />,
  calendar: (<><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M8 3v4M16 3v4M3 10h18" /></>),
  clock: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
  send: <path d="m3 11 18-8-6 18-3-7-9-3Z" />,
  user: (<><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></>),
  cap: (<><path d="m12 3 10 5-10 5L2 8l10-5Z" /><path d="M6 10v5c0 1.7 2.7 3 6 3s6-1.3 6-3v-5" /></>),
  chat: <path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5H3l2.2-2.6A8.5 8.5 0 1 1 21 11.5Z" />,
  bookOpen: (<><path d="M2 4h6a4 4 0 0 1 4 4v12a3 3 0 0 0-3-3H2z" /><path d="M22 4h-6a4 4 0 0 0-4 4v12a3 3 0 0 1 3-3h7z" /></>),
  list: <path d="M3 6h18M3 12h18M3 18h12" />,
};

interface IconProps {
  name: IconName;
  size?: number;
  /** Optional accessible label; the icon is aria-hidden unless given. */
  label?: string;
}

/** Shared primitive: inline-SVG icon (FC35 chrome). */
export default function Icon({ name, size = 16, label }: IconProps) {
  const glyph = GLYPHS[name];
  if (!glyph) return null;
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      {glyph}
    </svg>
  );
}