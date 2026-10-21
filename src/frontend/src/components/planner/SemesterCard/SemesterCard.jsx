import './SemesterCard.css';

/**
 * One semester of a degree plan roadmap (FC25). Renders the term/year header,
 * the semester credit total (which the plan's per-semester cap keeps under
 * the degree limit — FC32, enforced by the deterministic engine), and one
 * chip per planned course.
 *
 * Props:
 * - semester: { term: string, year: number, courses: string[], credits?: number }
 * - catalog: Record<courseId, { id, title, creditHours }> — course metadata,
 *   provided by the api service layer. Chips whose id is missing from the
 *   catalog render the id alone with no invented details (grounded-UI rule).
 */
export default function SemesterCard({ semester, catalog = {} }) {
  const { term, year, courses = [], credits } = semester ?? {};
  const isSummer = term === 'Summer';
  return (
    <article className={`semester-card${isSummer ? ' semester-card--summer' : ''}`}>
      <header className="semester-card-header">
        <h3 className="semester-card-term">
          {term} {year}
          {isSummer && <span className="semester-card-summer-flag"> (summer)</span>}
        </h3>
        <span className="semester-card-credits">
          {credits == null ? '—' : `${credits} credit${credits === 1 ? '' : 's'}`}
        </span>
      </header>
      {courses.length === 0 ? (
        <p className="semester-card-empty">No courses planned.</p>
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

// Seed corpus titles are stored uppercase (data/course-desc.jsonl); they are
// displayed in title case per product convention. Keep original casing for
// acronyms ("cse" → "CSE", "iot" → "IoT") — title-casing would mangle them.
const SMALL_WORDS = new Set([
  'a', 'an', 'the', 'and', 'or', 'for', 'to', 'in', 'of', 'on', 'with', 'via',
]);
const DISPLAY_ACRONYMS = { cse: 'CSE', iot: 'IoT', 'c++': 'C++', soc: 'SoC' };

function toTitleCase(title) {
  return String(title)
    .trim()
    .replace(/\.$/, '')
    .toLowerCase()
    .split(/\s+/)
    .map((word, index) => displayWord(word, index === 0))
    .join(' ');
}

function displayWord(word, isFirst) {
  const acronym = DISPLAY_ACRONYMS[word];
  if (acronym) return acronym;
  if (!isFirst && SMALL_WORDS.has(word)) return word;
  return word.replace(/(^|[-/])(\w)/g, (_, separator, letter) => separator + letter.toUpperCase());
}