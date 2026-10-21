import { useId } from 'react';
import './TextArea.css';

interface TextAreaProps {
  label?: string;
  /** sr-only label when no visible label (e.g. the composer field). */
  ariaLabel?: string;
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
  rows?: number;
  disabled?: boolean;
  /** Native key handler (composer: Enter sends, Shift+Enter newline). */
  onKeyDown?: React.KeyboardEventHandler<HTMLTextAreaElement>;
}

/**
 * Shared primitive: labeled multiline text input (FC35 prompt-based queries —
 * the chat composer field). Controlled.
 */
export default function TextArea({
  label,
  ariaLabel,
  value,
  onChange,
  placeholder,
  rows = 3,
  disabled = false,
  onKeyDown,
}: TextAreaProps) {
  const id = useId();
  return (
    <div className="text-area">
      {label ? (
        <label className="text-area-label" htmlFor={id}>
          {label}
        </label>
      ) : null}
      <textarea
        id={id}
        className="text-area-field"
        rows={rows}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        aria-label={ariaLabel}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
      />
    </div>
  );
}