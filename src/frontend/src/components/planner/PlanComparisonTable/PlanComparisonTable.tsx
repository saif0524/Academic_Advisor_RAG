import Badge from '../../shared/Badge/Badge';
import type { ProgramComparison } from '../../../api/types';
import './PlanComparisonTable.css';

interface PlanComparisonTableProps {
  comparison: ProgramComparison | null;
  loading?: boolean;
  error?: string | null;
}

/**
 * Side-by-side plan comparison for a prospective program change (wireframe
 * 05; FC26). The comparison — hours that count, hours remaining, expected
 * graduation, and the trade-off notes — comes from the api layer (mock of
 * the deterministic compare + degree-audit path); this component renders it.
 */
export default function PlanComparisonTable({ comparison, loading = false, error = null }: PlanComparisonTableProps) {
  if (loading) {
    return (
      <section className="plan-comparison-table" aria-busy="true">
        <p className="plan-comparison-table-state">Building the comparison…</p>
      </section>
    );
  }
  if (error) {
    return (
      <section className="plan-comparison-table">
        <p className="plan-comparison-table-state plan-comparison-table-state--error">
          Could not build the comparison: {error}
        </p>
      </section>
    );
  }
  if (!comparison) {
    return (
      <section className="plan-comparison-table">
        <p className="plan-comparison-table-state">
          Pick a new major and concentration above to compare degree plans.
        </p>
      </section>
    );
  }
  const { current, proposed, notes } = comparison;
  const rows: Array<{ label: string; key: keyof typeof current }> = [
    { label: 'Degree', key: 'degree' },
    { label: 'Concentration', key: 'concentration' },
    { label: 'Hours that count', key: 'hoursThatCount' },
    { label: 'Hours remaining', key: 'hoursRemaining' },
    { label: 'Expected graduation', key: 'graduation' },
  ];
  return (
    <section className="plan-comparison-table" aria-label="Plan comparison">
      <header className="plan-comparison-table-header">
        <h3 className="plan-comparison-table-title">Plan comparison</h3>
        <Badge variant="warning">Estimates — confirm before you commit</Badge>
      </header>
      <table className="plan-comparison-table-grid">
        <thead>
          <tr>
            <th scope="col">
              <span className="plan-comparison-table-sr">Requirement</span>
            </th>
            <th scope="col">Current</th>
            <th scope="col">New</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <th scope="row">{row.label}</th>
              <td className={current[row.key] === proposed[row.key] ? undefined : 'plan-comparison-table-diff'}>
                {current[row.key]}
              </td>
              <td className={current[row.key] === proposed[row.key] ? undefined : 'plan-comparison-table-diff'}>
                {proposed[row.key]}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {notes && notes.length > 0 ? (
        <ul className="plan-comparison-table-notes">
          {notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}