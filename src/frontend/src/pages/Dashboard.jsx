import './Dashboard.css';

/**
 * Advisor landing page — a composition root (may import from any domain).
 * Scaffold placeholder: chat (FC22–24, FC27–28), planner (FC1–7, FC25–26),
 * and classes (FC20–21) sections mount here as features are built.
 * Props: none.
 */
export default function Dashboard() {
  return (
    <main className="dashboard">
      <h1 className="dashboard-title">Academic AI Advisor</h1>
      <p className="dashboard-empty">
        Nothing mounted yet — advisor features appear here as they are built (FC1–FC21).
      </p>
    </main>
  );
}