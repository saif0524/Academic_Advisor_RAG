import type { Meta } from '@storybook/react-vite';
import CourseDetailDialog from './CourseDetailDialog';
import type { CourseDetail } from '../../../api/types';

const DETAIL_FIXTURE: CourseDetail = {
  id: '4380',
  title: 'INFORMATION SECURITY',
  description:
    'Hands-on introduction to the basics of security. Includes system security, buffer overflows, a high-level overview of cryptography, firewalls and intrusion detection.',
  creditHours: 3,
  meeting: '3 hrs · TuTh 11:00–12:20',
  prereqs: [],
};

const meta = {
  title: 'Components/search/CourseDetailDialog',
  component: CourseDetailDialog,
  args: { open: true, detail: DETAIL_FIXTURE, onClose: () => {} },
} satisfies Meta<typeof CourseDetailDialog>;

export default meta;

export const Default = {};
export const WithPrereqStatuses = {
  args: {
    detail: {
      id: '4381',
      title: 'INFORMATION SECURITY II',
      description:
        'Deeper study of the fundamentals of security, including symmetric key cryptography, public key cryptography, cryptographic protocols, malware design.',
      creditHours: 3,
      meeting: '3 hrs · MW 10:00–11:20',
      prereqs: [
        { id: '4380', title: 'INFORMATION SECURITY', status: 'met' as const },
      ],
    },
  },
};
export const Loading = { args: { detail: null, loading: true } };
export const ErrorState = { args: { detail: null, error: 'advisor API unreachable' } };
export const Unavailable = { args: { detail: null } };
export const Closed = { args: { open: false } };