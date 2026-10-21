import type { Meta } from '@storybook/react-vite';
import Icon from './Icon';
import type { IconName } from './Icon';

const ICON_NAMES: IconName[] = [
  'search', 'plus', 'close', 'check', 'checkCircle', 'warning', 'info',
  'edit', 'chevronDown', 'chevronRight', 'calendar', 'clock', 'send',
  'user', 'cap', 'chat', 'bookOpen', 'list',
];

const meta = {
  title: 'Components/shared/Icon',
  component: Icon,
  argTypes: {
    name: { control: 'select', options: ICON_NAMES },
  },
  args: { name: 'search', size: 24 },
} satisfies Meta<typeof Icon>;

export default meta;

export const Single = {};

/** Gallery of every glyph at a uniform size. */
export const Gallery = {
  render: () => (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
      {ICON_NAMES.map((name) => (
        <Icon key={name} name={name} size={22} label={name} />
      ))}
    </div>
  ),
};