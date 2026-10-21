---
name: react-component
description: React component conventions for the Academic AI Advisor frontend (src/frontend/) — one folder per component with the .jsx component, a plain .css file, and a mandatory Storybook CSF3 story; atomic decomposition into domain groups (chat/planner/degrees/classes/shared); built-in state management only (hooks + Context, no Redux/Zustand). Use when creating, modifying, or reviewing any frontend/React code or Storybook stories, or when scaffolding src/frontend.
---

# React component conventions

Applies to everything under `src/frontend/` (per `docs/planning/2026-10-19-src-monorepo-structure.md` §frontend). Follow these rules for creating, modifying, and reviewing frontend code.

## Bootstrapping (only while `src/frontend/` does not exist)

Do not scaffold silently — propose the setup and wait for explicit confirmation:

1. `npm create vite@latest src/frontend -- --template react` (JS template; the proposal's tree is `.jsx`/`.js`).
2. `cd src/frontend && npm install`.
3. `npx storybook@latest init` — then check `.storybook/main.js` picks up `src/**/*.stories.@(js|jsx)`.
4. If the user wants TypeScript instead of the proposal's JSX, switch extensions to `.tsx`/`.ts` **and update this skill plus the proposal doc first**.

## Component anatomy — one folder per component

```text
src/frontend/src/components/<domain>/<ComponentName>/
├── <ComponentName>.jsx          # functional component, default export
├── <ComponentName>.css          # plain CSS, imported at the top of the .jsx
└── <ComponentName>.stories.jsx  # Storybook CSF3 — required, ≥1 story
```

- Folder and files named exactly after the component (PascalCase). One component per folder.
- Props are the component's API: keep components presentational when practical; document props in a JSDoc block on the component (no prop-types dependency).
- **No component unit tests** — that is the `tester` skill's rule; UI verification is Storybook review (stories are the test surface for components).
- An optional `index.jsx` barrel re-export is allowed for tidy imports — nothing else goes in the folder.

```jsx
import './CourseCard.css';

/** Search-result card for a course. FC8/FC11. Props: course, bookmarked, onBookmark. */
export default function CourseCard({ course, bookmarked, onBookmark }) { … }
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

```jsx
import CourseCard from './CourseCard';

const meta = {
  title: 'Components/classes/CourseCard',
  component: CourseCard,
  args: { course: { id: '1105', title: 'Intro to CS&E' } }, // real seed data, never invented
};
export default meta;

export const Default = {};
export const Bookmarked = { args: { bookmarked: true } };
```

- `title` = `Components/<domain>/<ComponentName>`.
- Components needing Context are wrapped by a decorator with a stub provider; components that fetch receive data through props in stories (or a context decorator with fixtures) — stories must not hit the real API.

## Grounded UI (repo rules)

- Never render invented courses, sections, instructors, degrees, or requirements — data exists only in SQLite/Chroma behind the API. Empty lookup → explicit empty state.
- Actions taken on the student's behalf (adding/dropping classes, plan or major changes — FC20–FC21, FC23) always flow through a confirmation dialog in the UI; plan changes also need the multi-turn clarification flow (FC27–FC28).
- Cite FC IDs in component header comments for the requirements the component serves.

## Review checklist

Folder has component + CSS + story · default export · props documented · story title/controls correct · data states rendered · plain-CSS naming rule · no cross-domain imports outside `shared/` · no external state libs · `api/client.js` used for all HTTP · FC citations present · confirmation dialog for FC23-style actions.