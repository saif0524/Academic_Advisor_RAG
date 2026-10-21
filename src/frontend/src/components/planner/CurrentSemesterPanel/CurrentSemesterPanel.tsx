import Badge from '../../shared/Badge/Badge';
import { toTitleCase } from '../../shared/textCase';
import './CurrentSemesterPanel.css';

export interface CurrentSemesterCourse {
  id: string;
  title?: string | null;
  creditHours?: number | null;
  status?: 'in-progress' | 'completed' | 'planned';
}

interface CurrentSemesterPanelProps {
  term: string;
  courses: CurrentSemesterCourse[] | null;
  loading?: boolean;
  error?: string | null;
}

const STATUS_VARIANTS: Record<NonNullable<CurrentSemesterCourse['status']>, 'info' | 'success' | 'primary'> = {
  'in-progress': 'info',
  completed: 'success',
  planned: 'primary',
};

const STATUS_LABELS: Record<NonNullable<CurrentSemesterCourse['status']>, string> = {
  'in-progress': 'In progress',
  completed: 'Completed',
  planned: 'Planned',
};

/**
 * Home "This semester" block (wireframe 01): the student's current schedule
 * — the classes on their profile for the active term (FC14) with their
 * lifecycle status (FC21 states map directly to the badges). Read-only
 * display; status changes and removal live in the deferred FC20/FC21 flows.
 * Unknown course ids render the id alone (grounded-UI rule).
 */
export default function CurrentSemesterPanel({ term, courses, loading = false, error = null }: CurrentSemesterPanelProps) {
  return (
    <section className="current-semester-panel" aria-label={`This semester — ${term}`}>
      <header className="current-semester-panel-header">
        <h2 className="current-semester-panel-title">This semester</h2>
        {term ? (
          <Badge variant="info" dot>
            {term}
          </Badge>
        ) : null}
      </header>
      {loading ? <p className="current-semester-panel-state">Loading schedule…</p> : null}
      {error ? (
        <p className="current-semester-panel-state current-semester-panel-state--error">
          Could not load this semester: {error}
        </p>
      ) : null}
      {!loading && !error && (!courses || courses.length === 0) ? (
        <p className="current-semester-panel-state">No classes on your schedule for this term.</p>
      ) : null}
      {!loading && !error && courses && courses.length > 0 ? (
        <ul className="current-semester-panel-list">
          {courses.map((course) => (
            <li key={course.id} className="current-semester-panel-row">
              <span className="current-semester-panel-code">{course.id}</span>
              <span className="current-semester-panel-name">
                {course.title ? toTitleCase(course.title) : 'Course details unavailable'}
              </span>
              {course.status ? (
                <Badge variant={STATUS_VARIANTS[course.status]} dot>
                  {STATUS_LABELS[course.status]}
                </Badge>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}