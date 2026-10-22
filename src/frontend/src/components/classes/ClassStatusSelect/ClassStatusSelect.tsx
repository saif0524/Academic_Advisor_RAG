import { useState } from 'react';
import type { ClassStatus } from '../../../api/classes';
import './ClassStatusSelect.css';

export const CLASS_STATUS_OPTIONS: Array<{ value: ClassStatus; label: string }> = [
  { value: 'not_taken', label: 'Not taken' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'taken', label: 'Taken' },
  { value: 'passed', label: 'Passed' },
  { value: 'failed', label: 'Failed' },
];

interface ClassStatusSelectProps {
  courseLabel: string;
  /** Current profile status; undefined = not on the profile yet (shows Not taken). */
  status?: ClassStatus;
  /** Persists the change (api seam); rejection reverts and shows the error. */
  onChange: (next: ClassStatus) => Promise<unknown> | void;
}

/**
 * Per-class status control (FC21: not taken / in progress / taken / passed /
 * failed). A direct user action — no FC23 confirmation. The backend owns the
 * enum and the deterministic validator reads it (FC29–FC32).
 */
export default function ClassStatusSelect({ courseLabel, status, onChange }: ClassStatusSelectProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const handle = async (next: ClassStatus) => {
    setSaving(true);
    setError(null);
    try {
      await onChange(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };
  return (
    <span className="class-status-select">
      <select
        className={`class-status-select-field class-status-select-field--${status ?? 'not_taken'}`}
        aria-label={`Status of ${courseLabel}`}
        value={status ?? 'not_taken'}
        disabled={saving}
        onChange={(event) => handle(event.target.value as ClassStatus)}
      >
        {CLASS_STATUS_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error ? (
        <span className="class-status-select-error" role="alert">
          Couldn’t save status
        </span>
      ) : null}
    </span>
  );
}
