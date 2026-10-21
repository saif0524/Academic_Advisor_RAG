import type { Meta } from '@storybook/react-vite';
import Button from './Button';

const meta = {
  title: 'Components/shared/Button',
  component: Button,
  args: { children: 'Save plan', disabled: false, iconOnly: false },
  argTypes: {
    variant: { control: 'radio', options: ['primary', 'secondary', 'ghost', 'danger'] },
  },
} satisfies Meta<typeof Button>;

export default meta;

export const Primary = {};
export const Secondary = { args: { variant: 'secondary' as const, children: 'Cancel' } };
export const Ghost = { args: { variant: 'ghost' as const, children: 'Discard' } };
export const Danger = { args: { variant: 'danger' as const, children: 'Remove course' } };
export const Disabled = { args: { disabled: true } };