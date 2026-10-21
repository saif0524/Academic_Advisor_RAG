import type { Meta } from '@storybook/react-vite';
import SearchFilterChips from './SearchFilterChips';

const FILTERS_FIXTURE = [
  { id: 'spring-2027', label: 'Spring 2027', count: 3 },
  { id: 'degree', label: 'Counts toward my degree', count: 4 },
  { id: 'schedule', label: 'Fits my schedule', count: 3 },
];

const meta = {
  title: 'Components/search/SearchFilterChips',
  component: SearchFilterChips,
  args: { filters: FILTERS_FIXTURE, activeIds: [], onToggle: () => {} },
} satisfies Meta<typeof SearchFilterChips>;

export default meta;

export const Default = {};
export const SomeActive = { args: { activeIds: ['degree'] } };
export const NoFilters = { args: { filters: [] } };