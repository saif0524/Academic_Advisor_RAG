---
name: react-component
description: React component conventions for the Academic AI Advisor frontend (src/frontend/) — one folder per component with the .jsx component, a plain .css file, and a mandatory Storybook CSF3 story; atomic decomposition into domain groups (chat/planner/degrees/classes/shared); built-in state management only (hooks + Context, no Redux/Zustand). Use when creating, modifying, or reviewing any frontend/React code or Storybook stories, or when scaffolding src/frontend.
---

# React component conventions

Applies to everything under `src/frontend/` (per `docs/planning/2026-10-19-src-monorepo-structure.md` §frontend). Follow these rules for creating, modifying, and reviewing frontend code.

## Bootstrapping (only when a fresh frontend is needed)

Do not scaffold silently — propose the setup and wait for explicit confirmation:

1. `npm create vite@latest src/frontend -- --template react-ts` (TypeScript template).
2. `cd src/frontend && npm install`.
3. `npx storybook@latest init` — then check `.storybook/main.ts` picks up `src/**/*.stories.@(js|jsx|ts|tsx)`.

(The repo's frontend is already TS — scaffolded as React-JS on 2026-10-20 and converted to
TypeScript on 2026-10-21 per the user's call; keep new files `.tsx`/`.ts`.)

## Component anatomy — one folder per component

```text
src/frontend/src/components/<domain>/<ComponentName>/
├── <ComponentName>.tsx          # functional component, default export, typed props
├── <ComponentName>.css          # plain CSS, imported at the top of the .tsx
└── <ComponentName>.stories.tsx  # Storybook CSF3 — required, ≥1 story
```

- Folder and files named exactly after the component (PascalCase). One component per folder.
- **TypeScript is the repo standard** (switched from JS on 2026-10-21): props get a typed `Props`
  interface in the same file; domain data shapes live in `src/api/types.ts` — import types with
  `import type`; extensionless relative imports (`./Button`, `../shared/Badge/Badge`). Document
  behavior/FC context in JSDoc comments on the component.
- No prop-types dependency — the TS interface is the contract.
- **No component unit tests** — that is the `tester` skill's rule; UI verification is Storybook review (stories are the test surface for components).
- An optional `index.ts` barrel re-export is allowed for tidy imports — nothing else goes in the folder.
- Run `npm run typecheck` (`tsc --noEmit`) alongside lint before calling frontend work done.

```tsx
import type { CourseResult } from '../../../api/types';
import { toTitleCase } from '../../shared/textCase';
import './CourseCard.css';

/** Search-result card for a course. FC8/FC11. */
interface CourseCardProps {
  course: CourseResult;
  bookmarked?: boolean;
  onBookmark?: (courseId: string) => void;
}
export default function CourseCard({ course, bookmarked = false, onBookmark }: CourseCardProps) { … }
```

## Layout, domains & atomic decomposition

Top-level groups under `components/` (from the proposal): `chat/` (FC22–24, FC27–28), `planner/` (FC1–FC7, FC25–FC26), `degrees/` (FC15–FC19), `classes/` (FC20–FC21, FC23), plus `shared/` for primitives reused across domains (buttons, cards, dialogs, form fields).

Decompose complex UIs into smaller single-purpose components:

- Split when a component exceeds ~150 lines, mixes layout + data-fetching + interaction, or repeats JSX another component already renders.
- Children live in the same domain folder; promote to `shared/` once a second domain needs them.
- No cross-domain imports except through `shared/`. Pages under `src/pages/` are composition roots — they may import anything.
- Every component, pages included, gets a story.

## State management — built-in only (no Redux/Zustand/React Query/SWR)

- Local UI state → `useState`; multi-step/local reducers → `useReducer`; derived values → `useMemo`; side effects → `useEffect` with correct deps + cleanup, never during render.
- State shared across a subtree → Context. App-wide contexts live in `src/state/<Name>Context.jsx` — provider **and** the `use<Name>()` hook exported from the same file (e.g. `state/SessionContext.jsx`). Component-scoped contexts are colocated inside the component folder.
- Prop drilling more than 2–3 levels is a smell → use Context instead.
- All HTTP access goes through `src/api/client.js`; components never call `fetch` inline. Fetched data lives in state/Context; empty, loading, and error states are always rendered explicitly.

## CSS — plain files only

- Each component imports its own `<ComponentName>.css`; no Tailwind, no CSS-in-JS, no `styled-components`.
- Class names are kebab-case, prefixed with the component name (`course-card-title`); element/modifier suffixes allowed (`.course-card-title--highlight`).
- No inline `style` objects except passing computed CSS custom properties (`style={{ '--chart-pct': '40%' }}`).
- Global styles (resets, `:root` design tokens) belong only in `src/index.css`.

## Storybook rules

CSF3, one story per distinct visual state (default plus empty/loading/error for data-driven components), controls for every prop:

```tsx
import type { Meta } from '@storybook/react-vite';
import CourseCard from './CourseCard';

const meta = {
  title: 'Components/search/CourseCard',
  component: CourseCard,
  args: { course: { id: '1105', title: 'INTRODUCTION TO COMPUTER SCIENCE AND ENGINEERING.', /* … */ } }, // real seed data, never invented
} satisfies Meta<typeof CourseCard>;
export default meta;

export const Default = {};
export const Bookmarked = { args: { bookmarked: true } };
```

- `title` = `Components/<domain>/<ComponentName>`.
- Components needing Context are wrapped by a decorator with a stub provider; components that fetch receive data through props in stories (or a context decorator with fixtures) — stories must not hit the real API.

## Wireframe check — required for any visual change

`docs/wireframes/*.png` are the visual spec. Storybook stories are what you compare against them. Any change that alters how a page or component looks must be compared with its wireframe before the work counts as done. Don't skip this because you think the change is small. No MCP or new dependencies are needed; Playwright is already a devDependency.

1. Run Storybook (`npm run storybook`, port 6006) if it isn't already running: `curl -s localhost:6006 >/dev/null`.
2. Screenshot the story (from `src/frontend/`):
   ```bash
   npx playwright screenshot --viewport-size=1440,1100 --full-page --wait-for-timeout=2500 \
     "http://localhost:6006/iframe.html?id=<story-id>&viewMode=story" ../../var/shots/<name>.png
   ```
   Get story ids from `curl -s localhost:6006/index.json`. `var/` is gitignored.
3. Open both the screenshot and the wireframe PNG with the `read` tool. List the differences in layout, hierarchy, palette, spacing, copy, and controls. Ignore the wireframe's title caption and the sage canvas around the mockup.
4. Fix the differences, take a new screenshot, and repeat until the two match. Report any differences you leave on purpose and why. Examples: data the wireframe shows but the API doesn't have (grounded-UI rule), or a wireframe badge with no backing status.

| Wireframe | Story id |
| --- | --- |
| `01-home-active-degree-plan.png` | `pages-dashboard--default` (chat dock: `pages-advisorapp--chat-drawer`) |
| `02-timeline-semester-detail.png` | `pages-timelinepage--default` |
| `03-timeline-prerequisite-warning.png` | `pages-timelinepage--remove-prereq-flags-warnings` |
| `04-search-advisor-answer.png` | `pages-coursesearch--search-flow` |
| `05-account-change-major.png` | `pages-accountpage--change-program-flow` |
| `06-chat-previous-conversations.png` | `pages-advisorapp--chat-drawer` |

Rules:
- Compare against **stories, not the live app.** The dev server shows "Failed to fetch" when the API is down. A story used for a wireframe comparison must render from injected fixtures.
- Use **design tokens** from `src/index.css`. The palette there was sampled from the wireframes: dark green `--color-primary`, lime `--color-accent`, and so on. Don't hardcode hex values in component CSS.
- When you add a page or a new wireframe, add a row to the table above.

## Grounded UI (repo rules)

- **POC fidelity (2026-10-22):** components should be simple and working — explicit loading/empty/error states where data comes from the api, but don't gold-plate skeletons, optimistic updates, or retry/backoff machinery.
- Never render invented courses, sections, instructors, degrees, or requirements — data exists only in SQLite/Chroma behind the API. Empty lookup → explicit empty state.
- Actions taken on the student's behalf (adding/dropping classes, plan or major changes — FC20–FC21, FC23) always flow through a confirmation dialog in the UI; plan changes also need the multi-turn clarification flow (FC27–FC28).
- Cite FC IDs in component header comments for the requirements the component serves.

## Review checklist

Folder has component + CSS + story · default export · typed props (TS interface; `import type` from `api/types` for domain shapes) · story title/controls correct · data states rendered · plain-CSS naming rule · no cross-domain imports outside `shared/` · no external state libs · `api/client.ts` used for all HTTP · FC citations present · confirmation dialog for FC23-style actions · `npm run typecheck` + lint clean · wireframe check done (screenshot vs `docs/wireframes/` PNG, differences resolved or explained).