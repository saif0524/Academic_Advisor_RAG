import type { Meta } from '@storybook/react-vite';
import AddCourseSearch from './AddCourseSearch';
import type { CourseSuggestion } from '../../../api/types';

/** Real seed courses; meeting strings + verdict badges are mock verdicts of
    FC29/FC31 checks (api/courses). */
const CANDIDATES_FIXTURE: CourseSuggestion[] = [
  { id: '4308', title: 'ARTIFICIAL INTELLIGENCE', creditHours: 3, meeting: 'MW 1:00–2:20', badge: 'Prerequisites met', badgeVariant: 'success', conflict: null },
  { id: '4309', title: 'FUNDAMENTALS OF MACHINE LEARNING', creditHours: 3, meeting: 'MW 5:30–6:50', badge: 'Prerequisites met', badgeVariant: 'success', conflict: null },
  { id: '4344', title: 'COMPUTER NETWORK ORGANIZATION', creditHours: 3, meeting: 'MW 2:30–3:50', badge: 'Conflicts with CSE 4382', badgeVariant: 'danger', conflict: 'Conflicts with CSE 4382' },
];

const meta = {
  title: 'Components/planner/AddCourseSearch',
  component: AddCourseSearch,
  args: {
    value: '',
    onChange: () => {},
    candidates: CANDIDATES_FIXTURE,
    onPick: () => {},
  },
} satisfies Meta<typeof AddCourseSearch>;

export default meta;

export const Default = {};
export const WithQuery = { args: { value: '43' } };
export const Loading = { args: { candidates: null, loading: true } };
export const ErrorState = { args: { candidates: null, error: 'advisor API unreachable' } };
export const Unavailable = { args: { candidates: null } };