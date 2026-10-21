import type { Meta, StoryObj } from '@storybook/react-vite';
import CourseSearchBox from './CourseSearchBox';
import { userEvent } from 'storybook/test';

const meta = {
  title: 'Components/search/CourseSearchBox',
  component: CourseSearchBox,
  args: { onSearch: () => {} },
} satisfies Meta<typeof CourseSearchBox>;

export default meta;

export const Default: StoryObj<typeof CourseSearchBox> = {};

export const Busy: StoryObj<typeof CourseSearchBox> = { args: { busy: true } };

/** Clicking an example chip fills and submits that query (FC35 prompts). */
export const ExampleChipClick: StoryObj<typeof CourseSearchBox> = {
  play: async ({ canvas }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'What does CSE 4380 cover?' }));
  },
};