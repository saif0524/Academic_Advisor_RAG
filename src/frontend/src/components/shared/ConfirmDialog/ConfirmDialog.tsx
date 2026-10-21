import { useEffect, useRef } from 'react';
import Button from '../Button/Button';
import './ConfirmDialog.css';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  body?: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Styles the confirm action as destructive. */
  danger?: boolean;
  busy?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
}

/**
 * Shared primitive: modal confirmation dialog (FC35 structured dialog
 * inputs, FC23 confirm-before-acting surface — plan changes, major changes,
 * and other student-record actions confirm here; the deterministic side only
 * acts after the confirm path).
 */
export default function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return undefined;
    // Focus the confirm action when the dialog opens; Escape cancels.
    dialogRef.current
      ?.querySelector<HTMLButtonElement>(
        '.confirm-dialog-actions .button--danger, .confirm-dialog-actions .button--primary',
      )
      ?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancel?.();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="confirm-dialog-overlay" onMouseDown={onCancel}>
      <div
        ref={dialogRef}
        className="confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 className="confirm-dialog-title">{title}</h2>
        <div className="confirm-dialog-body">{body}</div>
        <div className="confirm-dialog-actions">
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} disabled={busy}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}