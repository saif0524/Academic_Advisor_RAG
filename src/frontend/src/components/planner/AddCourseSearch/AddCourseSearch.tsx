import Icon from '../../shared/Icon/Icon';
import SearchInput from '../../shared/SearchInput/SearchInput';
import { formatCourseCode, toTitleCase } from '../../shared/textCase';
import type { CourseSuggestion } from '../../../api/types';
import './AddCourseSearch.css';

interface AddCourseSearchProps {
  value: string;
  onChange: (next: string) => void;
  /** null → suggestions unavailable for this term (explicit empty state). */
  candidates?: CourseSuggestion[] | null;
  onPick?: (courseId: string) => void;
  loading?: boolean;
  error?: string | null;
}

/**
 * Timeline "Add a course" card (wireframes 02–03; FC8 search + FC29 verdict
 * display on candidates). A search field filters the candidate list (the
 * parent owns the query and the fetch); every candidate shows code, title,
 * hours/meeting and a round "+" that stages it in the parent's draft — the
 * deterministic engine re-reviews the draft; nothing is applied server-side
 * here. A candidate's verdict line renders only when the api layer supplies
 * a real verdict (non-neutral badge) — never invented (grounded-UI rule).
 */
export default function AddCourseSearch({
  value,
  onChange,
  candidates = null,
  onPick,
  loading = false,
  error = null,
}: AddCourseSearchProps) {
  return (
    <section className="add-course-search" aria-label="Add a course">
      <h3 className="add-course-search-title">Add a course</h3>
      {candidates !== null || value ? (
        <SearchInput
          value={value}
          onChange={onChange}
          placeholder="Search by code or title"
          label="Add a course — search by code or title"
        />
      ) : null}
      {loading ? <p className="add-course-search-state">Loading candidate courses…</p> : null}
      {error ? (
        <p className="add-course-search-state add-course-search-state--error">
          Could not load candidates: {error}
        </p>
      ) : null}
      {!loading && !error && candidates === null ? (
        <p className="add-course-search-state">Course suggestions are unavailable for this term.</p>
      ) : null}
      {!loading && !error && candidates !== null && candidates.length === 0 ? (
        <p className="add-course-search-state">No matching CSE courses on record.</p>
      ) : null}
      {!loading && !error && candidates && candidates.length > 0 ? (
        <ul className="add-course-search-list">
          {candidates.map((course) => {
            const code = formatCourseCode(course.id);
            const meta = [course.creditHours != null ? `${course.creditHours} hrs` : null, course.meeting]
              .filter(Boolean)
              .join(' · ');
            return (
              <li key={course.id} className="add-course-search-row">
                <span className="add-course-search-text">
                  <span>
                    <strong>{code}</strong> {course.title ? toTitleCase(course.title) : 'Course details unavailable'}
                  </span>
                  {meta ? <span className="add-course-search-meta">{meta}</span> : null}
                  {course.badge && course.badgeVariant !== 'neutral' ? (
                    <span className={`add-course-search-verdict add-course-search-verdict--${course.badgeVariant}`}>
                      {course.badge}
                    </span>
                  ) : null}
                </span>
                <button
                  type="button"
                  className="add-course-search-add"
                  onClick={() => onPick?.(course.id)}
                  aria-label={`Add ${code}`}
                >
                  <Icon name="plus" size={18} />
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
