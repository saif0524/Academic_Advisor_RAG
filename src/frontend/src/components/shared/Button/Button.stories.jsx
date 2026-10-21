import { expect } from 'storybook/test';
import Button from './Button';

const meta = {
  title: 'Components/shared/Button',
  component: Button,
  args: { children: 'Confirm changes', variant: 'primary' },
  argTypes: {
    variant: { control: 'radio', options: ['primary', 'secondary'] },
  },
};

export default meta;

export const Primary = {};

export const Secondary = { args: { variant: 'secondary' } };

export const Disabled = { args: { disabled: true } };

/* Exactly one CssCheck per project (Storybook setup): proves the global
   stylesheet (src/index.css tokens) actually loaded in the story canvas. */
export const CssCheck = {
  play: async ({ canvas }) => {
    const button = canvas.getByRole('button', { name: /confirm changes/i });
    // .button--primary resolves var(--color-primary) = #0b3d97 → rgb(11, 61, 151).
    await expect(getComputedStyle(button).backgroundColor).toBe('rgb(11, 61, 151)');
  },
};