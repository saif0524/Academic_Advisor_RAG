import Badge from '../../shared/Badge/Badge';
import Button from '../../shared/Button/Button';
import Icon from '../../shared/Icon/Icon';
import { toTitleCase } from '../../shared/textCase';
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
  planned: 'primary',
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
 * action (FC3) when provided, and one chip per planned course.
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
  const isSummer = term === 'Summer';
  return (
    <article className={`semester-card${isSummer ? ' semester-card--summer' : ''}`}>
      <header className="semester-card-header">
        <h3 className="semester-card-term">{term} {year}</h3>
        {onEdit && (
          <Button variant="ghost" onClick={onEdit}>
            <Icon name="edit" size={14} /> {onEditLabel}
          </Button>
        )}
      </header>
      <p className="semester-card-meta">
        {status ? (
          <Badge variant={STATUS_VARIANTS[status]} dot>
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
                <span className="semester-card-chip-id">{id}</span>
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