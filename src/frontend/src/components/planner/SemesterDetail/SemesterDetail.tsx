import Icon from '../../shared/Icon/Icon';
import ProgressBar from '../../shared/ProgressBar/ProgressBar';
import AddCourseSearch from '../AddCourseSearch/AddCourseSearch';
import PlanCheckBanner from '../PlanCheckBanner/PlanCheckBanner';
import PlannedCourseRow from '../PlannedCourseRow/PlannedCourseRow';
import type { CourseSuggestion, PlanReview, SemesterHydrated, SemesterStatus } from '../../../api/types';
import './SemesterDetail.css';

const STATUS_LABELS: Record<SemesterStatus, string> = {
  completed: 'Completed',
  'in-progress': 'In progress',
  planned: 'Planned',
  optional: 'Optional',
};

interface SemesterDetailProps {
  semester: SemesterHydrated | null;
  /** Per-semester credit cap (mock value from the api layer, FC32). */
  creditCap: number;
  /** Semester-scoped engine verdicts (FC29/FC32 display fields). */
  check?: PlanReview | null;
  onRemoveCourse?: (courseId: string) => void;
  searchTerm?: string;
  onSearchChange?: (next: string) => void;
  candidates?: CourseSuggestion[] | null;
  onPickCourse?: (courseId: string) => void;
  candidatesLoading?: boolean;
  candidatesError?: string | null;
  loading?: boolean;
  error?: string | null;
  /** ‹ › semester stepping; a button renders only when its handler is given. */
  onPrev?: () => void;
  onNext?: () => void;
}

/**
 * Selected-semester editing panel (wireframes 02–03): credit usage against
 * the degree's per-semester cap (FC32 display), the engine check banner
 * (FC29/FC32 verdicts from the api layer), the course rows with inline
 * warnings (FC29 display) and remove actions (FC3 add/edit), and the
 * add-course search. Composition only — all data via props; the page owns
 * the draft state and confirm/save flows. Rows on the in-progress semester
 * are not removable (their classes are on the profile — FC14/FC21).
 */
export default function SemesterDetail({
  semester,
  creditCap,
  check = null,
  onRemoveCourse,
  searchTerm = '',
  onSearchChange,
  candidates = null,
  onPickCourse,
  candidatesLoading = false,
  candidatesError = null,
  loading = false,
  error = null,
  onPrev,
  onNext,
}: SemesterDetailProps) {
  if (loading) {
    return (
      <section className="semester-detail" aria-busy="true">
        <p className="semester-detail-state">Loading this semester…</p>
      </section>
    );
  }
  if (error) {
    return (
      <section className="semester-detail">
        <p className="semester-detail-state semester-detail-state--error">
          Could not load this semester: {error}
        </p>
      </section>
    );
  }
  if (!semester) {
    return (
      <section className="semester-detail">
        <p className="semester-detail-state">
          Select a semester chip above to view and edit its courses.
        </p>
      </section>
    );
  }
  const { term, year, status, credits, courses = [] } = semester;
  const semesterIssues = check?.semesterIssues[semester.id] ?? [];
  const issueTexts = semesterIssues.map((issue) => issue.text);
  return (
    <section className="semester-detail" aria-label={`Semester detail — ${term} ${year}`}>
      <header className="semester-detail-header">
        <div>
          {status ? <p className="semester-detail-kicker">{STATUS_LABELS[status]}</p> : null}
          <h2 className="semester-detail-title">
            {term} {year}
          </h2>
        </div>
        {onPrev || onNext ? (
          <div className="semester-detail-nav">
            <button type="button" className="semester-detail-nav-button" onClick={onPrev} disabled={!onPrev} aria-label="Previous semester">
              <Icon name="chevronLeft" size={18} />
            </button>
            <button type="button" className="semester-detail-nav-button" onClick={onNext} disabled={!onNext} aria-label="Next semester">
              <Icon name="chevronRight" size={18} />
            </button>
          </div>
        ) : null}
      </header>
      <div className="semester-detail-credits">
        <div className="semester-detail-credits-row">
          <strong>
            {credits ?? 0} of {creditCap} credit hours
          </strong>
          <span>
            {courses.length} course{courses.length === 1 ? '' : 's'}
          </span>
        </div>
        <ProgressBar value={credits ?? 0} max={creditCap} label={`Semester credits of the ${creditCap}-hour cap`} />
      </div>
      <div className="semester-detail-columns">
        <div className="semester-detail-card">
          <h3 className="semester-detail-card-title">Courses</h3>
          {check && semesterIssues.length > 0 ? <PlanCheckBanner status="issues" issues={issueTexts} /> : null}
          {courses.length === 0 ? (
            <p className="semester-detail-empty">No courses planned for this term — add one.</p>
          ) : (
            <ul className="semester-detail-list">
              {courses.map((course) => (
                <PlannedCourseRow
                  key={course.id}
                  course={course}
                  warning={course.warning ?? null}
                  onRemove={status === 'in-progress' ? undefined : onRemoveCourse}
                />
              ))}
            </ul>
          )}
          {check && semesterIssues.length === 0 ? <PlanCheckBanner status="ok" /> : null}
        </div>
        <div className="semester-detail-card">
          <AddCourseSearch
            value={searchTerm}
            onChange={(next) => onSearchChange?.(next)}
            candidates={candidates}
            onPick={onPickCourse}
            loading={candidatesLoading}
            error={candidatesError}
          />
        </div>
      </div>
    </section>
  );
}
