# Git Process

Source for FC IDs: `docs/planning/2026-10-18-functional-requirements.md`.

## 1. Branches

- Default branch: `main`. Work happens on short-lived feature branches; no direct commits to `main`.
- **Branch names use a type prefix, then the FC id of the work:**

  ```
  <type>/fc<NN>-<short-slug>
  ```

  - Types: `feat/` (default, new functionality), `fix/` (bug fixes), `docs/` (documentation-only changes). Closest reasonable type wins; don't invent new ones without agreeing here.
  - The FC id comes immediately after the type prefix, lowercase, then a short hyphenated slug describing the work.
  - Examples:
    - `feat/fc9-semantic-course-search` — NL course search (FC9)
    - `feat/fc23-class-status-changes` — assistant confirmation actions (FC23)
    - `fix/fc29-prereq-checks` — prerequisite safeguard regression (FC29)
  - Branches must trace to at least one FC id, per the repo workflow rule ("trace every feature to its FC IDs before implementing"). Genuinely new requirements should be added to the FC doc (as `FC-new-<short-name>` until confirmed) before the branch is cut.

### Branch spanning multiple FCs

- When one branch tackles several requirements (common when they ship together, e.g. FC29–FC32 safeguards), **pick one FC for the branch name** — the primary one: the FC the branch is centered on, or the one the others depend on or are verified through.
- **List the remaining FCs in the PR description** under an "Implements" line, e.g.:

  ```
  Implements: FC29 (primary)
  Also implements: FC30, FC31, FC32
  ```

## 2. Pull Requests

- PR title: `FC<NN>: <one-line summary>` (keep the primary FC id visible).
- PR description must include:
  - **Implements / Also implements** line(s) with every FC id touched, as shown above.
  - A short note on what changed and how it was verified (tests for engine/services/agent logic per the tester conventions; Storybook review for UI).
  - Confirmation that affected docs were checked/updated (FC requirements doc, domain model, AGENTS.md repo map, dated proposals) — implementation tasks aren't done until docs are current.
- Merge to `main` after review; delete the feature branch once merged.

## 3. Quick reference

| Situation | Branch name | PR |
| --- | --- | --- |
| Single FC, new feature | `feat/fc21-class-status` | `Implements: FC21` |
| Single FC, bug fix | `fix/fc31-conflict-detection` | `Implements: FC31` |
| Several FCs shipped together | `feat/fc29-...` (primary) | Primary + `Also implements:` the rest |
| Docs-only change (new proposal, doc fix) | `docs/<slug>`, or `docs/fc33-...` if it serves an FC | Note which FCs the doc affects |