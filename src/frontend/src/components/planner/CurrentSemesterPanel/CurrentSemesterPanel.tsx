import Button from '../../shared/Button/Button';
import { formatCourseCode, toTitleCase } from '../../shared/textCase';
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
  /** "View schedule" action (FC14) — hidden when not given. */
  onViewSchedule?: () => void;
  /** "Add or drop" action (FC20/FC21 entry point) — hidden when not given. */
  onAddOrDrop?: () => void;
}

/**
 * Home "This semester" block (wireframe 01): a lime "In progress · <term>"
 * strip with the term's credit total, then the student's current classes
 * (FC14) as code · title · hours rows, and the View schedule / Add or drop
 * entry points (FC14, FC20/FC21 — the actual changes happen behind their
 * confirmation flows, never here). Unknown course ids render the code alone
 * (grounded-UI rule); hours sum only known credit values.
 */
export default function CurrentSemesterPanel({
  term,
  courses,
  loading = false,
  error = null,
  onViewSchedule,
  onAddOrDrop,
}: CurrentSemesterPanelProps) {
  const hasCourses = !loading && !error && courses && courses.length > 0;
  const totalHours = (courses ?? []).reduce((sum, course) => sum + (course.creditHours ?? 0), 0);
  return (
    <section className="current-semester-panel" aria-label={`This semester — ${term}`}>
      <header className="current-semester-panel-strip">
        <span>In progress{term ? ` · ${term}` : ''}</span>
        {hasCourses && totalHours > 0 ? <span>{totalHours} hrs</span> : null}
      </header>
      <div className="current-semester-panel-body">
        <h2 className="current-semester-panel-title">This semester</h2>
        {loading ? <p className="current-semester-panel-state">Loading schedule…</p> : null}
        {error ? (
          <p className="current-semester-panel-state current-semester-panel-state--error">
            Could not load this semester: {error}
          </p>
        ) : null}
        {!loading && !error && (!courses || courses.length === 0) ? (
          <p className="current-semester-panel-state">No classes on your schedule for this term.</p>
        ) : null}
        {hasCourses ? (
          <ul className="current-semester-panel-list">
            {courses.map((course) => (
              <li key={course.id} className="current-semester-panel-row">
                <span className="current-semester-panel-code">{formatCourseCode(course.id)}</span>
                <span className="current-semester-panel-name">
                  {course.title ? toTitleCase(course.title) : 'Course details unavailable'}
                </span>
                <span className="current-semester-panel-hours">
                  {course.creditHours != null ? `${course.creditHours} hrs` : ''}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
        {onViewSchedule || onAddOrDrop ? (
          <div className="current-semester-panel-actions">
            {onViewSchedule ? <Button onClick={onViewSchedule}>View schedule</Button> : null}
            {onAddOrDrop ? (
              <Button variant="secondary" onClick={onAddOrDrop}>
                Add or drop
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
