# Academic AI Advisor — frontend

React UI for the RAG-based academic advising platform (`src/frontend/`, domain-model §5).
Scaffolded with Vite (React, JS) + Storybook 10 + Vitest browser tests; structure follows
`docs/2026-10-19-src-monorepo-structure.md` §frontend and `.pi/skills/react-component/SKILL.md`.

## Commands

```bash
npm run dev             # Vite dev server (http://localhost:5173)
npm run build           # Production build
npm run storybook       # Storybook dev (http://localhost:6006)
npm run build-storybook # Static Storybook build
npx vitest --project storybook run   # browser-test all stories via the vitest addon
```

## Layout

```
src/
├── main.jsx                  # entry: SessionProvider + first page
├── api/client.js             # single HTTP wrapper (components never call fetch)
├── state/SessionContext.jsx  # app-wide session (provider + hook in one file)
├── components/               # one folder per component: Name.jsx + Name.css + Name.stories.jsx
│   ├── chat/                 # FC22–24, FC27–28
│   ├── planner/              # FC1–7, FC25–26
│   ├── degrees/              # FC15–FC19
│   ├── classes/              # FC20–21, FC23
│   └── shared/Button/        # cross-domain primitives — canonical anatomy example
└── pages/                    # composition roots (may import any domain)
    ├── Dashboard.jsx         # FC1–FC21 landing surface
    └── DegreeExplorer.jsx    # FC15–FC19 surface
```

## Configuration notes

- Storybook lives in `.storybook/` as `main.ts`/`preview.tsx` (Storybook 10 init default) —
  globs already pick up `src/**/*.stories.@(js|jsx|mjs|ts|tsx)`.
- Global styles/design tokens only in `src/index.css`; components own their CSS.
- Built-in state only (hooks + Context). No Redux/Zustand/React Query.
- Grounded UI: never render invented courses/degrees/sections — data comes from SQLite/Chroma
  behind the API; empty and error states render explicitly. Student actions (FC20–FC23) always
  go through a confirmation dialog.