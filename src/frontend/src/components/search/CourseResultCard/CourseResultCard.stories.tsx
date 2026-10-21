import type { Meta } from '@storybook/react-vite';
import CourseResultCard from './CourseResultCard';

const COURSE_FIXTURE = {
  id: '4380',
  title: 'INFORMATION SECURITY',
  creditHours: 3,
  meeting: '3 hrs · TuTh 11:00–12:20',
  description:
    'Hands-on introduction to the basics of security. Includes system security, buffer overflows, a high-level overview of cryptography, firewalls and intrusion detection.',
  term: 'Spring 2027',
  flags: [
    { label: 'Fits your schedule', variant: 'success' as const },
    { label: 'Prerequisites met', variant: 'success' as const },
  ],
};

const meta = {
  title: 'Components/search/CourseResultCard',
  component: CourseResultCard,
  args: { course: COURSE_FIXTURE, onDetails: () => {} },
} satisfies Meta<typeof CourseResultCard>;

export default meta;

export const Default = {};

/** Mixed verdict badges (FC29 warn, FC31 conflict — all api-supplied). */
export const WithFlags = {
  args: {
    course: {
      ...COURSE_FIXTURE,
      id: '4344',
      title: 'COMPUTER NETWORK ORGANIZATION',
      meeting: '3 hrs · MW 2:30–3:50',
      flags: [
        { label: 'Conflicts with CSE 4382', variant: 'danger' as const },
        { label: 'Prerequisites met', variant: 'success' as const },
      ],
    },
    onDetails: () => {},
  },
};

export const DetailsBusy = { args: { detailsBusy: true } };
export const NoFlags = { args: { course: { ...COURSE_FIXTURE, flags: [] } } };