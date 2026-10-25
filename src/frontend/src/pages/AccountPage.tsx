import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import AppShell from '../components/shared/AppShell/AppShell';
import type { PageId } from '../components/shared/AppSidebar/AppSidebar';
import Badge from '../components/shared/Badge/Badge';
import Button from '../components/shared/Button/Button';
import ConfirmDialog from '../components/shared/ConfirmDialog/ConfirmDialog';
import Select from '../components/shared/Select/Select';
import PlanComparisonTable from '../components/planner/PlanComparisonTable/PlanComparisonTable';
import PlanningPreferences from '../components/planner/PlanningPreferences/PlanningPreferences';
import {
  compareProgramChange,
  confirmProgramChange,
  getPlanOptions,
  getActivePlan,
  listPlans,
} from '../api/plans';
import { ApiError } from '../api/client';
import { getPlanningPreferences, getStudentProfile, savePlanningPreferences } from '../api/students';
import type {
  PlanningPreferences as PlanningPreferencesData,
  PlanOption,
  ProgramComparison,
  StudentProfile,
} from '../api/types';
import './AccountPage.css';

export interface AccountDependencies {
  profile: StudentProfile | null;
  preferences: PlanningPreferencesData | null;
  /** Generate-form inputs (FC1) straight from the degrees table. */
  options: { majors: PlanOption[] };
  /** Anchor for the FC26 comparison: the active plan, else the newest. */
  comparePlanId: string | null;
}

interface AccountPageProps {
  active?: PageId;
  onNavigate?: (page: PageId) => void;
  chatOpen?: boolean;
  onToggleChat?: () => void;
  chatSlot?: ReactNode;
  /** DI seam (stories inject instant fixtures); defaults to the live api. */
  loadDependencies?: () => Promise<AccountDependencies>;
  /** DI seam for the change-major comparison (FC26). */
  compareFn?: (newMajor: string, newConcentration: string) => Promise<ProgramComparison | null>;
  /** DI seam for the confirmed change: applies FC1/FC7 and auto-generates a
      fresh plan for the new degree, which becomes the active plan (FC6:
      any changed plan is active by default). The ConfirmDialog runs first. */
  confirmFn?: (newMajor: string, newConcentration: string) => Promise<{ applied: boolean; planId?: string | null }>;
  /** Called after a confirmed change with the freshly generated plan id. */
  onProgramChanged?: (planId: string | null) => void;
  savePreferencesFn?: (prefs: PlanningPreferencesData) => Promise<{ saved: boolean; savedAt: string }>;
}

/** Compare anchor (FC26): the active plan when one exists, else the most
    recently generated plan; null when the student has no plan on file. */
async function pickComparePlanId(): Promise<string | null> {
  try {
    const active = await getActivePlan();
    if (active) return active.plan_id;
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) throw error;
  }
  const plans = await listPlans();
  return plans.length ? plans[plans.length - 1].plan_id : null;
}

async function defaultLoadDependencies(): Promise<AccountDependencies> {
  const [profile, preferences, options, comparePlanId] = await Promise.all([
    getStudentProfile(),
    getPlanningPreferences(),
    getPlanOptions(),
    pickComparePlanId(),
  ]);
  return { profile, preferences, options, comparePlanId };
}

const DEFAULT_COMPARE = (comparePlanId: string | null) =>
  (newMajor: string, newConcentration: string): Promise<ProgramComparison | null> =>
    comparePlanId
      ? compareProgramChange({ existingPlanId: comparePlanId, majorName: newMajor, concentration: newConcentration })
      : Promise.resolve(null);

/**
 * Account page (wireframe 05): the pre-authenticated profile (FC36 — fields
 * the server doesn't track render as honest unknowns), the change-major flow
 * — pick a new major/concentration from the real degrees (FC1) → side-by-side
 * comparison against the plan on file (FC26, deterministic engine) → explicit
 * confirmation dialog before anything applies: the confirmed change updates
 * the major/concentration (FC1/FC7) and auto-generates a fresh (inactive)
 * plan for the new degree. Cancel never commits. The planning-preferences
 * form persists FC25/FC32 inputs. The right-hand chat covers multi-turn
 * guidance (FC28) via the AdvisorApp drawer.
 */
