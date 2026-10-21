import type { Meta } from '@storybook/react-vite';
import Badge from './Badge';

const meta = {
  title: 'Components/shared/Badge',
  component: Badge,
  args: { children: 'In progress' },
  argTypes: {
    variant: {
      control: 'radio',
      options: ['neutral', 'primary', 'info', 'success', 'warning', 'danger'],
    },
  },
} satisfies Meta<typeof Badge>;

export default meta;

export const Neutral = {};
export const WithDot = { args: { dot: true } };

/** Engine-verdict badges as they appear on course surfaces (FC29–FC32). */
export const Verdicts = {
  render: () => (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      <Badge variant="success">Prerequisites met</Badge>
      <Badge variant="success">Fits your schedule</Badge>
      <Badge variant="warning">Needs CSE 4380 first</Badge>
      <Badge variant="warning">Prereq in progress (CSE 3320)</Badge>
      <Badge variant="danger">Conflicts with CSE 4382</Badge>
      <Badge variant="info">1 issue</Badge>
    </div>
  ),
};