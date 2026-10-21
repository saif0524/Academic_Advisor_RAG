---
name: langgraph
description: LangGraph orchestration conventions for the Academic AI Advisor agent (src/agent/) — building and modifying the advisor StateGraph — nodes, tools, edges and conditional routing, state schema, human-in-the-loop interrupts for confirm-before-acting (FC23), clarification loops (FC27–28), checkpointing. Use when creating or changing anything in the advisor graph: nodes, tools, edges, state, checkpointer, or graph entry points.
---

# LangGraph — advisor graph conventions

Scope: `src/agent/` orchestration. The graph implements the domain-model §3 loop — classify intent → route (exact/SQLite vs semantic/Chroma vs plan request, FC22, FC33) → tools → summarize — with plan generation delegated to the deterministic engine (FC2, FC25–FC26). If the graph structure diverges from §3, update `docs/planning/2026-10-18-ai-advisor-domain-model.md` (docs-stay-current rule).

## The one non-negotiable rule

Graph nodes decide; they never compute constraints. Nodes route and delegate; constraint math (FC29–FC32) and plan generation (FC2, FC25–FC26) happen in `core` behind tools — the graph must not be able to bypass `CourseRecommendationValidator` / `DegreePlanGenerator`.

## Nodes

- One node = one concern: `classify_node`, `clarify_node`, `confirm_node`, `summarize_node`, … Keep them small state functions returning partial updates:

  ```python
  def classify_node(state: AdvisorState) -> dict:
      ...
      return {"intent": intent, "messages": [...] }
  ```

- Nodes never construct managers/agents — they call tools or services built with injected managers. No global singletons.
- Nodes may call the LLM (classification, summary, clarification wording) but must not derive advising facts themselves; empty tool results flow through as empty results.
- Complex flows become subgraphs, not mega-nodes (plan comparison FC26, major switch FC5a–c).

## State

- One state type — `AdvisorState` (TypedDict or Pydantic), mirroring `ConversationSession` (§3): `messages` with the `add_messages` reducer, plus `intent`, `pending_action`, `context_state`, and any per-feature fields. Nodes return partial updates; never mutate the state in place.
- `pending_action` holds a proposed-but-not-yet-executed action (FC23) until explicitly confirmed or cancelled.

## Tools

- Tools live in `agent/tools/` and stay thin wrappers over `core`/`database` (schedule → SQL, FC8; search → Chroma, FC9; plan → deterministic engine): docstrings are LLM-facing — describe return values and when *not* to call; tool names snake_case.
- **Acting tools (add/drop class, create/modify plan — FC20–FC21, FC23) never fire from the model's decision alone.** They execute only after an `interrupt`/human-in-the-loop pause: store the proposal in `pending_action`, interrupt, resume only on explicit user confirmation; on denial route to summarize/clarify. Tests must cover this gate (see `tester` skill).
- Tool factories receive managers as parameters (closure/`functools.partial`) so graphs are rebuildable per app process.

## Edges & routing

- Entry: `START → classify_node`. Intent routing via **conditional edges** implemented as named `route_*` functions reading only `state.intent`/`state.pending_action`, with an explicit mapping dict — no stringly-typed branching buried in node bodies.
- Clarification (FC27–28) is a **bounded loop**: `clarify_node` → tool/plan refinement → back to classify; every loop must have a proceed-or-end condition.
- Terminal: after `summarize_node` → `END`; new user turns resume via the checkpointer.
- Draw/check the graph when it changes: `graph.get_graph().print_ascii()` or a Mermaid dump belongs in the PR description/doc note.

## Checkpointing

- Dev: `MemorySaver`. The chat-history persistence seam remains `SQLDatabaseManager` (FC34) — keep graph thread state and SQL history aligned; if they diverge, document why in the change and update the domain model.

## Testing hook

Graph tests run with stubbed models and fake tool nodes — assert on routing outcomes and state transitions, per the `tester` skill.