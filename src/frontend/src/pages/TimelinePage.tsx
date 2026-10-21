import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import AppShell from '../components/shared/AppShell/AppShell';
import type { PageId } from '../components/shared/AppSidebar/AppSidebar';
import SemesterTimeline from '../components/planner/SemesterTimeline/SemesterTimeline';
import SemesterDetail from '../components/planner/SemesterDetail/SemesterDetail';
import UnsavedChangesBar from '../components/planner/UnsavedChangesBar/UnsavedChangesBar';
import { getActivePlan, getCourseCatalog, reviewPlanDraft, savePlanDraft } from '../api/plans';
import { getCourseSuggestions } from '../api/courses';
import { getMeeting } from '../api/catalog';
import type {
  ActivePlanData,
  CourseCatalog,
  CourseSuggestion,
  PlanReview,
  Semester,
  SemesterHydrated,
  SemesterSummary,
} from '../api/types';
import './TimelinePage.css';

export interface TimelineDependencies {
  plan: ActivePlanData | null;
  catalog: CourseCatalog;
}

interface TimelinePageProps {
  active?: PageId;
  onNavigate?: (page: PageId) => void;
  chatOpen?: boolean;
  onToggleChat?: () => void;
  chatSlot?: ReactNode;
  /** DI seam (stories inject instant fixtures); defaults to the api mock. */
  loadDependencies?: () => Promise<TimelineDependencies>;
}

async function defaultLoadDependencies(): Promise<TimelineDependencies> {
  const [plan, catalog] = await Promise.all([getActivePlan(), getCourseCatalog()]);
  return { plan, catalog };
}

const creditsFor = (courseIds: string[], catalog: CourseCatalog): number =>
  courseIds.reduce((sum, id) => sum + (catalog[id]?.creditHours ?? 0), 0);

/**
 * Timeline page (wireframes 02/03; FC3): select a semester chip, edit its
 * courses (remove / add via search), and see live engine-verdict feedback —
 * the plan check banner and per-course warnings come from the api seam's
 * deterministic review (mock of CourseRecommendationValidator, FC29–FC32,
 * display only). Edits stage a draft; "Unsaved changes — Discard | Save
 * plan" persists via the api seam (FC3). The in-progress semester is
 * read-only — those classes are on the profile (FC14/FC21).
 */
