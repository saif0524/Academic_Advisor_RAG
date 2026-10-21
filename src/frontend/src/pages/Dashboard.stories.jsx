import { expect } from 'storybook/test';
import Dashboard from './Dashboard';

const meta = {
  title: 'Pages/Dashboard',
  component: Dashboard,
};

export default meta;

export const Default = {};

/* Overlay open via the fixture prop — the planner covers the dashboard and
   offers the back action; the default loaders run against the mocked api
   service (api/plans.js). */
export const PlannerOverlayOpen = {
  args: { initialPlanPageOpen: true },
};

/* Opening the planner from the landing page (FC1/FC2/FC25 entry point). */
export const OpensPlanner = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('button', { name: /open the planner/i })).toBeVisible();
  },
};