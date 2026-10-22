import { useState } from 'react';
import Button from '../../shared/Button/Button';
import SearchInput from '../../shared/SearchInput/SearchInput';
import './CourseSearchBox.css';

const EXAMPLE_QUERIES = [
  'What should I take next semester?',
  'What does CSE 4380 cover?',
  'Which security electives fit my Spring 2027 schedule?',
];

interface CourseSearchBoxProps {
  /** Parent-owned search action; the box owns only the draft query. */
  onSearch?: (query: string) => void;
  /** Pins the field + buttons while a search runs. */
  busy?: boolean;
}

/**
 * Search entry (wireframe 04): one box for course codes/titles (FC8)
 * or plain-language questions (FC9). The
 * example chips (FC35 prompt-based queries) fill-and-submit the query.
 */
export default function CourseSearchBox({ onSearch, busy = false }: CourseSearchBoxProps) {
  const [query, setQuery] = useState('');
  const submit = (text = query) => {
    const trimmed = (text ?? '').trim();
    if (trimmed === '' || busy) return;
    onSearch?.(trimmed);
  };
  return (
    <section className="course-search-box" aria-label="Course search">
      <p className="course-search-box-hint">
        Type a course code or title, or ask a question in plain language
      </p>
      <form
        className="course-search-box-row"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="CSE 4380, operating systems, or a question…"
          suggestions={[]}
          label="Search courses or ask a question"
          noResultsText=""
        />
        <Button type="submit" disabled={busy}>
          {busy ? 'Searching…' : 'Search'}
        </Button>
      </form>
      <div className="course-search-box-examples" aria-label="Example questions">
        {EXAMPLE_QUERIES.map((example) => (
          <button
            key={example}
            type="button"
            className="course-search-box-example"
            onClick={() => {
              setQuery(example);
              submit(example);
            }}
            disabled={busy}
          >
            {example}
          </button>
        ))}
      </div>
    </section>
  );
}