export default function AccountPage({
  active = 'account',
  onNavigate,
  chatOpen = false,
  onToggleChat,
  chatSlot = null,
  loadDependencies,
  compareFn,
  confirmFn = confirmProgramChange,
  onProgramChanged,
  savePreferencesFn = savePlanningPreferences,
}: AccountPageProps) {
  const loadData = loadDependencies ?? defaultLoadDependencies;
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [preferences, setPreferences] = useState<PlanningPreferencesData | null>(null);
  const [options, setOptions] = useState<{ majors: PlanOption[] }>({ majors: [] });
  const [comparePlanId, setComparePlanId] = useState<string | null>(null);
  const [prefsSaving, setPrefsSaving] = useState(false);
  const [prefsError, setPrefsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [newMajor, setNewMajor] = useState('');
  const [newConcentration, setNewConcentration] = useState('');
  const [comparison, setComparison] = useState<ProgramComparison | null>(null);
  const [comparing, setComparing] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [applied, setApplied] = useState(false);

  useEffect(() => {
    // External system: the api seam (sync state persists for the component
    // lifetime; seam changes remount the page, so no pre-await setState).
    let cancelled = false;
    const run = async () => {
      try {
        const deps = await loadData();
        if (!cancelled) {
          setProfile(deps.profile);
          setPreferences(deps.preferences);
          setOptions(deps.options);
          setComparePlanId(deps.comparePlanId);
        }
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

  /* picking handlers reset the comparison state synchronously (event
     writes); the effect only applies post-await results. */
  const handleSetNewMajor = (value: string) => {
    setNewMajor(value);
    setComparison(null);
    setCompareError(null);
    setApplied(false);
    setComparing(Boolean(value));
  };
  const handleSetNewConcentration = (value: string) => {
    setNewConcentration(value);
    setComparison(null);
    setCompareError(null);
    setApplied(false);
    setComparing(Boolean(value && newMajor));
  };

  /* FC26 comparison runs whenever a complete new pair is picked; invalid
     pairs resolve null → "pick below". With no plan on file the compare is
     refused honestly — nothing is invented. */
  useEffect(() => {
    if (!newMajor || !newConcentration || !comparing) return;
    let cancelled = false;
    const runCompare = compareFn ?? DEFAULT_COMPARE(comparePlanId);
    const run = async () => {
      try {
        if (!compareFn && !comparePlanId) {
          setCompareError('No degree plan on file to compare — generate one from the dashboard first.');
          return;
        }
        const result = await runCompare(newMajor, newConcentration);
        if (!cancelled) setComparison(result);
      } catch (error) {
        if (!cancelled) setCompareError(error instanceof Error ? error.message : String(error));
      } finally {
        if (!cancelled) setComparing(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [newMajor, newConcentration, comparing, compareFn, comparePlanId]);

  const handleCancelChange = () => {
    setNewMajor('');
    setNewConcentration('');
    setComparison(null);
    setCompareError(null);
    setComparing(false);
    setApplied(false);
  };

  /* FC23-style gate — the ConfirmDialog ran before this fires: applying the
     change updates the profile AND generates the new active plan (FC6). */
  const handleConfirmChange = async () => {
    setConfirming(true);
    try {
      const result = await confirmFn(newMajor, newConcentration);
      if (result.applied) {
        setApplied(true);
        try {
          setProfile(await getStudentProfile());
        } catch {
          /* profile refresh is best-effort */
        }
        onProgramChanged?.(result.planId ?? null);
      }
    } catch (error) {
      setApplied(false);
      setCompareError(error instanceof Error ? error.message : String(error));
    } finally {
      setConfirming(false);
      setConfirmOpen(false);
    }
  };

  const handleSavePreferences = async (prefs: PlanningPreferencesData) => {
    setPrefsSaving(true);
    setPrefsError(null);
    try {
      await savePreferencesFn(prefs);
      setPreferences(prefs);
    } catch (error) {
      setPrefsError(error instanceof Error ? error.message : String(error));
    } finally {
      setPrefsSaving(false);
    }
  };

  const selectedOption = options.majors.find((option) => option.name === newMajor);

  return (
    <AppShell active={active} onNavigate={onNavigate} chatOpen={chatOpen} onToggleChat={onToggleChat} chatSlot={chatSlot}>
      <main className="account-page">
        <header className="account-page-header">
          <h1 className="account-page-title">Account</h1>
          {profile ? (
            <div className="account-page-identity">
              <p className="account-page-name">{profile.name ?? 'Not on record'}</p>
              <p className="account-page-meta">
                Student ID {profile.studentIdLabel} · Catalog year {profile.catalogYear} · Standing {profile.standing}
              </p>
              <p className="account-page-major">
                Major and concentration:{' '}
                <strong>
                  {profile.major ?? 'Not set'} — {profile.concentration ?? 'Not set'}
                </strong>
                {applied ? (
                  <Badge variant="success" dot>Program change applied — new active plan generated</Badge>
                ) : null}
              </p>
            </div>
          ) : (
            <p className="account-page-state">{loading ? 'Loading your profile…' : `Could not load your profile: ${loadError ?? 'not found'}`}</p>
          )}
        </header>

        {profile ? (
          <>
            <section className="account-page-change" aria-label="Change program">
              <h2 className="account-page-section-title">Program change</h2>
              <p className="account-page-hint">
                Pick a new major and concentration to compare the current and new degree plans. The
                advisor can walk through the pros and cons before you commit.
              </p>
              <div className="account-page-change-selects">
                <Select
                  label="New major"
                  value={newMajor}
                  onChange={handleSetNewMajor}
                  options={options.majors.map((option) => option.name)}
                  placeholder="Select a major"
                />
                <Select
                  label="Concentration"
                  value={newConcentration}
                  onChange={handleSetNewConcentration}
                  options={selectedOption?.concentrations ?? []}
                  placeholder="Select a concentration"
                  disabled={!newMajor}
                />
                <Button variant="secondary" onClick={handleCancelChange} disabled={!newMajor && !newConcentration}>
                  Cancel
                </Button>
              </div>
              <PlanComparisonTable comparison={comparison} loading={comparing} error={compareError} />
              {comparison ? (
                <div className="account-page-change-actions">
                  <Button onClick={() => setConfirmOpen(true)}>Confirm program change…</Button>
                </div>
              ) : null}
            </section>

            <PlanningPreferences
              preferences={preferences}
              onSave={handleSavePreferences}
              saving={prefsSaving}
              saveError={prefsError}
            />
          </>
        ) : null}

        <ConfirmDialog
          open={confirmOpen}
          title="Program change"
          body={
            comparison ? (
              <>
                Switch to <strong>{comparison.proposed.degree} — {comparison.proposed.concentration}</strong>?{' '}
                {comparison.current.hoursThatCount}; {comparison.proposed.hoursRemaining}.
                A fresh plan for the new degree will be generated and made your active plan.
              </>
            ) : (
              'Apply the selected program change?'
            )
          }
          confirmLabel="Confirm program change"
          cancelLabel="Cancel"
          busy={confirming}
          onConfirm={handleConfirmChange}
          onCancel={() => setConfirmOpen(false)}
        />
      </main>
    </AppShell>
  );
}