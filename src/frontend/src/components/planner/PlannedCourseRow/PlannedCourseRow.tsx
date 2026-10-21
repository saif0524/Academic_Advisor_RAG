import Badge from '../../shared/Badge/Badge';
import Button from '../../shared/Button/Button';
import Icon from '../../shared/Icon/Icon';
import { toTitleCase } from '../../shared/textCase';
import type { SemesterCourse } from '../../../api/types';
import './PlannedCourseRow.css';

interface PlannedCourseRowProps {
  course: SemesterCourse;
  /** Engineering-verdict text shown under the row (FC29 display). */
  warning?: string | null;
  /** e.g. 'In progress' via a Badge variant (FC21 display). */
  statusNote?: string;
  onRemove?: (courseId: string) => void;
}

/**
 * One course row of a timeline semester (wireframes 02/03; FC3 editing
 * surface): code, title, hours + meeting line (FC12 schedule display), the
 * remove action, and — when the api layer flags it — the engine's
 * prerequisite warning (FC29 verdict display). Unknown ids render the id
 * alone (grounded-UI).
 */
export default function PlannedCourseRow({ course, warning = null, statusNote, onRemove }: PlannedCourseRowProps) {
  return (
    <li className="planned-course-row">
      <div className="planned-course-row-main">
        <span className="planned-course-row-code">{course.id}</span>
        <span className="planned-course-row-text">
          <span className="planned-course-row-title">
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
        {onRemove ? (
          <Button
            variant="ghost"
            iconOnly
            onClick={() => onRemove(course.id)}
            aria-label={`Remove CSE ${course.id}`}
          >
            <Icon name="close" size={14} />
          </Button>
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