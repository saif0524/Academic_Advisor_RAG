import type { Meta } from '@storybook/react-vite';
import PlanCheckBanner from './PlanCheckBanner';

const meta = {
  title: 'Components/planner/PlanCheckBanner',
  component: PlanCheckBanner,
  args: { status: 'ok' as const },
} satisfies Meta<typeof PlanCheckBanner>;

export default meta;

/** Wireframe 02 — green all-clear. */
export const Ok = {};

/** Wireframe 03 — live prerequisite flags after an unsaved removal (FC29). */
export const Issues = {
  args: {
    status: 'issues' as const,
    issues: [
      'CSE 4381 needs CSE 4380 in an earlier semester',
      'CSE 4317 needs CSE 4316 in an earlier semester',
    ],
  },
};