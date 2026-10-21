import { useEffect, useState } from 'react';
import MajorSpecSelector from '../components/planner/MajorSpecSelector/MajorSpecSelector';
import PlanRoadmap from '../components/planner/PlanRoadmap/PlanRoadmap';
import Button from '../components/shared/Button/Button';
import {
  activatePlan,
  generatePlan as generatePlanViaApi,
  getCourseCatalog,
  getPlanOptions,
} from '../api/plans';
import { ApiError } from '../api/client';
import type { CourseCatalog, PlanDetail, PlanOption } from '../api/types';
import './PlanGenerator.css';

interface LoadDependencies {
  options: { majors: PlanOption[] };
  catalog: CourseCatalog;
}

interface PlanGeneratorProps {
  /** Closes the overlay, returning to the home page. */
  onNavigateBack?: () => void;
  /** Opens the timeline to keep editing the generated plan. */
  onOpenPlan?: () => void;
  /** DI seam (stories inject instant fixtures); defaults to the live api. */
  loadDependencies?: () => Promise<LoadDependencies>;
  /** DI seam (stories inject fixtures). Null result means the requested
      major/concentration has no plan — the page renders an explicit error. */
  generatePlanFn?: (request: { majorName: string; concentration: string; includeSummer?: boolean }) => Promise<PlanDetail | null>;
}

async function defaultLoadDependencies(): Promise<LoadDependencies> {
  const [options, catalog] = await Promise.all([getPlanOptions(), getCourseCatalog()]);
  return { options, catalog };
}

/** Live generate: 404 (unknown major/concentration pair) resolves null so
    the page renders its explicit not-found error (grounded, no fake plan). */
async function defaultGenerate(request: {
  majorName: string;
  concentration: string;
  includeSummer?: boolean;
}): Promise<PlanDetail | null> {
  try {
    return await generatePlanViaApi(request);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

/**
 * Full-page "generate a degree plan" experience (FC1, FC2, FC25) rendered as
 * a viewport-filling overlay, with an explicit back action (no router —
 * single-page state).
 *
 * Generation goes to POST /plans/generate — the deterministic engine builds
 * the roadmap and grounded caveats ride along as `plan.notes`. Generation is
 * only a preview (no FC23 gate); the generated plan is INACTIVE — make it
 * active from here or keep editing in the timeline (generate → edit →
 * make active).
 */
export default function PlanGenerator({
  onNavigateBack,
  onOpenPlan,
  loadDependencies,
  generatePlanFn,
}: PlanGeneratorProps) {
  const loadData = loadDependencies ?? defaultLoadDependencies;
  const generate = generatePlanFn ?? defaultGenerate;

  const [data, setData] = useState<LoadDependencies | null>(null); // { options, catalog }
  const [loadError, setLoadError] = useState(false);
  const [major, setMajor] = useState('');
  const [concentration, setConcentration] = useState('');
  const [includeSummer, setIncludeSummer] = useState(false);
  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState('');
  const [activating, setActivating] = useState(false);
  const [activateError, setActivateError] = useState('');
  const [activated, setActivated] = useState(false);

  const [reloadToken, setReloadToken] = useState(0);
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const result = await loadData();
        if (!cancelled) setData(result);
      } catch {
        if (!cancelled) setLoadError(true);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [loadData, reloadToken]);

  /* FC1: selecting a new major clears the concentration so the student
     re-specifies exactly one specialization for the new major. */
  const handleSelectionChange = (next: { major?: string; concentration?: string; includeSummer?: boolean }) => {
    if (next.major !== undefined && next.major !== major) {
      setMajor(next.major);
      setConcentration('');
      return;
    }
    if (next.concentration !== undefined) setConcentration(next.concentration);
    if (next.includeSummer !== undefined) setIncludeSummer(next.includeSummer);
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerateError('');
    setActivated(false);
    setActivateError('');
    try {
      const request = {
        majorName: major,
        concentration,
        includeSummer, // optional summer sessions upon request (FC25)
      };
      const result = await generate(request);
      if (result === null) {
        setGenerateError(`No plan could be generated for ${major} with the ${concentration} specialization.`);
        return;
      }
      setPlan(result);
    } catch (error) {
      setGenerateError(
        error instanceof Error ? error.message : 'Plan generation failed. Select Generate plan to try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  /* The explicit activation step (FC6): the plan becomes the dashboard's
     plan only on confirmation here — generate → edit → make active. */
  const handleMakeActive = async () => {
    if (!plan) return;
    setActivating(true);
    setActivateError('');
    try {
      await activatePlan(plan.plan_id);
      setActivated(true);
    } catch (error) {
      setActivateError(error instanceof Error ? error.message : String(error));
    } finally {
      setActivating(false);
    }
  };

  const canGenerate = Boolean(major && concentration);
  const isLoading = !data && !loadError;

  return (
    <div className="plan-generator">
      <header className="plan-generator-header">
        <Button variant="secondary" onClick={onNavigateBack}>
          ← Back to Dashboard
        </Button>
        <div className="plan-generator-heading">
          <h1 className="plan-generator-title">Generate Degree Plan</h1>
          <p className="plan-generator-subtitle">
            Build a semester-by-semester roadmap for your major and specialization.
          </p>
        </div>
      </header>
      <main className="plan-generator-main">
        {isLoading ? (
          <p className="plan-generator-status" role="status">
            Loading majors and the course catalog…
          </p>
        ) : null}
        {loadError ? (
          <div className="plan-generator-error" role="alert">
            <p>We couldn&apos;t load majors or the course catalog.</p>
            <Button onClick={() => setReloadToken((token) => token + 1)}>Try again</Button>
          </div>
        ) : null}
        {data ? (
          <>
            <MajorSpecSelector
              options={data.options}
              major={major}
              concentration={concentration}
              includeSummer={includeSummer}
              onSelectionChange={handleSelectionChange}
              onGenerate={handleGenerate}
              canGenerate={canGenerate}
              disabled={isGenerating}
            />
            {generateError ? (
              <p className="plan-generator-alert" role="alert">
                {generateError}
              </p>
            ) : null}
            {isGenerating ? (
              <p className="plan-generator-status" role="status">
                Generating your plan…
              </p>
            ) : null}
            {!plan && !isGenerating ? (
              <p className="plan-generator-hint" role="status">
                Choose your major and specialization, then select Generate plan.
              </p>
            ) : null}
            {plan ? (
              <>
                <PlanRoadmap
                  plan={plan}
                  catalog={data.catalog}
                  note={plan.notes?.length ? plan.notes.join(' · ') : undefined}
                />
                {activateError ? (
                  <p className="plan-generator-alert" role="alert">{activateError}</p>
                ) : null}
                <div className="plan-generator-actions">
                  <Button onClick={handleMakeActive} disabled={activating}>
                    {activating ? 'Activating…' : activated ? 'Active ✓' : 'Make active'}
                  </Button>
                  {onOpenPlan ? (
                    <Button variant="secondary" onClick={onOpenPlan}>
                      Keep editing in timeline →
                    </Button>
                  ) : null}
                </div>
              </>
            ) : null}
          </>
        ) : null}
      </main>
    </div>
  );
}