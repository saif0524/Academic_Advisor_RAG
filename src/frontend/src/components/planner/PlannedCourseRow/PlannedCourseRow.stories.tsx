import type { Meta } from '@storybook/react-vite';
import PlannedCourseRow from './PlannedCourseRow';
import type { SemesterCourse } from '../../../api/types';

const meta = {
  title: 'Components/planner/PlannedCourseRow',
  component: PlannedCourseRow,
  args: {
    course: {
      id: '4316',
      title: 'COMPUTER SYSTEM DESIGN PROJECT I',
      creditHours: 3,
      meeting: 'MW 4:00–5:20',
    } satisfies SemesterCourse,
    onRemove: () => {},
  },
} satisfies Meta<typeof PlannedCourseRow>;

export default meta;

export const Default = {};

/** Wireframe 03 — engine prerequisite verdict under the row (FC29). */
export const WithWarning = {
  args: {
    course: {
      id: '4381',
      title: 'INFORMATION SECURITY II',
      creditHours: 3,
      meeting: 'MW 10:00–11:20',
      warning: 'CSE 4381 needs CSE 4380 in an earlier semester',
    } satisfies SemesterCourse,
    onRemove: () => {},
  },
};

/** In-progress course carried on the profile (FC21 status display). */
export const InProgress = {
  args: {
    course: { id: '3310', title: 'FUNDAMENTALS OF SOFTWARE ENGINEERING', creditHours: 3, meeting: 'TuTh 9:30–10:50' } satisfies SemesterCourse,
    statusNote: 'In progress',
    onRemove: undefined,
  },
};

export const UnknownCourse = {
  args: { course: { id: '9999', creditHours: 3 } as SemesterCourse, onRemove: () => {} },
};