export default function TimelinePage({
  active = 'timeline',
  onNavigate,
  chatOpen = false,
  onToggleChat,
  chatSlot = null,
  loadDependencies,
}: TimelinePageProps) {
  const loadData = loadDependencies ?? defaultLoadDependencies;
  const [plan, setPlan] = useState<ActivePlanData | null>(null);
  const [catalog, setCatalog] = useState<CourseCatalog>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Semester[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [candidates, setCandidates] = useState<CourseSuggestion[] | null>(null);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [candidatesError, setCandidatesError] = useState<string | null>(null);

  useEffect(() => {
    // External system: the api seam. Mount state (loading=true) is covered
    // by useState defaults; seam changes remount the page, so all setState
    // calls happen after the await.
    let cancelled = false;
    const run = async () => {
      try {
        const { plan: loadedPlan, catalog: loadedCatalog } = await loadData();
        if (cancelled) return;
        setPlan(loadedPlan);
        setCatalog(loadedCatalog);
        const defaultSemester =
          loadedPlan?.semesters.find((s) => s.status === 'planned') ?? loadedPlan?.semesters[0];
        setSelectedId(defaultSemester?.id ?? null);
        setDraft(loadedPlan ? loadedPlan.semesters.map((s) => ({ ...s, courseIds: [...s.courseIds] })) : null);
      } catch (error) {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : String(error));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [loadData]);

  /* Live engine-verdict display: the deterministic review runs over the
     draft whenever it changes (mock seam for the FC29–FC32 validator). */
  const check: PlanReview | null = useMemo(() => (draft ? reviewPlanDraft(draft) : null), [draft]);

  const selected = draft?.find((semester) => semester.id === selectedId) ?? null;
  const selectedIsEditable = selected !== null && selected.status !== 'in-progress';

  /* Hydrated rows for the detail panel: catalog titles + meetings + the
     per-course warning text from the review (grounded data only). */
  const selectedSemester: SemesterHydrated | null = useMemo(() => {
    if (!selected) return null;
    return {
      ...selected,
      courses: selected.courseIds.map((id) => {
        const course = catalog[id];
        return {
          id,
          title: course?.title ?? null,
          creditHours: course?.creditHours ?? null,
          meeting: getMeeting(id),
          warning: check?.semesterIssues[selected.id]?.find((issue) => issue.course === id)?.text,
        };
      }),
    };
  }, [selected, catalog, check]);

  const summaries: SemesterSummary[] = useMemo(
    () =>
      (draft ?? []).map((semester) => ({
        id: semester.id,
        term: semester.term,
        year: semester.year,
        status: semester.status,
        credits: semester.credits,
        courseCount: semester.courseIds.length,
        issueCount: check?.semesterIssues[semester.id]?.length ?? 0,
      })),
    [draft, check],
  );

  const dirty = useMemo(() => {
    if (!plan || !draft) return false;
    const planKey = JSON.stringify(plan.semesters.map(({ id, courseIds, credits }) => ({ id, courseIds, credits })));
    const draftKey = JSON.stringify(draft.map(({ id, courseIds, credits }) => ({ id, courseIds, credits })));
    return planKey !== draftKey;
  }, [plan, draft]);

  /* Selecting a semester resets the candidate fetch state (event-handler
     sync writes), then the effect fetches fresh candidates post-await. */
  const handleSelectSemester = (id: string) => {
    if (id === selectedId) return;
    setSelectedId(id);
    setSearchTerm('');
    setCandidates(null);
    setCandidatesError(null);
    setCandidatesLoading(true);
  };

  useEffect(() => {
    // External system: the courses suggest endpoint. Sync state is managed in
    // handleSelectSemester; this effect only applies post-await results.
    if (selectedId === null || !selectedIsEditable) return;
    let cancelled = false;
    const run = async () => {
      try {
        const suggestions = await getCourseSuggestions(selectedId, selected?.courseIds ?? []);
        if (!cancelled) {
          setCandidates(suggestions);
          setCandidatesLoading(false);
        }
      } catch (error) {
        if (!cancelled) {
          setCandidatesError(error instanceof Error ? error.message : String(error));
          setCandidatesLoading(false);
        }
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [selectedId, selectedIsEditable, selected, searchTerm]);

  /* FC3 mutations stage a draft only; Save persists via the api seam. */
  const stageSemester = (mutate: (courseIds: string[]) => string[] | null) => {
    setDraft((current) => {
      if (!current) return current;
      return current.map((semester) => {
        if (semester.id !== selectedId) return semester;
        const nextIds = mutate(semester.courseIds);
        if (nextIds === null) return semester;
        return { ...semester, courseIds: nextIds, credits: creditsFor(nextIds, catalog) };
      });
    });
  };

  const handleRemoveCourse = (courseId: string) => {
    if (!selectedIsEditable) return; // profile classes are read-only
    stageSemester((courseIds) => courseIds.filter((id) => id !== courseId));
  };

  const handlePickCourse = (courseId: string) => {
    if (!selectedIsEditable) return;
    stageSemester((courseIds) => (courseIds.includes(courseId) ? null : [...courseIds, courseId]));
    // Remove the picked course from the visible candidate list synchronously
    // (event handler) — the engine re-reviews the new draft via check.
    setCandidates((current) => (current ? current.filter((course) => course.id !== courseId) : current));
    setSearchTerm('');
  };

  const handleDiscard = () => {
    if (!plan) return;
    setDraft(plan.semesters.map((s) => ({ ...s, courseIds: [...s.courseIds] })));
    setSaveError(null);
  };

  const handleSave = async () => {
    if (!draft) return;
    setSaving(true);
    setSaveError(null);
    try {
      await savePlanDraft();
      const nextCheck = reviewPlanDraft(draft);
      setPlan((current) =>
        current
          ? { ...current, semesters: draft.map((s) => ({ ...s, courseIds: [...s.courseIds] })), check: nextCheck }
          : current,
      );
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  };

  /* Loading signal for the detail panel's add-course search. */
  const showCandidatesLoading = candidatesLoading || (selectedIsEditable && candidates === null && !candidatesError);

  return (
    <AppShell active={active} onNavigate={onNavigate} chatOpen={chatOpen} onToggleChat={onToggleChat} chatSlot={chatSlot}>
      <main className="timeline-page">
        <header className="timeline-page-header">
          <h1 className="timeline-page-title">Timeline</h1>
          {plan ? (
            <p className="timeline-page-program">
              {plan.program.majorName.replace('BS in ', 'BS ')} — {plan.program.concentration}
            </p>
          ) : null}
        </header>
        {loadError ? (
          <p className="timeline-page-error" role="alert">
            Could not load the timeline: {loadError}
          </p>
        ) : (
          <>
            <SemesterTimeline
              semesters={summaries}
              selectedId={selectedId}
              onSelect={handleSelectSemester}
              loading={loading}
            />
            {saveError ? (
              <p className="timeline-page-error" role="alert">
                Could not save the plan: {saveError}
              </p>
            ) : null}
            <SemesterDetail
              semester={selectedSemester}
              creditCap={18}
              check={check}
              onRemoveCourse={handleRemoveCourse}
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              candidates={showCandidatesLoading ? null : selectedIsEditable ? candidates : null}
              onPickCourse={handlePickCourse}
              candidatesLoading={showCandidatesLoading}
              candidatesError={selectedIsEditable ? candidatesError : null}
              loading={loading}
            />
          </>
        )}
        {dirty ? <UnsavedChangesBar onDiscard={handleDiscard} onSave={handleSave} busy={saving} /> : null}
      </main>
    </AppShell>
  );
}