import { useState } from 'react';
import Button from '../../shared/Button/Button';
import Checkbox from '../../shared/Checkbox/Checkbox';
import Select from '../../shared/Select/Select';
import { toTitleCase } from '../../shared/textCase';
import type { PlanningPreferences as PlanningPreferencesData } from '../../../api/types';
import './PlanningPreferences.css';

/* Cap choices mirror the fixture demo range (mock of the degree's FC32 limit). */
const CREDIT_OPTIONS = [12, 13, 14, 15, 16, 17, 18];
const CLASS_TIME_OPTIONS = ['Any time', 'Mornings', 'Afternoons', 'Evenings'];

interface PlanningPreferencesProps {
  preferences: PlanningPreferencesData | null;
  /** Parent-owned async save (mock of PUT /students/me/preferences). */
  onSave?: (draft: PlanningPreferencesData) => Promise<void>;
  saving?: boolean;
  saveError?: string | null;
}

interface SeededState {
  seed: PlanningPreferencesData | null;
  draft: PlanningPreferencesData | null;
  saved: boolean;
}

/**
 * Planning preferences form (wireframe 05): the inputs the deterministic
 * plan engine consumes — max credit hours per semester (FC32 cap), optional
 * summer sessions (FC25), preferred class times. Local draft state re-seeded
 * when the loaded preferences change (React's adjust-state-on-props-change
 * pattern, no effect cascade), with an explicit save action.
 */
export default function PlanningPreferences({
  preferences,
  onSave,
  saving = false,
  saveError = null,
}: PlanningPreferencesProps) {
  const [seededState, setSeededState] = useState<SeededState>({
    seed: preferences,
    draft: preferences ? { ...preferences } : null,
    saved: false,
  });
  if (seededState.seed !== preferences) {
    setSeededState({
      seed: preferences,
      draft: preferences ? { ...preferences } : null,
      saved: false,
    });
  }
  const draft = seededState.draft;
  const saved = seededState.saved;

  const update = (patch: Partial<PlanningPreferencesData>) =>
    setSeededState((current) => ({ ...current, draft: current.draft ? { ...current.draft, ...patch } : null, saved: false }));

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draft) return;
    await onSave?.(draft);
    setSeededState((current) => ({ ...current, saved: true }));
  };

  if (!draft) {
    if (saving) return <p className="planning-preferences-state">Loading preferences…</p>;
    return (
      <p className="planning-preferences-state">
        {saveError ? `Could not load preferences: ${saveError}` : 'No planning preferences yet.'}
      </p>
    );
  }

  return (
    <form className="planning-preferences" onSubmit={handleSubmit} aria-label="Planning preferences">
      <h3 className="planning-preferences-title">Planning preferences</h3>
      <Select
        label="Max credit hours per semester"
        value={String(draft.maxCreditsPerSemester ?? '')}
        options={CREDIT_OPTIONS.map((limit) => ({ value: String(limit), label: `${limit} hours` }))}
        onChange={(value) => update({ maxCreditsPerSemester: Number(value) })}
      />
      <Checkbox
        label="Include summer sessions"
        checked={Boolean(draft.includeSummer)}
        onChange={(checked) => update({ includeSummer: checked })}
      />
      <Select
        label="Preferred class times"
        value={draft.preferredClassTimes ?? ''}
        options={CLASS_TIME_OPTIONS.map(toTitleCase)}
        onChange={(value) => update({ preferredClassTimes: value })}
      />
      <div className="planning-preferences-footer">
        <Button type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save preferences'}
        </Button>
        {saved && !saveError ? <span className="planning-preferences-saved">Saved</span> : null}
        {saveError ? <span className="planning-preferences-error">{saveError}</span> : null}
      </div>
    </form>
  );
}