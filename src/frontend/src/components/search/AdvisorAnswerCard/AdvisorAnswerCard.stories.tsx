import type { Meta } from '@storybook/react-vite';
import AdvisorAnswerCard from './AdvisorAnswerCard';

const meta = {
  title: 'Components/search/AdvisorAnswerCard',
  component: AdvisorAnswerCard,
  args: {
    answer: {
      text:
        'Two cybersecurity electives fit your plan toward the Cybersecurity concentration. ' +
        'CSE 4380 Information Security is the strongest pick — it is the prerequisite for ' +
        'CSE 4381, which your plan needs in Fall 2027.',
      matchCount: 2,
    },
  },
} satisfies Meta<typeof AdvisorAnswerCard>;

export default meta;

export const Default = {};
export const NoMatches = { args: { answer: { text: 'I could not find courses matching that — try a course code.', matchCount: 0 } } };
export const Loading = { args: { answer: null, loading: true } };
export const ErrorState = { args: { answer: null, error: 'advisor API unreachable' } };
export const Empty = { args: { answer: null } };