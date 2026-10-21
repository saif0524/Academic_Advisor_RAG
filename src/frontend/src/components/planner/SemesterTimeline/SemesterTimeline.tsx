import Badge from '../../shared/Badge/Badge';
import type { SemesterStatus, SemesterSummary } from '../../../api/types';
import './SemesterTimeline.css';

const STATUS_VARIANTS: Record<SemesterStatus, 'success' | 'info' | 'primary' | 'neutral'> = {
  completed: 'success',
  'in-progress': 'info',
  planned: 'primary',
  optional: 'neutral',
};

const STATUS_LABELS: Record<SemesterStatus, string> = {
  completed: 'Completed',
  'in-progress': 'In progress',
  planned: 'Planned',
  optional: 'Optional',
};

interface SemesterTimelineProps {
  semesters: SemesterSummary[] | null;
  selectedId: string | null;
  onSelect?: (id: string) => void;
  loading?: boolean;
  error?: string | null;
}

/**
 * Horizontal semester chips strip (wireframes 02/03; FC25 roadmap
 * navigation). One chip per semester: term, hours + course count, lifecycle
 * status, and an issue badge when the engine flags it (FC29/FC32 verdict
 * counts come from the api layer — display only). Selecting a chip drives
 * the detail panel below.
 */
export default function SemesterTimeline({ semesters, selectedId, onSelect, loading = false, error = null }: SemesterTimelineProps) {
  if (loading) {
    return (
      <section className="semester-timeline" aria-busy="true">
        <p className="semester-timeline-state">Loading your timeline…</p>
      </section>
    );
  }
  if (error) {
    return (
      <section className="semester-timeline">
        <p className="semester-timeline-state semester-timeline-state--error">
          Could not load the timeline: {error}
        </p>
      </section>
    );
  }
  if (!semesters || semesters.length === 0) {
    return (
      <section className="semester-timeline">
        <p className="semester-timeline-state">No semesters in this plan yet.</p>
      </section>
    );
  }
  return (
    <section className="semester-timeline" aria-label="Semesters in order">
      <ul className="semester-timeline-list">
        {semesters.map((semester) => (
          <li key={semester.id}>
            <button
              type="button"
              className={`semester-timeline-chip semester-timeline-chip--${semester.status}${
                selectedId === semester.id ? ' semester-timeline-chip--selected' : ''
              }`}
              aria-pressed={selectedId === semester.id}
              onClick={() => onSelect?.(semester.id)}
            >
              <span className="semester-timeline-chip-term">
                {semester.term} {semester.year}
              </span>
              <span className="semester-timeline-chip-meta">
                {semester.credits} hrs · {semester.courseCount} course{semester.courseCount === 1 ? '' : 's'}
              </span>
              <Badge variant={STATUS_VARIANTS[semester.status]} dot>
                {STATUS_LABELS[semester.status]}
              </Badge>
              {semester.issueCount > 0 ? (
                <Badge variant="warning">
                  {semester.issueCount} issue{semester.issueCount === 1 ? '' : 's'}
                </Badge>
              ) : null}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}