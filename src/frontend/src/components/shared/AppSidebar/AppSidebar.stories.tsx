import type { Meta } from '@storybook/react-vite';
import AppSidebar from './AppSidebar';

const meta = {
  title: 'Components/shared/AppSidebar',
  component: AppSidebar,
  args: { active: 'home' as const, onNavigate: () => {}, studentName: 'Jordan Lee' },
  argTypes: {
    active: { control: 'radio', options: ['home', 'timeline', 'search', 'account'] },
  },
} satisfies Meta<typeof AppSidebar>;

export default meta;

export const Home = {};
export const Timeline = { args: { active: 'timeline' as const } };

export const InitialsOnly = { args: { studentName: undefined } };