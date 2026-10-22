import type { ReactNode } from 'react';
import SemesterCard from '../SemesterCard/SemesterCard';
import type { CourseCatalog, PlanDetail } from '../../../api/types';
import './PlanRoadmap.css';

interface PlanRoadmapProps {
  plan: PlanDetail | null;
  catalog?: CourseCatalog;
  /** Caveat line rendered in the footer (preview note). */
  note?: string | null;
  /** Action buttons rendered beside the summary at the top. */
  actions?: ReactNode;
  /** Per-semester Edit action (FC3) — the page routes it to the
      engine-validated timeline editor. Omit to render read-only cards. */
  onEditSemester?: (semester: { term: string; year: number }) => void;
}

/**
 * Semester-by-semester roadmap of a generated degree plan (FC25). Renders
 * the plan summary header (major/concentration, summer flag, generated
 * date) and a single column of collapsible SemesterCards (one per
 * semester) with an optional per-semester Edit action (FC3).
 */
export default function PlanRoadmap({ plan, catalog = {}, note = null, actions, onEditSemester }: PlanRoadmapProps) {
  const semesters = plan?.semesters ?? [];
  const totalCredits = semesters.reduce((sum, semester) => sum + (semester.credits ?? 0), 0);
  const generatedDate = plan?.created_at
    ? new Date(plan.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
    : null;
  return (
    <section className="plan-roadmap" aria-label="Generated degree plan">
      <header className="plan-roadmap-header">
        <div className="plan-roadmap-summary">
          <h2 className="plan-roadmap-title">
            {plan?.target_major ?? 'Degree plan'}
            {plan?.concentration ? ` — ${plan.concentration}` : ''}
          </h2>
          <p className="plan-roadmap-meta">
            {semesters.length} semester{semesters.length === 1 ? '' : 's'}
            {` · ${totalCredits} planned credits`}
            {plan?.includes_summer ? ' · includes summer sessions' : ''}
            {generatedDate ? ` · generated ${generatedDate}` : ''}
          </p>
          {note ? <p className="plan-roadmap-note">{note}</p> : null}
        </div>
        {actions ? <div className="plan-roadmap-actions">{actions}</div> : null}
      </header>
      {semesters.length === 0 ? (
        <p className="plan-roadmap-empty">This plan has no semesters yet.</p>
      ) : (
        <div className="plan-roadmap-list">
          {semesters.map((semester) => (
            <SemesterCard
              key={`${semester.term}-${semester.year}`}
              semester={semester}
              catalog={catalog}
              collapsible
              onEdit={onEditSemester ? () => onEditSemester(semester) : undefined}
            />
          ))}
        </div>
      )}
    </section>
  );
}