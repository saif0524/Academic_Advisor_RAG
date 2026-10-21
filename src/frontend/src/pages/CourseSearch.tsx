import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import AppShell from '../components/shared/AppShell/AppShell';
import type { PageId } from '../components/shared/AppSidebar/AppSidebar';
import CourseSearchBox from '../components/search/CourseSearchBox/CourseSearchBox';
import AdvisorAnswerCard from '../components/search/AdvisorAnswerCard/AdvisorAnswerCard';
import SearchFilterChips from '../components/search/SearchFilterChips/SearchFilterChips';
import type { SearchFilter } from '../components/search/SearchFilterChips/SearchFilterChips';
import CourseResultCard from '../components/search/CourseResultCard/CourseResultCard';
import CourseDetailDialog from '../components/search/CourseDetailDialog/CourseDetailDialog';
import { getCourseDetailLive, searchLive } from '../api/liveSearch';
import type { CourseDetail, SearchResponse } from '../api/types';
import './CourseSearch.css';

interface CourseSearchProps {
  active?: PageId;
  onNavigate?: (page: PageId) => void;
  chatOpen?: boolean;
  onToggleChat?: () => void;
  chatSlot?: ReactNode;
  /** DI seams (stories inject canned fixtures); default to the api mocks. */
  searchFn?: (query: string) => Promise<SearchResponse>;
  detailFn?: (courseId: string) => Promise<CourseDetail | null>;
}

/**
 * Search page (wireframe 04): one box — course codes/titles (FC8, SQLite
 * path) or plain-language questions (FC9, Chroma path) — an advisor answer
 * card powered by the SAME live agent as the chat drawer (FC22, persisted
 * FC34), FC10 filter chips, and matching course cards with engine-verdict
 * badges from the FC24 audit endpoint (FC29–FC32). Details opens the
 * FC11/FC12 dialog. All data through the api seams; stories inject fixtures.
 */
export default function CourseSearch({
  active = 'search',
  onNavigate,
  chatOpen = false,
  onToggleChat,
  chatSlot = null,
  searchFn = searchLive,
  detailFn = getCourseDetailLive,
}: CourseSearchProps) {
  const [submitted, setSubmitted] = useState('');
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilters, setActiveFilters] = useState<string[]>([]);

  const [detail, setDetail] = useState<CourseDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const runSearch = async (query: string) => {
    setSubmitted(query);
    setLoading(true);
    setError(null);
    setActiveFilters([]);
    try {
      const result = await searchFn(query);
      setResponse(result);
    } catch (searchError) {
      setResponse(null);
      setError(searchError instanceof Error ? searchError.message : String(searchError));
    } finally {
      setLoading(false);
    }
  };

  const courseFilters: SearchFilter[] = useMemo(() => {
    const courses = response?.courses ?? [];
    // Terms derive from the actual results — no hardcoded semester labels.
    const terms = [...new Set(courses.map((c) => c.term).filter((t): t is string => Boolean(t)))];
    const primaryTerm = terms[0] ?? 'All terms';
    return [
      ...(terms.length > 0 ? [{ id: 'term', label: primaryTerm, count: courses.filter((c) => c.term === primaryTerm).length }] : []),
      {
        id: 'degree',
        label: 'Counts toward my degree',
        count: courses.filter((c) => !c.flags.some((f) => f.label.startsWith("Doesn't count"))).length,
      },
      {
        id: 'schedule',
        label: 'Fits my schedule',
        count: courses.filter((c) => !c.flags.some((f) => f.variant === 'danger')).length,
      },
    ];
  }, [response]);

  const primaryTerm = useMemo(
    () => ([...new Set((response?.courses ?? []).map((c) => c.term).filter((t): t is string => Boolean(t)))])[0] ?? 'Spring 2027',
    [response],
  );

  const filteredCourses = useMemo(() => {
    const courses = response?.courses ?? [];
    return courses.filter((course) => {
      if (activeFilters.includes('term') && course.term !== primaryTerm) return false;
      if (activeFilters.includes('degree') && course.flags.some((f) => f.label.startsWith("Doesn't count"))) return false;
      if (activeFilters.includes('schedule') && course.flags.some((f) => f.variant === 'danger')) return false;
      return true;
    });
  }, [response, activeFilters, primaryTerm]);

  const handleDetails = async (courseId: string) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailError(null);
    setDetail(null);
    try {
      const result = await detailFn(courseId);
      if (result === null) setDetailError(`No details on record for CSE ${courseId}.`);
      else setDetail(result);
    } catch (error) {
      setDetailError(error instanceof Error ? error.message : String(error));
    } finally {
      setDetailLoading(false);
    }
  };

  const hasSearched = submitted !== '';

  return (
    <AppShell active={active} onNavigate={onNavigate} chatOpen={chatOpen} onToggleChat={onToggleChat} chatSlot={chatSlot}>
      <main className="course-search">
        <header className="course-search-header">
          <h1 className="course-search-title">Search</h1>
        </header>
        <CourseSearchBox onSearch={runSearch} busy={loading} />
        {hasSearched ? (
          <>
            <AdvisorAnswerCard answer={response?.answer ?? null} loading={loading} error={error} />
            {!loading && !error && (response?.courses.length ?? 0) > 0 ? (
              <SearchFilterChips
                filters={courseFilters}
                activeIds={activeFilters}
                onToggle={(id, nextActive) =>
                  setActiveFilters((current) =>
                    nextActive ? [...current, id] : current.filter((existing) => existing !== id),
                  )
                }
              />
            ) : null}
            {!loading && !error && filteredCourses.length > 0 ? (
              <div className="course-search-results">
                {filteredCourses.map((course) => (
                  <CourseResultCard key={course.id} course={course} onDetails={handleDetails} />
                ))}
              </div>
            ) : null}
            {!loading && !error && (response?.courses.length ?? 0) === 0 ? (
              <p className="course-search-empty" role="status">
                No matching courses on record — try a CSE course code or a question about your plan.
              </p>
            ) : null}
          </>
        ) : null}
        <CourseDetailDialog
          open={detailOpen}
          detail={detail}
          loading={detailLoading}
          error={detailError}
          onClose={() => setDetailOpen(false)}
        />
      </main>
    </AppShell>
  );
}