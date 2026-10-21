import type { Meta, StoryObj } from '@storybook/react-vite';
import AdvisorApp from './AdvisorApp';
import { expect, userEvent } from 'storybook/test';

const meta = {
  title: 'Pages/AdvisorApp',
  component: AdvisorApp,
} satisfies Meta<typeof AdvisorApp>;

export default meta;

/** First screen students see: home = wireframe 01, chat closed. */
export const Home: StoryObj<typeof AdvisorApp> = {};

/** Page navigation via the shared sidebar (single-page state, no router). */
export const NavigateToTimeline: StoryObj<typeof AdvisorApp> = {
  play: async ({ canvas }) => {
    await userEvent.click(canvas.getByRole('button', { name: /Timeline/i }));
    await expect(await canvas.findByRole('heading', { level: 1, name: /Timeline/i })).toBeVisible();
  },
};

/** The advisor drawer opens from the floating pill and persists. */
export const ChatDrawer: StoryObj<typeof AdvisorApp> = {
  play: async ({ canvas }) => {
    await userEvent.click(canvas.getByRole('button', { name: /Advisor/i }));
    await expect(await canvas.findByText(/Demo replies — no live advisor agent/i)).toBeVisible();
    await userEvent.click(canvas.getByRole('button', { name: 'Close advisor chat' }));
    await expect(canvas.queryByText(/Demo replies — no live advisor agent/i)).not.toBeInTheDocument();
  },
};