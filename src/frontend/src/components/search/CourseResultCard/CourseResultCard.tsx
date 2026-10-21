import Badge from '../../shared/Badge/Badge';
import Button from '../../shared/Button/Button';
import { toTitleCase } from '../../shared/textCase';
import type { CourseResult } from '../../../api/types';
import './CourseResultCard.css';

interface CourseResultCardProps {
  course: CourseResult;
  onDetails?: (courseId: string) => void;
  detailsBusy?: boolean;
}

/**
 * One matching-course card (wireframe 04; FC8/FC11/FC12 display + FC29–FC32
 * verdict badges). The flags — "Prerequisites met", "Needs CSE 4380 first",
 * "Conflicts with CSE 4382" — arrive from the api layer as engine verdicts
 * (display only; the client never computes constraints).
 */
export default function CourseResultCard({ course, onDetails, detailsBusy = false }: CourseResultCardProps) {
  return (
    <article className="course-result-card" aria-label={`Course: ${course.title}`}>
      <header className="course-result-card-header">
        <h3 className="course-result-card-title">
          <span className="course-result-card-code">{course.id}</span> {toTitleCase(course.title)}
        </h3>
        <Button variant="secondary" onClick={() => onDetails?.(course.id)} disabled={detailsBusy}>
          Details
        </Button>
      </header>
      <p className="course-result-card-meta">
        {course.creditHours} hrs{course.meeting ? ` · ${course.meeting}` : ''}
        {course.term ? ` · ${course.term}` : ''}
      </p>
      <p className="course-result-card-description">{course.description}</p>
      {course.flags.length > 0 ? (
        <footer className="course-result-card-flags">
          {course.flags.map((flag) => (
            <Badge key={flag.label} variant={flag.variant}>{flag.label}</Badge>
          ))}
        </footer>
      ) : null}
    </article>
  );
}