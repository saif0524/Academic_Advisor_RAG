import { useState } from 'react';
import Button from '../components/shared/Button/Button.jsx';
import PlanGenerator from './PlanGenerator.jsx';
import './Dashboard.css';

/**
 * Advisor landing page — composition root (may import from any domain).
 * Hosts the full-page degree-planner overlay (FC1, FC2, FC25): opening it
 * covers this page with the planner experience; its back action returns
 * here (no router — single-page state). Chat (FC22–24, FC27–28) and class
 * management (FC20–21) sections mount here as features are built.
 *
 * Props: initialPlanPageOpen (boolean, default false) — lets the Storybook
 * story show the planner overlay open without interaction.
 */
export default function Dashboard({ initialPlanPageOpen = false }) {
  const [isPlanPageOpen, setIsPlanPageOpen] = useState(initialPlanPageOpen);
  return (
    <>
      <main className="dashboard">
        <h1 className="dashboard-title">Academic AI Advisor</h1>
        <section className="dashboard-section" aria-label="Degree planner">
          <h2 className="dashboard-section-title">Degree planner</h2>
          <p className="dashboard-section-copy">
            Choose your major and specialization, then generate a semester-by-semester
            roadmap of your degree.
          </p>
          <Button onClick={() => setIsPlanPageOpen(true)}>Open the planner</Button>
        </section>
        <p className="dashboard-empty">
          Chat and class management appear here as features are built.
        </p>
      </main>
      {isPlanPageOpen && (
        <PlanGenerator onNavigateBack={() => setIsPlanPageOpen(false)} />
      )}
    </>
  );
}