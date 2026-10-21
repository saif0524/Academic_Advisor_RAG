import type { Meta, StoryObj } from '@storybook/react-vite';
import CourseSearch from './CourseSearch';
import type { CourseDetail, SearchResponse } from '../api/types';
import { expect, userEvent } from 'storybook/test';

/* Canned seam fixtures — grounded course records (api/catalog) with mock
   engine verdicts (API-layer, never computed client-side). */
const RESPONSE_FIXTURE: SearchResponse = {
  answer: {
    text:
      'Two cybersecurity electives fit your plan toward the Cybersecurity concentration. ' +
      'CSE 4380 Information Security is the strongest pick — it is the prerequisite for ' +
      'CSE 4381, which your plan needs in Fall 2027.',
    matchCount: 2,
  },
  courses: [
    {
      id: '4380',
      title: 'INFORMATION SECURITY',
      creditHours: 3,
      meeting: '3 hrs · TuTh 11:00–12:20',
      description: 'Hands-on introduction to the basics of security.',
      term: 'Spring 2027',
      flags: [
        { label: 'Fits your schedule', variant: 'success' },
        { label: 'Prerequisites met', variant: 'success' },
      ],
    },
    {
      id: '4344',
      title: 'COMPUTER NETWORK ORGANIZATION',
      creditHours: 3,
      meeting: '3 hrs · MW 2:30–3:50',
      description: 'Design and analysis of computer networks.',
      term: 'Spring 2027',
      flags: [
        { label: 'Conflicts with CSE 4382', variant: 'danger' },
        { label: 'Prerequisites met', variant: 'success' },
      ],
    },
  ],
};

const DETAIL_FIXTURE: CourseDetail = {
  id: '4380',
  title: 'INFORMATION SECURITY',
  description: 'Hands-on introduction to the basics of security.',
  creditHours: 3,
  meeting: '3 hrs · TuTh 11:00–12:20',
  prereqs: [],
};

const SEAMS = {
  searchFn: () => Promise.resolve(RESPONSE_FIXTURE),
  detailFn: () => Promise.resolve(DETAIL_FIXTURE),
};

const meta = {
  title: 'Pages/CourseSearch',
  component: CourseSearch,
  args: SEAMS,
} satisfies Meta<typeof CourseSearch>;

export default meta;

export const Landing: StoryObj<typeof CourseSearch> = {};

/** Full wireframe 04 flow: ask → answer + matching courses → Details. */
export const SearchFlow: StoryObj<typeof CourseSearch> = {
  play: async ({ canvas }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'What does CSE 4380 cover?' }));
    await expect(await canvas.findByText(/Two cybersecurity electives/i)).toBeVisible();
    await userEvent.click(canvas.getAllByRole('button', { name: 'Details' })[0]);
    await expect(
      await canvas.findByRole('heading', { name: 'Prerequisites' }),
    ).toBeVisible();
  },
};

export const SearchError: StoryObj<typeof CourseSearch> = {
  args: { searchFn: () => Promise.reject(new Error('advisor API unreachable')), detailFn: () => Promise.resolve(null) },
  play: async ({ canvas }) => {
    await userEvent.type(canvas.getByLabelText('Search courses or ask a question'), 'security{Enter}');
    await expect(await canvas.findByText(/The advisor could not answer/i)).toBeVisible();
  },
};