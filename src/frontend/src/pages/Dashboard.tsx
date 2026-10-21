import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import AppShell from '../components/shared/AppShell/AppShell';
import type { PageId } from '../components/shared/AppSidebar/AppSidebar';
import Button from '../components/shared/Button/Button';
import PlanProgressHeader from '../components/planner/PlanProgressHeader/PlanProgressHeader';
import CurrentSemesterPanel from '../components/planner/CurrentSemesterPanel/CurrentSemesterPanel';
import SemesterCard from '../components/planner/SemesterCard/SemesterCard';
import type { CurrentSemesterCourse } from '../components/planner/CurrentSemesterPanel/CurrentSemesterPanel';
import PlanGenerator from './PlanGenerator';
import { getActivePlan, getCourseCatalog } from '../api/plans';
import type { ActivePlanData, CourseCatalog } from '../api/types';
import './Dashboard.css';

export interface DashboardDependencies {
  plan: ActivePlanData | null;
  catalog: CourseCatalog;
}

interface DashboardProps {
  /** Shell wiring (AdvisorApp owns these; stories use the defaults). */
  active?: PageId;
  onNavigate?: (page: PageId) => void;
  chatOpen?: boolean;
  onToggleChat?: () => void;
  chatSlot?: ReactNode;
  /** DI seam (stories inject instant fixtures); defaults to the api mock. */
  loadDependencies?: () => Promise<DashboardDependencies>;
  /** Lets the Storybook story show the planner overlay without interaction. */
  initialPlannerOpen?: boolean;
}

const EMPTY_CATALOG: CourseCatalog = {};

async function defaultLoadDependencies(): Promise<DashboardDependencies> {
  const [plan, catalog] = await Promise.all([getActivePlan(), getCourseCatalog()]);
  return { plan, catalog };
}

/**
 * Home page (wireframes 01/06): the active degree plan summary, this
 * semester's classes (FC14/FC21 display), and the "My semesters" roadmap
 * grid (FC25) with Edit actions into the Timeline (FC3). The FC2 planner
 * overlay opens from the section header. All data flows through the api
 * mock seams; statuses/verdicts are display fields, never computed here.
 */
export default function Dashboard({
  active = 'home',
  onNavigate,
  chatOpen = false,
  onToggleChat,
  chatSlot = null,
  loadDependencies,
  initialPlannerOpen = false,
}: DashboardProps) {
  const loadData = loadDependencies ?? defaultLoadDependencies;
  const [data, setData] = useState<DashboardDependencies | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [plannerOpen, setPlannerOpen] = useState(initialPlannerOpen);

  useEffect(() => {
    // External system: the api seam. Sync state lives for the component's
    // lifetime (seam changes remount via key), so no pre-await setState here.
    let cancelled = false;
    const run = async () => {
      try {
        const result = await loadData();
        if (!cancelled) setData(result);
      } catch (loadError) {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : String(loadError));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [loadData]);

  const plan = data?.plan ?? null;
  // Stable identity so useMemos below don't recompute every render.
  const catalog = data?.catalog ?? EMPTY_CATALOG;

  const currentSemesterCourses: CurrentSemesterCourse[] | null = useMemo(() => {
    const inProgress = plan?.semesters.find((semester) => semester.status === 'in-progress');
    if (!inProgress) return null;
    return inProgress.courseIds.map((id) => ({
      id,
      title: catalog[id]?.title ?? null,
      creditHours: catalog[id]?.creditHours ?? null,
      status: 'in-progress' as const,
    }));
  }, [plan, catalog]);

  const currentTerm = useMemo(() => {
    const inProgress = plan?.semesters.find((semester) => semester.status === 'in-progress');
    return inProgress ? `${inProgress.term} ${inProgress.year}` : (plan?.currentTerm ?? '');
  }, [plan]);

  return (
    <AppShell active={active} onNavigate={onNavigate} chatOpen={chatOpen} onToggleChat={onToggleChat} chatSlot={chatSlot}>
      <main className="dashboard">
        <PlanProgressHeader plan={plan} loading={loading} error={error} />
        <CurrentSemesterPanel term={currentTerm} courses={currentSemesterCourses} loading={loading} error={error} />
        <section className="dashboard-semesters" aria-label="My semesters">
          <header className="dashboard-semesters-header">
            <h2 className="dashboard-semesters-title">My semesters</h2>
            <Button variant="secondary" onClick={() => setPlannerOpen(true)}>
              New plan
            </Button>
          </header>
          {plan?.semesters.length ? (
            <div className="dashboard-semesters-grid">
              {plan.semesters.map((semester) => (
                <SemesterCard
                  key={semester.id}
                  semester={{
                    term: semester.term,
                    year: semester.year,
                    courses: semester.courseIds,
                    credits: semester.credits,
                  }}
                  catalog={catalog}
                  status={semester.status}
                  onEdit={() => onNavigate?.('timeline')}
                  emptyNote={semester.status === 'optional' ? 'Optional — not in your plan' : undefined}
                />
              ))}
            </div>
          ) : (
            <p className="dashboard-semesters-empty">
              {loading ? 'Loading your semesters…' : 'No semesters in your active plan yet.'}
            </p>
          )}
        </section>
        {plannerOpen && <PlanGenerator onNavigateBack={() => setPlannerOpen(false)} />}
      </main>
    </AppShell>
  );
}