import type { Meta } from '@storybook/react-vite';
import Markdown from './Markdown';

const meta = {
  title: 'Components/shared/Markdown',
  component: Markdown,
  args: {
    text:
      '## Suggested next steps\n\n' +
      'Based on your plan, **CSE 4380 Information Security** is the strongest pick:\n\n' +
      '- It is the prerequisite for `CSE 4381`.\n' +
      '- Your plan needs CSE 4381 in Fall 2027.\n\n' +
      '| Course | Credits |\n| --- | --- |\n| CSE 4380 | 3 |\n| CSE 4381 | 3 |\n',
  },
} satisfies Meta<typeof Markdown>;

export default meta;

export const Default = {};
export const PlainText = { args: { text: 'I could not find courses matching that — try a course code.' } };
