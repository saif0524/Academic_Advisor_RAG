import { useId } from 'react';
import './Select.css';

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  label?: string;
  value: string;
  onChange: (next: string) => void;
  options: Array<SelectOption | string>;
  /** Shown as a disabled first option when value is ''. */
  placeholder?: string;
  disabled?: boolean;
}

/**
 * Shared primitive: labeled native select (major/concentration FC1,
 * planning preferences FC32, term pickers). Controlled.
 */
export default function Select({ label, value, onChange, options, placeholder, disabled = false }: SelectProps) {
  const id = useId();
  const normalized: SelectOption[] = options.map((option) =>
    typeof option === 'string' ? { value: option, label: option } : option,
  );
  return (
    <div className="select">
      {label ? (
        <label className="select-label" htmlFor={id}>
          {label}
        </label>
      ) : null}
      <select
        id={id}
        className="select-field"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        {placeholder !== undefined ? (
          <option value="" disabled>
            {placeholder}
          </option>
        ) : null}
        {normalized.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}