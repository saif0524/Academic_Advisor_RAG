import type { Meta, StoryObj } from '@storybook/react-vite';
import SearchInput from './SearchInput';
import { expect, userEvent } from 'storybook/test';

/** Real seed courses (data/course-desc.jsonl); meeting-time strings are mock
    metadata from the api seams (real section data lives in SQLite, FC33). */
const SUGGESTIONS_FIXTURE = [
  { id: '4380', primary: 'Information Security', secondary: '3 hrs · TuTh 11:00–12:20', badge: 'Prerequisites met', badgeVariant: 'success' as const },
  { id: '4381', primary: 'Information Security II', secondary: '3 hrs · MW 10:00–11:20', badge: 'Needs CSE 4380 first', badgeVariant: 'warning' as const },
  { id: '4308', primary: 'Artificial Intelligence', secondary: '3 hrs · MW 1:00–2:20', badge: 'Prerequisites met', badgeVariant: 'success' as const },
];

const meta = {
  title: 'Components/shared/SearchInput',
  component: SearchInput,
  args: {
    value: 'secur',
    onChange: () => {},
    placeholder: 'Search by code or title',
    suggestions: SUGGESTIONS_FIXTURE,
  },
} satisfies Meta<typeof SearchInput>;

export default meta;

/** Suggestion list rendered while focused and the query is non-empty. */
export const WithSuggestions: StoryObj<typeof SearchInput> = {
  play: async ({ canvas }) => {
    await userEvent.click(canvas.getByRole('textbox', { hidden: true }));
    await expect(canvas.getByText('Information Security II')).toBeVisible();
  },
};

export const NoResults: StoryObj<typeof SearchInput> = {
  args: { value: 'zzz', suggestions: [], noResultsText: 'No courses match your search.' },
};

export const PlainField: StoryObj<typeof SearchInput> = {
  args: { value: '', placeholder: 'Search conversations' },
};