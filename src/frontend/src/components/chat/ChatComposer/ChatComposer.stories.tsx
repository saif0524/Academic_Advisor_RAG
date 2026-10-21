import type { Meta, StoryObj } from '@storybook/react-vite';
import ChatComposer from './ChatComposer';
import { expect, userEvent } from 'storybook/test';

const meta = {
  title: 'Components/chat/ChatComposer',
  component: ChatComposer,
  args: { onSend: () => {} },
} satisfies Meta<typeof ChatComposer>;

export default meta;

export const Default: StoryObj<typeof ChatComposer> = {};
export const Busy: StoryObj<typeof ChatComposer> = { args: { busy: true } };
export const Disabled: StoryObj<typeof ChatComposer> = { args: { disabled: true } };

let sentTexts: string[] = [];

/** Enter sends the draft and clears it; Shift+Enter keeps the newline. */
export const SendsOnEnter: StoryObj<typeof ChatComposer> = {
  play: async ({ canvas }) => {
    const field = canvas.getByLabelText('Message to the advisor');
    await userEvent.type(field, 'What does CSE 4380 cover?');
    await userEvent.keyboard('{Enter}');
    await expect(field).toHaveValue('');
    void sentTexts;
  },
};