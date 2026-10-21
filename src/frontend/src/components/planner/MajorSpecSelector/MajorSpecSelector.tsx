import Button from '../../shared/Button/Button';
import Checkbox from '../../shared/Checkbox/Checkbox';
import Select from '../../shared/Select/Select';
import type { PlanOption } from '../../../api/types';
import './MajorSpecSelector.css';

interface MajorSpecSelectorProps {
  /** null/empty renders an explicit "no majors available" state (grounded UI). */
  options?: { majors: PlanOption[] } | null;
  major?: string;
  concentration?: string;
  includeSummer?: boolean;
  /** Selections are controlled; the parent owns state + generate action. */
  onSelectionChange?: (partial: { major?: string; concentration?: string; includeSummer?: boolean }) => void;
  onGenerate?: () => void;
  /** Enable the generate button (major + concentration set). */
  canGenerate?: boolean;
  disabled?: boolean;
}

/**
 * Plan-generation form (FC1, FC2): one major and one concentration — a
 * student can only have one of each (FC1) — plus the optional
 * summer-sessions toggle (FC25).
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
}: MajorSpecSelectorProps) {
  const majors = options?.majors ?? [];
  const selectedMajor = majors.find((option) => option.name === major);
  const hasOptions = majors.length > 0;
  return (
    <section className="major-spec-selector" aria-label="Degree plan options">
      <div className="major-spec-selector-fields">
        <div className="major-spec-selector-field">
          <Select
            label="Major"
            value={major}
            options={majors.map((option) => option.name)}
            placeholder={hasOptions ? 'Select your major' : undefined}
            disabled={disabled || !hasOptions}
            onChange={(next) => onSelectionChange?.({ major: next, concentration: '' })}
          />
        </div>
        <div className="major-spec-selector-field">
          <Select
            label="Concentration"
            value={concentration}
            options={selectedMajor?.concentrations ?? []}
            placeholder={selectedMajor ? 'Select your specialization' : undefined}
            disabled={disabled || !selectedMajor}
            onChange={(next) => onSelectionChange?.({ concentration: next })}
          />
        </div>
        <div className="major-spec-selector-field">
          <Checkbox
            label="Include summer sessions"
            checked={includeSummer}
            disabled={disabled}
            onChange={(checked) => onSelectionChange?.({ includeSummer: checked })}
          />
        </div>
      </div>
      {!hasOptions && (
        <p className="major-spec-selector-empty">No majors available right now (grounded data only).</p>
      )}
      <div className="major-spec-selector-actions">
        <Button onClick={onGenerate} disabled={disabled || !canGenerate}>
          Generate plan
        </Button>
      </div>
    </section>
  );
}