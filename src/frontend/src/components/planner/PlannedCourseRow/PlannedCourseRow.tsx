import ClassStatusSelect from '../../classes/ClassStatusSelect/ClassStatusSelect';
import type { ClassStatus } from '../../../api/classes';
import Badge from '../../shared/Badge/Badge';
import Icon from '../../shared/Icon/Icon';
import { formatCourseCode, toTitleCase } from '../../shared/textCase';
import type { SemesterCourse } from '../../../api/types';
import './PlannedCourseRow.css';

interface PlannedCourseRowProps {
  course: SemesterCourse;
  /** Engineering-verdict text shown under the row (FC29 display). */
  warning?: string | null;
  /** e.g. 'In progress' via a Badge variant (FC21 display). */
  statusNote?: string;
  onRemove?: (courseId: string) => void;
  /** FC21 status control — shown when `onStatusChange` is given. */
  status?: ClassStatus;
  onStatusChange?: (courseId: string, next: ClassStatus) => Promise<unknown> | void;
}

/**
 * One course row of a timeline semester (wireframes 02/03; FC3 editing
 * surface): code, title, hours + meeting line (FC12 schedule display), the
 * remove action, and — when the api layer flags it — the engine's
 * prerequisite warning (FC29 verdict display). Unknown ids render the id
 * alone (grounded-UI).
 */
export default function PlannedCourseRow({ course, warning = null, statusNote, onRemove, status, onStatusChange }: PlannedCourseRowProps) {
  return (
    <li className="planned-course-row">
      <div className="planned-course-row-main">
        <span className="planned-course-row-text">
          <span className="planned-course-row-title">
            <strong className="planned-course-row-code">{formatCourseCode(course.id)}</strong>{' '}
            {course.title ? toTitleCase(course.title) : 'Course details unavailable'}
          </span>
          <span className="planned-course-row-meta">
            {course.creditHours != null ? `${course.creditHours} hrs` : ''}
            {course.meeting ? ` · ${course.meeting}` : ''}
          </span>
        </span>
        {statusNote ? (
          <Badge variant="info" dot>
            {statusNote}
          </Badge>
        ) : null}
        {onStatusChange ? (
          <ClassStatusSelect
            courseLabel={formatCourseCode(course.id)}
            status={status}
            onChange={(next) => onStatusChange(course.id, next)}
          />
        ) : null}
        {onRemove ? (
          <button
            type="button"
            className="planned-course-row-remove"
            onClick={() => onRemove(course.id)}
            aria-label={`Remove ${formatCourseCode(course.id)}`}
          >
            <Icon name="minus" size={16} />
          </button>
        ) : null}
      </div>
      {warning ? (
        <p className="planned-course-row-warning" role="status">
          <Icon name="warning" size={14} /> {warning}
        </p>
      ) : null}
    </li>
  );
}