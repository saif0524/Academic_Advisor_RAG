import { useState } from 'react';
import type { Meta } from '@storybook/react-vite';
import ClassStatusSelect from './ClassStatusSelect';
import type { ClassStatus } from '../../../api/classes';

const meta = {
  title: 'Components/classes/ClassStatusSelect',
  component: ClassStatusSelect,
  args: { courseLabel: 'CSE 1105', status: 'not_taken', onChange: async () => {} },
} satisfies Meta<typeof ClassStatusSelect>;

export default meta;

export const Default = {};

/** Injected fixture saver — never hits the real api. */
export const Interactive = {
  render: () => {
    const [status, setStatus] = useState<ClassStatus>('in_progress');
    return <ClassStatusSelect courseLabel="CSE 1105" status={status} onChange={async (next) => setStatus(next)} />;
  },
};

export const SaveFails = {
  args: { status: 'passed', onChange: async () => { throw new Error('boom'); } },
};
