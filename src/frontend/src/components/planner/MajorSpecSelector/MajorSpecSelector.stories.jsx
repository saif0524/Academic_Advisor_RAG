import MajorSpecSelector from './MajorSpecSelector';

const OPTIONS_FIXTURE = {
  majors: [
    { name: 'BS in Computer Science', concentrations: ['Cybersecurity', 'Artificial Intelligence'] },
    {
      name: 'BS in Software Engineering',
      concentrations: ['Cybersecurity', 'Artificial Intelligence'],
    },
  ],
};

const meta = {
  title: 'Components/planner/MajorSpecSelector',
  component: MajorSpecSelector,
};

export default meta;

export const Default = {
  args: {
    options: OPTIONS_FIXTURE,
    major: 'BS in Computer Science',
    concentration: 'Artificial Intelligence',
    includeSummer: false,
    onSelectionChange: () => {},
    onGenerate: () => {},
    canGenerate: true,
  },
};

export const NoOptions = {
  args: {
    options: null,
    onSelectionChange: () => {},
    onGenerate: () => {},
  },
};

/* Major picked but no specialization yet — generate stays disabled (one
   major + one specialization required, FC1). */
export const PartialSelection = {
  args: {
    options: OPTIONS_FIXTURE,
    major: 'BS in Software Engineering',
    concentration: '',
    onSelectionChange: () => {},
    onGenerate: () => {},
    canGenerate: false,
  },
};

/* All controls disabled while a generation is running. */
export const Generating = {
  args: {
    ...Default.args,
    canGenerate: false,
    disabled: true,
  },
};