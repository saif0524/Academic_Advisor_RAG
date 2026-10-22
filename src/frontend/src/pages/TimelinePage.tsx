import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import AppShell from '../components/shared/AppShell/AppShell';
import type { PageId } from '../components/shared/AppSidebar/AppSidebar';
import Button from '../components/shared/Button/Button';
import Select from '../components/shared/Select/Select';
import SemesterTimeline from '../components/planner/SemesterTimeline/SemesterTimeline';
import SemesterDetail from '../components/planner/SemesterDetail/SemesterDetail';
import UnsavedChangesBar from '../components/planner/UnsavedChangesBar/UnsavedChangesBar';
import { getCourseSuggestions } from '../api/courses';
import {
  activatePlan,
  getPlanById,
  getActivePlan,
  getCourseCatalog,
  listPlanVersions,
  listPlans,
  planDetailToActive,
  revertPlan,
  reviewPlanDraft,
  savePlanDraft,
} from '../api/plans';
import type {
  ActivePlanData,
  CourseCatalog,
  CourseSuggestion,
  PlanListItem,
  PlanReview,
  PlanVersionInfo,
  Semester,
  SemesterHydrated,
  SemesterSummary,
} from '../api/types';
import { useClassStatuses } from '../state/useClassStatuses';
import type { ClassStatus, ClassStatusMap } from '../api/classes';
import './TimelinePage.css';

export interface TimelineDependencies {
  plans: PlanListItem[];
  plan: ActivePlanData | null;
  activePlanId: string | null;
  catalog: CourseCatalog;
}

interface TimelinePageProps {
  active?: PageId;
  onNavigate?: (page: PageId) => void;
  chatOpen?: boolean;
  onToggleChat?: () => void;
  chatSlot?: ReactNode;
  /** DI seam (stories inject instant fixtures); defaults to the live api. */
  loadDependencies?: () => Promise<TimelineDependencies>;
  /** DI seam for the FC29–FC32 draft review (stories inject deterministic
      fixture verdicts; the live default posts to POST /plans/review). */
  reviewFn?: (semesters: Array<Pick<Semester, 'id' | 'term' | 'year' | 'courseIds' | 'credits'>>) => Promise<PlanReview>;
  /** DI seam for add-course candidates (FC8; stories inject fixtures, the
      live default is GET /courses). */
  /** DI seams for FC21 class statuses (stories inject fixtures; live default is /classes). */
  loadClassStatuses?: () => Promise<ClassStatusMap>;
  saveClassStatus?: (courseId: string, status: ClassStatus) => Promise<ClassStatus>;
  searchCourses?: (semesterId: string, alreadyPlannedIds: string[], query: string) => Promise<CourseSuggestion[]>;
}

/** Live defaults (FC6 list + FC3 view + FC8 catalog; the active plan wins,
    the most recently generated plan is the fallback when nothing is active). */
async function defaultLoadDependencies(): Promise<TimelineDependencies> {
  const [plans, activeDetail, catalog] = await Promise.all([
    listPlans(),
    getActivePlan(),
    getCourseCatalog(),
  ]);
  const activePlanId = activeDetail?.plan_id ?? null;
  const fallbackId = plans[plans.length - 1]?.plan_id ?? null;
  let plan = activeDetail ?? null;
  if (plan === null && fallbackId) {
    try {
      plan = planDetailToActive(
        await getPlanById(fallbackId),
        { completionPercent: null, completedHours: null, inProgressHours: null, totalCreditsRequired: null },
      );
    } catch {
      plan = null; // honest empty state when the fallback can't load
    }
  }
  return { plans, plan, activePlanId, catalog };
}

const creditsFor = (courseIds: string[], catalog: CourseCatalog): number =>
  courseIds.reduce((sum, id) => sum + (catalog[id]?.creditHours ?? 0), 0);

/**
 * Timeline page (wireframes 02/03; FC3): select a plan from the student's
 * plans (FC6), edit semester courses (remove / add via live search, FC8),
 * and see engine-verdict feedback — the plan-check banner and per-course
 * warnings come from the server's deterministic review (POST /plans/review,
 * FC29–FC32; never computed client-side). Edits stage a draft; "Save plan"
 * persists via PATCH /plans/{id} (engine-validated, versioned — FC3/FC4).
 * The in-progress semester is read-only — those classes are on the profile
 * (FC14/FC21). "Make active" promotes the plan for the dashboard (FC6).
 */
