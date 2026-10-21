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
import { compareProgramChange, confirmProgramChange } from '../api/plans';
import { getPlanningPreferences, getStudentProfile, savePlanningPreferences } from '../api/students';
import type {
  PlanningPreferences as PlanningPreferencesData,
  ProgramComparison,
  StudentProfile,
} from '../api/types';
import './AccountPage.css';

export interface AccountDependencies {
  profile: StudentProfile | null;
  preferences: PlanningPreferencesData | null;
}

interface AccountPageProps {
  active?: PageId;
  onNavigate?: (page: PageId) => void;
  chatOpen?: boolean;
  onToggleChat?: () => void;
  chatSlot?: ReactNode;
  /** DI seam (stories inject instant fixtures); defaults to the api mock. */
  loadDependencies?: () => Promise<AccountDependencies>;
  /** DI seams for the change-major and preference actions. */
  compareFn?: (newMajor: string, newConcentration: string) => Promise<ProgramComparison | null>;
  confirmFn?: () => Promise<{ applied: boolean }>;
  savePreferencesFn?: (prefs: PlanningPreferencesData) => Promise<{ saved: boolean; savedAt: string }>;
}

async function defaultLoadDependencies(): Promise<AccountDependencies> {
  const [profile, preferences] = await Promise.all([getStudentProfile(), getPlanningPreferences()]);
  return { profile, preferences };
}

const DEFAULT_COMPARE = (major: string, concentration: string): Promise<ProgramComparison | null> =>
  compareProgramChange({ majorName: major, concentration });

/**
 * Account page (wireframe 05): the pre-authenticated profile (FC36), the
 * change-major flow — pick a new major/concentration (FC1) → side-by-side
 * comparison (FC26, from the api's deterministic compare path) → explicit
 * confirmation dialog before anything applies (FC23; Cancel never commits) —
 * and the planning-preferences form (FC25/FC32). The right-hand chat covers
 * multi-turn guidance (FC28) via the AdvisorApp drawer.
 */
export default function AccountPage({
  active = 'account',
  onNavigate,
  chatOpen = false,
  onToggleChat,
  chatSlot = null,
  loadDependencies,
  compareFn = DEFAULT_COMPARE,
  confirmFn = confirmProgramChange,
  savePreferencesFn = savePlanningPreferences,
}: AccountPageProps) {
  const loadData = loadDependencies ?? defaultLoadDependencies;
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [preferences, setPreferences] = useState<PlanningPreferencesData | null>(null);
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

  /* FC26 comparison runs whenever a complete new pair is picked (mock of the
     deterministic compare path); invalid pairs resolve null → "pick below". */
  useEffect(() => {
    if (!newMajor || !newConcentration || !comparing) return;
    let cancelled = false;
    const run = async () => {
      try {
        const result = await compareFn(newMajor, newConcentration);
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
  }, [newMajor, newConcentration, comparing, compareFn]);

  const handleCancelChange = () => {
    setNewMajor('');
    setNewConcentration('');
    setComparison(null);
    setCompareError(null);
    setComparing(false);
    setApplied(false);
  };

  /* FC23 — the deterministic side only applies after this confirm path. */
  const handleConfirmChange = async () => {
    setConfirming(true);
    try {
      const result = await confirmFn();
      if (result.applied) setApplied(true);
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

  return (
    <AppShell active={active} onNavigate={onNavigate} chatOpen={chatOpen} onToggleChat={onToggleChat} chatSlot={chatSlot}>
      <main className="account-page">
        <header className="account-page-header">
          <h1 className="account-page-title">Account</h1>
          {profile ? (
            <div className="account-page-identity">
              <p className="account-page-name">{profile.name}</p>
              <p className="account-page-meta">
                Student ID {profile.studentIdLabel} · Catalog year {profile.catalogYear} · {profile.standing}
              </p>
              <p className="account-page-major">
                Major and concentration: <strong>{profile.major} — {profile.concentration}</strong>
                {applied ? (
                  <Badge variant="success" dot>Program change applied (demo)</Badge>
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
                  options={['BS in Computer Science', 'BS in Software Engineering']}
                  placeholder="Select a major"
                />
                <Select
                  label="Concentration"
                  value={newConcentration}
                  onChange={handleSetNewConcentration}
                  options={['Cybersecurity', 'Artificial Intelligence']}
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
                Hours that count: {comparison.current.hoursThatCount} → {comparison.proposed.hoursThatCount};
                expected graduation moves to {comparison.proposed.graduation}.
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