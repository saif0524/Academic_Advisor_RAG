import Button from '../../shared/Button/Button.jsx';
import './MajorSpecSelector.css';

/**
 * Plan-generation form (FC1, FC2): one major and one concentration — a
 * student can only have one of each (FC1) — plus the optional
 * summer-sessions toggle (FC25). Selections are controlled; the parent owns
 * the selection state and the generate action.
 *
 * Props:
 * - options: { majors: Array<{ name: string, concentrations: string[] }> } | null
 *   — null/empty renders an explicit "no majors available" state (grounded UI).
 * - major, concentration, includeSummer: current selections (controlled).
 * - onSelectionChange: (partial: { major?, concentration?, includeSummer? }) => void
 * - onGenerate: () => void — fires when Generate plan is clicked.
 * - canGenerate: boolean — enable the generate button (major + concentration set).
 * - disabled: boolean — disable all controls (busy/generating).
 */
export default function MajorSpecSelector({
  options = null,
  major = '',
  concentration = '',
  includeSummer = false,
  onSelectionChange,
  onGenerate,
  canGenerate = false,
  disabled = false,
}) {
  const majors = options?.majors ?? [];
  const selectedMajor = majors.find((option) => option.name === major);
  const hasOptions = majors.length > 0;
  return (
    <section className="major-spec-selector" aria-label="Degree plan options">
      <div className="major-spec-selector-fields">
        <div className="major-spec-selector-field">
          <label className="major-spec-selector-label" htmlFor="major-spec-selector-major">
            Major
          </label>
          <select
            id="major-spec-selector-major"
            className="major-spec-selector-select"
            value={major}
            disabled={disabled || !hasOptions}
            onChange={(event) => onSelectionChange({ major: event.target.value })}
          >
            <option value="">Select a major…</option>
            {hasOptions &&
              majors.map((option) => (
                <option key={option.name} value={option.name}>
                  {option.name}
                </option>
              ))}
          </select>
        </div>
        <div className="major-spec-selector-field">
          <label className="major-spec-selector-label" htmlFor="major-spec-selector-concentration">
            Specialization (concentration)
          </label>
          <select
            id="major-spec-selector-concentration"
            className="major-spec-selector-select"
            value={concentration}
            disabled={disabled || !selectedMajor}
            onChange={(event) => onSelectionChange({ concentration: event.target.value })}
          >
            <option value="">Select a specialization…</option>
            {selectedMajor?.concentrations.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div className="major-spec-selector-field">
          <label className="major-spec-selector-check" htmlFor="major-spec-selector-summer">
            <input
              id="major-spec-selector-summer"
              type="checkbox"
              checked={includeSummer}
              disabled={disabled}
              onChange={(event) => onSelectionChange({ includeSummer: event.target.checked })}
            />
            Include summer sessions (optional)
          </label>
        </div>
      </div>
      <div className="major-spec-selector-actions">
        <Button onClick={onGenerate} disabled={disabled || !canGenerate}>
          Generate plan
        </Button>
        {!disabled && !canGenerate && (
          <p className="major-spec-selector-hint" role="status">
            {hasOptions
              ? 'Choose a major and specialization to generate a plan.'
              : 'No majors are available yet.'}
          </p>
        )}
      </div>
    </section>
  );
}