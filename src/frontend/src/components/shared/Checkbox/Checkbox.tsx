import { useId } from 'react';
import './Checkbox.css';

interface CheckboxProps {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}

/**
 * Shared primitive: labeled checkbox toggle (e.g. include summer sessions —
 * FC25 planning preference). Controlled.
 */
export default function Checkbox({ label, checked, onChange, disabled = false }: CheckboxProps) {
  const id = useId();
  return (
    <div className="checkbox">
      <input
        id={id}
        className="checkbox-input"
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <label className="checkbox-label" htmlFor={id}>
        {label}
      </label>
    </div>
  );
}