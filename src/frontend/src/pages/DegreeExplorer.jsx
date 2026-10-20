import './DegreeExplorer.css';

/**
 * Degree exploration/audit surface (FC15–FC19) — composition root for the
 * degrees/ components. Scaffold placeholder: until the requirements API is
 * wired (data lives in SQLite/Chroma, FC33), an explicit empty state renders
 * — no invented degree data (grounded-UI rule).
 * Props: none.
 */
export default function DegreeExplorer() {
  return (
    <main className="degree-explorer">
      <h1 className="degree-explorer-title">Degree Explorer</h1>
      <p className="degree-explorer-empty">
        No degree requirements loaded yet (FC15–FC19, FC33).
      </p>
    </main>
  );
}