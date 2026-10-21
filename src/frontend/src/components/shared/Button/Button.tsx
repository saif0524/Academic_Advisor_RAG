import './Button.css';
import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  /** Label content — may include an Icon. */
  children: ReactNode;
  variant?: ButtonVariant;
  /** Square padding for icon-only round buttons (e.g. row remove, close). */
  iconOnly?: boolean;
}

/**
 * Shared primitive: button used by forms and confirmation surfaces
 * (planner FC2/FC3, FC20–FC23 dialogs, chat composer). Extend the variants
 * rather than restyling per component. Native button attributes
 * (aria-label, disabled, type, …) pass through for a11y and tests.
 */
export default function Button({
  children,
  variant = 'primary',
  disabled = false,
  iconOnly = false,
  ...rest
}: ButtonProps) {
  const classes = ['button', `button--${variant}`, iconOnly ? 'button--icon-only' : '']
    .filter(Boolean)
    .join(' ');
  return (
    <button className={classes} disabled={disabled} {...rest}>
      {children}
    </button>
  );
}