export default function TimelinePage({
  active = 'timeline',
  onNavigate,
  chatOpen = false,
  onToggleChat,
  chatSlot = null,
  loadDependencies,
  reviewFn,
  searchCourses,
  loadClassStatuses,
  saveClassStatus,
}: TimelinePageProps) {
  const loadData = loadDependencies ?? defaultLoadDependencies;
  const review = reviewFn ?? reviewPlanDraft;
  const { statuses: classStatuses, changeStatus } = useClassStatuses(loadClassStatuses, saveClassStatus);
  const fetchCandidates = searchCourses ?? getCourseSuggestions;
  const [plans, setPlans] = useState<PlanListItem[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [activePlanId, setActivePlanId] = useState<string | null>(null);
  const [plan, setPlan] = useState<ActivePlanData | null>(null);
  const [versions, setVersions] = useState<PlanVersionInfo[]>([]);
  const [catalog, setCatalog] = useState<CourseCatalog>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activating, setActivating] = useState(false);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Semester[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [candidates, setCandidates] = useState<CourseSuggestion[] | null>(null);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [candidatesError, setCandidatesError] = useState<string | null>(null);

  const initialLoad = () => {
    let cancelled = false;
    const run = async () => {
      try {
        const deps = await loadData();
        if (cancelled) return;
        setPlans(deps.plans);
        setActivePlanId(deps.activePlanId);
        setCatalog(deps.catalog);
        setSelectedPlanId(deps.plan?.plan_id ?? deps.plans[deps.plans.length - 1]?.plan_id ?? null);
        setPlan(deps.plan);
        const defaultSemester =
          deps.plan?.semesters.find((s) => s.status === 'planned') ?? deps.plan?.semesters[0];
        setSelectedId(defaultSemester?.id ?? null);
        setDraft(deps.plan ? deps.plan.semesters.map((s) => ({ ...s, courseIds: [...s.courseIds] })) : null);
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
  };

  useEffect(initialLoad, [loadData]);

  /* Switch plans (FC6): load the chosen plan fresh and re-run the review. */
  const handleSelectPlan = (planId: string) => {
    if (planId === selectedPlanId) return;
    setSelectedPlanId(planId);
    setSelectedId(null);
    setDraft(null);
    setLoadError(null);
    const run = async () => {
      try {
        await refreshPlanById(planId);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : String(error));
      }
    };
    void run();
  };

  async function refreshPlanById(planId: string) {
    const detail = await getPlanById(planId);
    const reviewResult = await review(detail.semesters.map((s) => ({
      id: `${s.term.toLowerCase()}-${s.year}`,
      term: s.term, year: s.year, courseIds: s.courses, credits: s.credits ?? 0,
    })));
    const active = planDetailToActive(detail, plan ? {
      completionPercent: null,
      completedHours: plan.progress.completed,
      inProgressHours: plan.progress.inProgress,
      totalCreditsRequired: plan.progress.total,
    } : null);
    setPlan({ ...active, check: reviewResult });
    const defaultSemester =
      active.semesters.find((s) => s.status === 'planned') ?? active.semesters[0];
    setSelectedId(defaultSemester?.id ?? null);
    setDraft(active.semesters.map((s) => ({ ...s, courseIds: [...s.courseIds] })));
    listPlanVersions(planId).then(setVersions).catch(() => setVersions([]));
  }

  /* Live engine-verdict display: the deterministic review (FC29–FC32) runs
     server-side whenever the draft changes. */
  const [check, setCheck] = useState<PlanReview | null>(null);
  useEffect(() => {
    if (!draft) {
      setCheck(null);
      return;
    }
    let cancelled = false;
    review(draft)
      .then((reviewResult) => {
        if (!cancelled) setCheck(reviewResult);
      })
      .catch((error) => {
        if (!cancelled) {
          setCheck({ status: 'issues', issues: [`Could not review the draft: ${error instanceof Error ? error.message : String(error)}`], semesterIssues: {} });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [draft, review]);

  const selected = draft?.find((semester) => semester.id === selectedId) ?? null;
  const selectedIsEditable = selected !== null && selected.status !== 'in-progress';

  /* Hydrated rows for the detail panel: catalog titles + the per-course
     warning text from the review (grounded data only; meetings come from
     the courses detail endpoint, not fabricated here). */
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
          meeting: null,
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

  const selectedIndex = summaries.findIndex((semester) => semester.id === selectedId);

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
    // External system: the courses search endpoint (FC8). Sync state is
    // managed in handleSelectSemester; this effect only applies post-await.
    if (selectedId === null || !selectedIsEditable) return;
    let cancelled = false;
    const run = async () => {
      try {
        const suggestions = await fetchCandidates(selectedId, selected?.courseIds ?? [], searchTerm);
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
  }, [selectedId, selectedIsEditable, selected, searchTerm, fetchCandidates]);

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
    if (!draft || !selectedPlanId) return;
    setSaving(true);
    setSaveError(null);
    try {
      const detail = await savePlanDraft(selectedPlanId, draft);
      const refreshed = planDetailToActive(
        detail,
        plan ? {
          completionPercent: null,
          completedHours: plan.progress.completed,
          inProgressHours: plan.progress.inProgress,
          totalCreditsRequired: plan.progress.total,
        } : null,
      );
      setPlan(refreshed);
      setDraft(refreshed.semesters.map((s) => ({ ...s, courseIds: [...s.courseIds] })));
      const reviewed = await review(refreshed.semesters);
      setPlan((current) => (current ? { ...current, check: reviewed } : current));
      listPlanVersions(selectedPlanId).then(setVersions).catch(() => setVersions([]));
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  };

  /* FC5: revert to a previous version — the restored payload becomes a new
     version server-side, so history stays honest. */
  const [reverting, setReverting] = useState(false);
  const handleRevert = async (versionId: string) => {
    if (!selectedPlanId) return;
    setReverting(true);
    setSaveError(null);
    try {
      await revertPlan(selectedPlanId, versionId);
      await refreshPlanById(selectedPlanId);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : String(error));
    } finally {
      setReverting(false);
    }
  };

  /* FC6: make the selected plan the dashboard's plan (explicit step). */
  const handleMakeActive = async () => {
    if (!selectedPlanId) return;
    setActivating(true);
    setSaveError(null);
    try {
      await activatePlan(selectedPlanId);
      setActivePlanId(selectedPlanId);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : String(error));
    } finally {
      setActivating(false);
    }
  };

  /* Loading signal for the detail panel's add-course search. */
  const showCandidatesLoading = candidatesLoading || (selectedIsEditable && candidates === null && !candidatesError);

  const planOptions = plans.map((p) => ({
    value: p.plan_id,
    label: `${p.target_major ?? 'Plan'} — ${p.concentration ?? ''} (${p.created_at ? new Date(p.created_at).toISOString().slice(0, 10) : 'date unknown'})`,
  }));


  return (
    <AppShell active={active} onNavigate={onNavigate} chatOpen={chatOpen} onToggleChat={onToggleChat} chatSlot={chatSlot}>
      <main className="timeline-page">
        <header className="timeline-page-header">
          {plan ? (
            <p className="timeline-page-program">
              {plan.program.majorName.replace('BS in ', 'BS ')} · {plan.program.concentration}
            </p>
          ) : null}
          <h1 className="timeline-page-title">Timeline</h1>
        </header>
        {loadError ? (
          <p className="timeline-page-error" role="alert">
            Could not load the timeline: {loadError}
          </p>
        ) : (
          <>
            {plans.length > 0 ? (
              <div className="timeline-page-plan-selector">
                <Select
                  label="Plan"
                  value={selectedPlanId ?? ''}
                  options={planOptions}
                  onChange={handleSelectPlan}
                />
                {selectedPlanId !== activePlanId ? (
                  <Button onClick={handleMakeActive} disabled={activating}>
                    {activating ? 'Activating…' : 'Make active'}
                  </Button>
                ) : (
                  <span className="timeline-page-active-note" role="status">Active plan</span>
                )}
                {versions.length > 1 ? (
                  <Select
                    label="Revert to version"
                    value=""
                    placeholder="Choose version…"
                    options={versions.slice(0, -1).map((v) => ({
                      value: v.version_id,
                      label: `v${v.version_id}${v.label ? ` — ${v.label}` : ''}`,
                    }))}
                    onChange={(version) => {
                      if (version) void handleRevert(version);
                    }}
                    disabled={reverting}
                  />
                ) : null}
              </div>
            ) : null}
            {saveError ? (
              <p className="timeline-page-error" role="alert">
                {saveError}
              </p>
            ) : null}
            <SemesterTimeline
              semesters={summaries}
              selectedId={selectedId}
              onSelect={handleSelectSemester}
              loading={loading}
            />
            <SemesterDetail
              semester={selectedSemester}
              creditCap={18}
              check={check}
              onRemoveCourse={handleRemoveCourse}
              classStatuses={classStatuses}
              onStatusChange={changeStatus}
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              candidates={showCandidatesLoading ? null : selectedIsEditable ? candidates : null}
              onPickCourse={handlePickCourse}
              candidatesLoading={showCandidatesLoading}
              candidatesError={selectedIsEditable ? candidatesError : null}
              loading={loading}
              onPrev={selectedIndex > 0 ? () => handleSelectSemester(summaries[selectedIndex - 1].id) : undefined}
              onNext={
                selectedIndex >= 0 && selectedIndex < summaries.length - 1
                  ? () => handleSelectSemester(summaries[selectedIndex + 1].id)
                  : undefined
              }
            />
          </>
        )}
        {dirty ? <UnsavedChangesBar onDiscard={handleDiscard} onSave={handleSave} busy={saving} /> : null}
      </main>
    </AppShell>
  );
}