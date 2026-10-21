import type { ReactNode } from 'react';
import './Badge.css';

export type BadgeVariant = 'neutral' | 'primary' | 'info' | 'success' | 'warning' | 'danger';

const VARIANTS: BadgeVariant[] = ['neutral', 'primary', 'info', 'success', 'warning', 'danger'];

interface BadgeProps {
  /** Status/verdict chip content — text or text-with-counts. */
  children: ReactNode;
  variant?: BadgeVariant;
  /** Colored status dot before the text. */
  dot?: boolean;
}

/**
 * Shared primitive: status/verdict chip. Soft background + strong text.
 */
export default function Badge({ children, variant = 'neutral', dot = false }: BadgeProps) {
  const safeVariant: BadgeVariant = VARIANTS.includes(variant) ? variant : 'neutral';
  return (
    <span className={`badge badge--${safeVariant}`}>
      {dot && <span className="badge-dot" aria-hidden="true" />}
      {children}
    </span>
  );
}