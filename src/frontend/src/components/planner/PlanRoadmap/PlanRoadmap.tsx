import SemesterCard from '../SemesterCard/SemesterCard';
import type { CourseCatalog, PlanDetail } from '../../../api/types';
import './PlanRoadmap.css';

interface PlanRoadmapProps {
  plan: PlanDetail | null;
  catalog?: CourseCatalog;
  /** Caveat line rendered in the footer (mock preview note). */
  note?: string | null;
}

/**
 * Semester-by-semester roadmap of a generated degree plan (FC25). Renders
 * the plan summary header (major/concentration, summer flag, generated
 * date), one SemesterCard per semester, and the planned-credit total.
 */
export default function PlanRoadmap({ plan, catalog = {}, note = null }: PlanRoadmapProps) {
  const semesters = plan?.semesters ?? [];
  const totalCredits = semesters.reduce((sum, semester) => sum + (semester.credits ?? 0), 0);
  const generatedDate = plan?.created_at
    ? new Date(plan.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
    : null;
  return (
    <section className="plan-roadmap" aria-label="Generated degree plan">
      <header className="plan-roadmap-header">
        <h2 className="plan-roadmap-title">
          {plan?.target_major ?? 'Degree plan'}
          {plan?.concentration ? ` — ${plan.concentration}` : ''}
        </h2>
        <p className="plan-roadmap-meta">
          {semesters.length} semester{semesters.length === 1 ? '' : 's'}
          {plan?.includes_summer ? ' · includes summer sessions' : ''}
          {generatedDate ? ` · generated ${generatedDate}` : ''}
        </p>
      </header>
      {semesters.length === 0 ? (
        <p className="plan-roadmap-empty">This plan has no semesters yet.</p>
      ) : (
        <div className="plan-roadmap-grid">
          {semesters.map((semester) => (
            <SemesterCard
              key={`${semester.term}-${semester.year}`}
              semester={semester}
              catalog={catalog}
            />
          ))}
        </div>
      )}
      <footer className="plan-roadmap-footer">
        <p className="plan-roadmap-total">Planned roadmap credits: {totalCredits}</p>
        {note ? <p className="plan-roadmap-note">{note}</p> : null}
      </footer>
    </section>
  );
}