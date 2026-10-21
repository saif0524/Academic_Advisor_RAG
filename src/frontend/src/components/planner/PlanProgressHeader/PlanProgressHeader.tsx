import Badge from '../../shared/Badge/Badge';
import Icon from '../../shared/Icon/Icon';
import ProgressBar from '../../shared/ProgressBar/ProgressBar';
import Select from '../../shared/Select/Select';
import type { ActivePlanData } from '../../../api/types';
import './PlanProgressHeader.css';

interface PlanProgressHeaderProps {
  plan: ActivePlanData | null;
  termOptions?: string[];
  onTermChange?: (term: string) => void;
  loading?: boolean;
  error?: string | null;
}

/**
 * Home header block (wireframe 01): the active degree plan summary —
 * major + concentration + catalog year (FC1/FC7), overall credit progress
 * toward the one selected degree (FC19), the on-track note (engine verdict
 * display), and the current-term picker. All data comes from the api layer;
 * nothing is computed here.
 */
export default function PlanProgressHeader({
  plan,
  termOptions,
  onTermChange,
  loading = false,
  error = null,
}: PlanProgressHeaderProps) {
  if (loading) {
    return (
      <section className="plan-progress-header" aria-busy="true">
        <p className="plan-progress-header-state">Loading your active degree plan…</p>
      </section>
    );
  }
  if (error) {
    return (
      <section className="plan-progress-header">
        <p className="plan-progress-header-state plan-progress-header-state--error">
          Could not load your degree plan: {error}
        </p>
      </section>
    );
  }
  if (!plan || !plan.program) {
    return (
      <section className="plan-progress-header">
        <p className="plan-progress-header-state">No active degree plan on record.</p>
      </section>
    );
  }
  const { program, progress, onTrackNote, currentTerm } = plan;
  return (
    <section className="plan-progress-header" aria-label="Active degree plan">
      <p className="plan-progress-header-kicker">Active degree plan</p>
      <h1 className="plan-progress-header-title">{program.majorName}</h1>
      <p className="plan-progress-header-meta">
        {program.concentration} concentration
        {program.catalogYear && program.catalogYear !== '—' ? ` · Catalog ${program.catalogYear}` : ''}
      </p>
      <p className="plan-progress-header-credits">
        {progress.completed} of {progress.total} credit hours
      </p>
      <ProgressBar
        segments={[
          { key: 'completed', label: 'Completed', value: progress.completed, variant: 'completed' },
          { key: 'inprogress', label: 'In progress', value: progress.inProgress, variant: 'in-progress' },
          { key: 'planned', label: 'Planned', value: progress.planned, variant: 'planned' },
        ]}
        showLegend
        label="Degree progress by status"
      />
      <p className="plan-progress-header-ontrack">
        <Icon name="checkCircle" size={16} /> {onTrackNote}
      </p>
      {termOptions && termOptions.length > 0 && (
        <div className="plan-progress-header-term">
          <Select
            label="Current term"
            value={currentTerm ?? ''}
            options={termOptions}
            onChange={onTermChange ?? (() => {})}
          />
        </div>
      )}
      {program.catalogYear && program.catalogYear !== '—' ? (
        <Badge variant="neutral">{program.catalogYear} catalog</Badge>
      ) : null}
    </section>
  );
}