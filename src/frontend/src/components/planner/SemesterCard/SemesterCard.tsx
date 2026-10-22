import Badge from '../../shared/Badge/Badge';
import Button from '../../shared/Button/Button';
import { formatCourseCode, toTitleCase } from '../../shared/textCase';
import type { CourseCatalog, SemesterStatus } from '../../../api/types';
import './SemesterCard.css';

const STATUS_LABELS: Record<SemesterStatus, string> = {
  completed: 'Completed',
  'in-progress': 'In progress',
  planned: 'Planned',
  optional: 'Optional',
};

const STATUS_VARIANTS: Record<SemesterStatus, 'success' | 'info' | 'primary' | 'neutral'> = {
  completed: 'success',
  'in-progress': 'info',
  planned: 'neutral',
  optional: 'neutral',
};

interface SemesterCardProps {
  /** One roadmap semester (FC25). */
  semester: { term: string; year: number; courses: string[]; credits?: number };
  /** Course metadata from the api layer. Chips whose id is missing render
      the id alone with no invented details (grounded-UI rule). */
  catalog?: CourseCatalog;
  status?: SemesterStatus;
  /** Renders the Edit button when given (FC3 edit entry point). */
  onEdit?: () => void;
  onEditLabel?: string;
  emptyNote?: string;
}

/**
 * One semester of a degree plan (FC25) — used on the Home "My semesters"
 * grid (wireframe 01). Renders the term/year header with an optional status
 * badge (FC14/FC21 lifecycle), the semester credit total (kept under the
 * degree's per-semester cap by the deterministic engine — FC32), the Edit
 * action (FC3) when provided, and one code/title line per planned course.
 * Optional semesters (e.g. summer, not in the plan) render as a dashed card
 * with an "Add <term>" button wired to the same FC3 edit entry point.
 */
export default function SemesterCard({
  semester,
  catalog = {},
  status,
  onEdit,
  onEditLabel = 'Edit',
  emptyNote,
}: SemesterCardProps) {
  const { term, year, courses = [], credits } = semester ?? {};
  const isOptional = status === 'optional';
  if (isOptional) {
    return (
      <article className="semester-card semester-card--optional">
        <h3 className="semester-card-term">{term} {year}</h3>
        <p className="semester-card-empty">{emptyNote ?? 'Optional · not in your plan'}</p>
        {onEdit ? (
          <div>
            <Button variant="ghost" onClick={onEdit}>
              Add {term.toLowerCase()}
            </Button>
          </div>
        ) : null}
      </article>
    );
  }
  return (
    <article className="semester-card">
      <header className="semester-card-header">
        <h3 className="semester-card-term">{term} {year}</h3>
        {onEdit && (
          <button type="button" className="semester-card-edit" onClick={onEdit}>
            {onEditLabel}
          </button>
        )}
      </header>
      <p className="semester-card-meta">
        {status ? (
          <Badge variant={STATUS_VARIANTS[status]}>
            {STATUS_LABELS[status]}
          </Badge>
        ) : null}
        <span className="semester-card-credits">{credits == null ? '— hrs' : `${credits} hrs`}</span>
      </p>
      {courses.length === 0 ? (
        <p className="semester-card-empty">{emptyNote ?? 'No courses planned.'}</p>
      ) : (
        <ul className="semester-card-list">
          {courses.map((id) => {
            const course = catalog[id];
            return (
              <li
                key={id}
                className={`semester-card-chip${course ? '' : ' semester-card-chip--unknown'}`}
              >
                <span className="semester-card-chip-id">{formatCourseCode(id)}</span>
                <span className="semester-card-chip-title">
                  {course ? toTitleCase(course.title) : 'Course details unavailable'}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </article>
  );
}