# Academic AI Advisor — frontend

React + **TypeScript** UI for the RAG-based academic advising platform
(`src/frontend/`, domain-model §5). Built with Vite + Storybook 10; component
conventions in `.pi/skills/react-component/SKILL.md`; UI structure in
`docs/planning/2026-10-19-src-monorepo-structure.md` §frontend; screens follow
the wireframes in `docs/wireframes/` (01 home, 02–03 timeline, 04 search,
05 account, 06 chat history).

## Commands

```bash
npm run dev             # Vite dev server (http://localhost:5173)
npm run build           # Production build
npm run typecheck       # tsc --noEmit (strict TS)
npm run lint            # oxlint
npm run storybook       # Storybook dev (http://localhost:6006)
npm run build-storybook # Static Storybook build
npx vitest --project storybook run   # story-driven browser tests (playwright)
```

Done = typecheck + lint + build + stories green.

## Layout

```
src/
├── main.tsx                  # entry: SessionProvider (FC36) + AdvisorApp
├── api/
│   ├── client.ts             # single HTTP wrapper (components never call fetch)
│   ├── types.ts              # shared domain DTOs (mirrors future FastAPI schemas)
│   ├── catalog.ts            # fixture data grounded in data/course-desc.jsonl
│   ├── plans.ts              # MOCK: FC1–FC3, FC7, FC19, FC25–FC26 (plan routes 501 today)
│   ├── courses.ts            # MOCK: FC8–FC12 search/detail + FC29–FC32 verdict displays
│   ├── chat.ts               # MOCK: FC22–24, FC27 chat (canned deterministic replies)
│   └── students.ts           # MOCK: FC36 profile + FC25/FC32 preferences
├── state/SessionContext.tsx  # app-wide session (provider + useSession hook)
├── components/               # one folder per component: Name.tsx + Name.css + Name.stories.tsx
│   ├── chat/                 # ChatPanel, ChatMessage(List), ChatComposer, ActionConfirmationCard
│   │                         #   (FC23 confirm gate), ConversationHistory(Item) — FC22–24/27/34
│   ├── planner/              # PlanProgressHeader, CurrentSemesterPanel, SemesterCard,
│   │                         #   SemesterTimeline, SemesterDetail, PlannedCourseRow, PlanCheckBanner,
│   │                         #   AddCourseSearch, UnsavedChangesBar, PlanComparisonTable,
│   │                         #   PlanningPreferences, MajorSpecSelector, PlanRoadmap — FC1–3/7/19/25–26/32
│   ├── search/               # CourseSearchBox, AdvisorAnswerCard, SearchFilterChips,
│   │                         #   CourseResultCard, CourseDetailDialog — FC8–FC12
│   ├── degrees/              # FC15–FC19 (pending — DegreeExplorer page is a placeholder)
│   ├── classes/              # FC20–FC21 (deferred — no wireframe coverage)
│   └── shared/               # AppSidebar, AppShell, Icon, Button, Badge, ProgressBar,
│                             #   TextInput, TextArea, Select, Checkbox, SearchInput,
│                             #   ConfirmDialog, textCase.ts
└── pages/                    # composition roots (may import any domain)
    ├── AdvisorApp.tsx        # page state + chat drawer state (no router, single-page state)
    ├── Dashboard.tsx         # wireframe 01/06: plan summary, this semester, my semesters
    ├── TimelinePage.tsx      # wireframes 02/03: draft edits + engine-verdict display (FC3)
    ├── CourseSearch.tsx      # wireframe 04: query → advisor answer + matching courses
    ├── AccountPage.tsx       # wireframe 05: profile, program change (FC23 gate), comparison, prefs
    ├── PlanGenerator.tsx     # FC2 full-page overlay (opened from Home "New plan")
    └── DegreeExplorer.tsx    # FC15–FC19 placeholder (explicit empty state)
```

## Configuration notes

- Storybook lives in `.storybook/` as `main.ts`/`preview.tsx` (Storybook 10
  default) — globs pick up `src/**/*.stories.@(js|jsx|mjs|ts|tsx)`.
- Global styles/design tokens only in `src/index.css`; components own their CSS.
- Built-in state only (hooks + Context). No Redux/Zustand/React Query.
- All HTTP goes through `api/client.ts` via `request<T>()`; until the FastAPI
  endpoints are wired, the `api/*.ts` services are labeled MOCKs (deterministic
  fixtures, real seed courses from `data/course-desc.jsonl`) — swap bodies for
  `request()` calls when the server lands.
- Engine verdicts (prereqs, conflicts, credit caps — FC29–FC32) are always
  display fields supplied by the api layer; the frontend never computes
  constraints, and FC23-style actions confirm in the UI before applying.