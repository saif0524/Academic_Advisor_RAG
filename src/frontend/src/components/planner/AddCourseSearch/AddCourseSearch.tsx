import SearchInput from '../../shared/SearchInput/SearchInput';
import { toTitleCase } from '../../shared/textCase';
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
 * Timeline "Add a course" search (wireframes 02–03; FC8 search entry + FC29
 * verdict badges on candidates). Wraps the shared SearchInput combobox and
 * maps seed courses into suggestion rows. Picking a candidate only stages it
 * in the parent's draft — the deterministic engine re-reviews on the next
 * draft render cycle; nothing is applied server-side here.
 */
export default function AddCourseSearch({
  value,
  onChange,
  candidates = null,
  onPick,
  loading = false,
  error = null,
}: AddCourseSearchProps) {
  const suggestions = (candidates ?? []).map((course) => ({
    id: course.id,
    primary: toTitleCase(course.title ?? 'Course details unavailable'),
    secondary: [course.creditHours != null ? `${course.creditHours} hrs` : null, course.meeting]
      .filter(Boolean)
      .join(' · '),
    badge: course.badge,
    badgeVariant: course.badgeVariant,
  }));
  return (
    <section className="add-course-search" aria-label="Add a course">
      <h3 className="add-course-search-title">Add a course</h3>
      {loading ? <p className="add-course-search-state">Loading candidate courses…</p> : null}
      {error ? (
        <p className="add-course-search-state add-course-search-state--error">
          Could not load candidates: {error}
        </p>
      ) : null}
      {!loading && !error && candidates === null ? (
        <p className="add-course-search-state">Course suggestions are unavailable for this term.</p>
      ) : null}
      {!loading && !error && candidates !== null && (
        <SearchInput
          value={value}
          onChange={onChange}
          placeholder="Search by code or title"
          suggestions={suggestions}
          onSelect={onPick}
          label="Add a course — search by code or title"
          noResultsText="No matching CSE courses on record."
        />
      )}
    </section>
  );
}