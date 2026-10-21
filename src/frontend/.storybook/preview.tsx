import type { Preview, Decorator } from '@storybook/react-vite'
import '../src/index.css';
import { SessionProvider } from '../src/state/SessionContext';

/* Shared decorators: the real app provider tree (SessionProvider, FC36) and
   the real root stylesheet (src/index.css tokens), so every story renders as
   it does in the app. No MSW yet — the API has no endpoints, and stories
   receive data through props (they must never hit the real API). */
const withProviders: Decorator = (Story) => (
  <SessionProvider>
    <Story />
  </SessionProvider>
);

const preview: Preview = {
  decorators: [withProviders],
  parameters: {
    controls: {
      matchers: {
       color: /(background|color)$/i,
       date: /Date$/i,
      },
    },

    a11y: {
      // 'todo' - show a11y violations in the test UI only
      // 'error' - fail CI on a11y violations
      // 'off' - skip a11y checks entirely
      test: 'todo'
    }
  },
};

export default preview;