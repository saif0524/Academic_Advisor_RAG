import { useEffect, useState } from 'react';
import MajorSpecSelector from '../components/planner/MajorSpecSelector/MajorSpecSelector.jsx';
import PlanRoadmap from '../components/planner/PlanRoadmap/PlanRoadmap.jsx';
import Button from '../components/shared/Button/Button.jsx';
import {
  generatePlan as generatePlanViaApi,
  getCourseCatalog,
  getPlanOptions,
} from '../api/plans.js';
import './PlanGenerator.css';

/**
 * Full-page "generate a degree plan" experience (FC1, FC2, FC25) rendered as
 * a viewport-filling overlay over the Dashboard, with an explicit
 * back-to-Dashboard action (no router — single-page state).
 *
 * All data flows through the api service layer (mocked in api/plans.js until
 * the FastAPI plan endpoints are wired) — components never fetch inline.
 * Generation is a preview: it does not modify the student's record, so no
 * FC23 confirmation gate applies here.
 *
 * Props:
 * - onNavigateBack: () => void — closes the overlay, returning to Dashboard.
 * - loadDependencies?: async () => Promise<{ options, catalog }> — DI seam
 *   (stories inject instant fixtures); defaults to the api service.
 * - generatePlanFn?: async (request) => Promise<PlanDetail | null> — DI seam
 *   (stories inject fixtures); defaults to the api service. Null result
 *   means the requested major/concentration has no plan.
 */
const MOCK_PREVIEW_NOTE =
  'Mock preview: CSE coursework only — the full plan adds general education, math, and physics to the degree total.';

async function defaultLoadDependencies() {
  const [options, catalog] = await Promise.all([getPlanOptions(), getCourseCatalog()]);
  return { options, catalog };
}

export default function PlanGenerator({
  onNavigateBack,
  loadDependencies,
  generatePlanFn,
}) {
  const loadData = loadDependencies ?? defaultLoadDependencies;
  const generate = generatePlanFn ?? generatePlanViaApi;

  const [data, setData] = useState(null); // { options, catalog }
  const [loadError, setLoadError] = useState(false);
  const [major, setMajor] = useState('');
  const [concentration, setConcentration] = useState('');
  const [includeSummer, setIncludeSummer] = useState(false);
  const [plan, setPlan] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState('');

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
  const handleSelectionChange = (next) => {
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
    try {
      const request = {
        majorName: major,
        concentration,
        includeSummer, // optional summer sessions upon request (FC25)
      };
      const result = await generate(request);
      if (result === null) {
        setGenerateError(
          `No plan could be generated for ${major} with the ${concentration} specialization.`,
        );
        return;
      }
      setPlan(result);
    } catch {
      setGenerateError('Plan generation failed. Select Generate plan to try again.');
    } finally {
      setIsGenerating(false);
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
        {isLoading && (
          <p className="plan-generator-status" role="status">
            Loading majors and the course catalog…
          </p>
        )}
        {loadError && (
          <div className="plan-generator-error" role="alert">
            <p>We couldn't load majors or the course catalog.</p>
            <Button onClick={() => setReloadToken((token) => token + 1)}>Try again</Button>
          </div>
        )}
        {data && (
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
            {generateError && (
              <p className="plan-generator-alert" role="alert">
                {generateError}
              </p>
            )}
            {isGenerating && (
              <p className="plan-generator-status" role="status">
                Generating your plan…
              </p>
            )}
            {!plan && !isGenerating && (
              <p className="plan-generator-hint" role="status">
                Choose your major and specialization, then select Generate plan.
              </p>
            )}
            {plan && (
              <PlanRoadmap plan={plan} catalog={data.catalog} note={MOCK_PREVIEW_NOTE} />
            )}
          </>
        )}
      </main>
    </div>
  );
}