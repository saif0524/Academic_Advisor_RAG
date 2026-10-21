import { useId } from 'react';
import './TextInput.css';

interface TextInputProps {
  label?: string;
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
  disabled?: boolean;
  type?: 'text' | 'number';
  /** Supporting text below the field (e.g. FC35 dialog hint). */
  hint?: string;
  error?: string;
}

/**
 * Shared primitive: labeled single-line text input (FC35 structured dialog
 * inputs). Controlled; the parent owns the value.
 */
export default function TextInput({
  label,
  value,
  onChange,
  placeholder,
  disabled = false,
  type = 'text',
  hint,
  error,
}: TextInputProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  return (
    <div className="text-input">
      {label ? (
        <label className="text-input-label" htmlFor={id}>
          {label}
        </label>
      ) : null}
      <input
        id={id}
        className={`text-input-field${error ? ' text-input-field--error' : ''}`}
        type={type}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={hint || error ? hintId : undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      {hint || error ? (
        <p id={hintId} className={`text-input-note${error ? ' text-input-note--error' : ''}`}>
          {error || hint}
        </p>
      ) : null}
    </div>
  );
}