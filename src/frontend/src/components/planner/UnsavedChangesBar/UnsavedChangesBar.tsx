import Button from '../../shared/Button/Button';
import './UnsavedChangesBar.css';

interface UnsavedChangesBarProps {
  onDiscard?: () => void;
  onSave?: () => void;
  busy?: boolean;
  changesCount?: number | null;
}

/**
 * Sticky draft bar (wireframe 03; FC3 edit surface): "Unsaved changes" with
 * Discard/Save. Save and Discard are draft operations on the plan — the page
 * owns confirm/dirty logic; this bar is purely presentational.
 */
export default function UnsavedChangesBar({ onDiscard, onSave, busy = false, changesCount }: UnsavedChangesBarProps) {
  return (
    <div className="unsaved-changes-bar" role="status">
      <span className="unsaved-changes-bar-label">
        Unsaved changes{typeof changesCount === 'number' ? ` · ${changesCount}` : ''}
      </span>
      <div className="unsaved-changes-bar-actions">
        <Button variant="secondary" onClick={onDiscard} disabled={busy}>
          Discard
        </Button>
        <Button variant="primary" onClick={onSave} disabled={busy}>
          Save plan
        </Button>
      </div>
    </div>
  );
}