/**
 * /build — deterministic build pipeline for the Academic AI Advisor repo.
 *
 * Phases (each phase = one isolated `pi --print` subprocess, sequential):
 *   1. ARCHITECT  stronger model requested via PI_BUILD_ARCHITECT_MODEL; read-only tools.
 *                 Produces a task graph (strict JSON) parsed & validated in plain code.
 *   2. WORKER     one subprocess per task, in dependency order. Writes code.
 *   3. TESTER     fresh subprocess, no write tools. Must start its output with PASS or FAIL.
 *   4. DOC WRITER read+edit tools; only appends to docs/implementation-log.md.
 *
 * The orchestrator itself is plain TypeScript: no LLM calls, no heuristic retries.
 * Configure via environment variables (all optional):
 *   PI_BUILD_PI_BIN            pi binary to use (default: "pi", falls back to "npx pi")
 *   PI_BUILD_ARCHITECT_MODEL   model pattern for phase 1 (default: inherit pi default)
 *   PI_BUILD_WORKER_MODEL      model pattern for phase 2
 *   PI_BUILD_TESTER_MODEL      model pattern for phase 3
 *   PI_BUILD_DOCS_MODEL        model pattern for phase 4
 *   PI_BUILD_TIMEOUT_MS        per-phase timeout (default: 900000)
 *   PI_BUILD_MAX_TASKS         reject graphs larger than this (default: 12)
 *
 * Per-phase model defaults live in the committed .pi/pipeline.json (team-shared);
 * PI_BUILD_*_MODEL env vars override per user. Phases with neither inherit pi's
 * project default model (settings.json defaultModel).
 */

import { execFile, spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { promisify } from "node:util";
import type { ExtensionAPI, ExtensionCommandContext } from "@earendil-works/pi-coding-agent";

const execFileAsync = promisify(execFile);

// ---------- configuration ----------

const TIMEOUT_MS = Number(process.env.PI_BUILD_TIMEOUT_MS ?? 900_000);
const MAX_TASKS = Number(process.env.PI_BUILD_MAX_TASKS ?? 12);

interface PipelineConfig {
	architectModel?: string;
	workerModel?: string;
	testerModel?: string;
	docsModel?: string;
}

/** Committed team defaults from .pi/pipeline.json (absent file = empty config). */
function readPipelineConfig(): PipelineConfig {
	try {
		const raw = readFileSync(join(process.cwd(), ".pi", "pipeline.json"), "utf8");
		const parsed = JSON.parse(raw);
		if (parsed && typeof parsed === "object") return parsed as PipelineConfig;
	} catch {
		// missing or unparseable config — env vars / pi defaults apply
	}
	return {};
}

function resolveModel(envValue: string | undefined, fileKey: keyof PipelineConfig, fileCfg: PipelineConfig): string | undefined {
	return envValue ?? fileCfg[fileKey];
}

// ---------- subprocess plumbing ----------

let piCommand: string[] | null = null;

/** Resolve how to invoke the pi CLI once, lazily (never in the factory). */
function resolvePiCommand(): string[] {
	if (piCommand) return piCommand;
	if (process.env.PI_BUILD_PI_BIN) {
		piCommand = [process.env.PI_BUILD_PI_BIN];
		return piCommand;
	}
	try {
		const check = spawnSync("pi", ["--version"], { timeout: 5_000 });
		piCommand = check.status === 0 ? ["pi"] : ["npx", "pi"];
	} catch {
		piCommand = ["npx", "pi"];
	}
	return piCommand;
}

interface PiRun {
	ok: boolean;
	text: string;
	stderr: string;
}

/** Run one headless pi invocation to completion. */
async function runPi(
	args: string[],
	prompt: string,
	notify: (msg: string, type?: "info" | "warning" | "error") => void,
): Promise<PiRun> {
	const argv = [...resolvePiCommand(), ...args, "-a", "--no-session", "--print", prompt];
	try {
		const { stdout, stderr } = await execFileAsync(argv[0], argv.slice(1), {
			timeout: TIMEOUT_MS,
			maxBuffer: 32 * 1024 * 1024,
			cwd: process.cwd(),
			env: { ...process.env, PI_ORCHESTRATOR_ACTIVE: "1" },
		});
		return { ok: true, text: stdout.trim(), stderr: stderr.trim() };
	} catch (err: any) {
		if (err?.killed || err?.signal === "SIGTERM") {
			notify("phase timed out; aborting pipeline", "error");
			return { ok: false, text: "", stderr: `timed out after ${TIMEOUT_MS}ms` };
		}
		return {
			ok: false,
			text: String(err?.stdout ?? "").trim(),
			stderr: String(err?.stderr ?? err?.message ?? "").trim(),
		};
	}
}

function modelArg(model: string | undefined, thinking?: string): string[] {
	const flags: string[] = [];
	if (model) flags.push("--model", model);
	if (thinking) flags.push("--thinking", thinking);
	return flags;
}

// ---------- task graph (validated as plain data, like FC29-32 validate LLM output) ----------

interface Task {
	id: string;
	title: string;
	description: string;
	files: string[];
	context_files: string[];
	fc_ids: string[];
	depends_on: string[];
	skill?: string;
}

interface TaskGraph {
	objective: string;
	fc_ids: string[];
	tasks: Task[];
}

function parseTaskGraph(raw: string): TaskGraph {
	let text = raw.trim();
	// Defensive extraction: strip markdown fences, then take the outermost JSON object.
	const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
	if (fenced && fenced[1]?.trim().startsWith("{")) text = fenced[1];
	const start = text.indexOf("{");
	const end = text.lastIndexOf("}");
	if (start === -1 || end === -1 || end <= start) throw new Error("architect returned no JSON object");
	let graph: unknown;
	try {
		graph = JSON.parse(text.slice(start, end + 1));
	} catch (e) {
		throw new Error(`architect JSON unparseable: ${(e as Error).message}`);
	}
	const g = graph as Partial<TaskGraph>;
	if (typeof g.objective !== "string" || !g.objective.trim()) throw new Error("task graph: missing objective");
	if (!Array.isArray(g.tasks) || g.tasks.length === 0) throw new Error("task graph: no tasks");
	if (g.tasks.length > MAX_TASKS) throw new Error(`task graph: ${g.tasks.length} tasks exceeds max ${MAX_TASKS}`);

	const ids = new Set<string>();
	for (const t of g.tasks as Task[]) {
		for (const key of ["id", "title", "description"] as const) {
			if (typeof t[key] !== "string" || !(t[key] as string).trim()) throw new Error(`task graph: missing ${key}`);
		}
		if (typeof t.id !== "string") throw new Error("task graph: id not a string");
		if (ids.has(t.id)) throw new Error(`task graph: duplicate id ${t.id}`);
		ids.add(t.id);
		for (const arrKey of ["files", "context_files", "fc_ids", "depends_on"] as const) {
			if (!Array.isArray(t[arrKey]) || (t[arrKey] as string[]).some((s) => typeof s !== "string")) {
				throw new Error(`task graph ${t.id}: ${arrKey} must be a string array`);
			}
		}
		if (t.files.length === 0 && t.skill === undefined) {
			throw new Error(`task graph ${t.id}: no files and no skill — task touches nothing`);
		}
	}
	for (const t of g.tasks as Task[]) {
		for (const dep of t.depends_on) {
			if (!ids.has(dep)) throw new Error(`task graph: ${t.id} depends on unknown task ${dep}`);
		}
	}
	// Cycle check via Kahn's algorithm (also produces execution order).
	const remainingDeps = new Map((g.tasks as Task[]).map((t) => [t.id, new Set(t.depends_on)]));
	const order: string[] = [];
	while (remainingDeps.size > 0) {
		const ready = [...remainingDeps.entries()].filter(([, deps]) => deps.size === 0).map(([id]) => id);
		if (ready.length === 0) throw new Error("task graph: dependency cycle detected");
		for (const id of ready) {
			remainingDeps.delete(id);
			order.push(id);
			for (const deps of remainingDeps.values()) deps.delete(id);
		}
	}
	return { objective: g.objective, fc_ids: g.fc_ids ?? [], tasks: g.tasks as Task[] };
}

function topoOrder(tasks: Task[]): Task[] {
	const done = new Set<string>();
	const out: Task[] = [];
	while (out.length < tasks.length) {
		let progress = false;
		for (const t of tasks) {
			if (done.has(t.id)) continue;
			if (t.depends_on.every((d) => done.has(d))) {
				done.add(t.id);
				out.push(t);
				progress = true;
			}
		}
		if (!progress) throw new Error("dependency cycle detected at runtime"); // unreachable post-parse
	}
	return out;
}

// ---------- prompts ----------

const PLANNER_PROMPT = (feature: string) => `
You are the planning phase of an automated build pipeline for the Academic AI Advisor repo.
FIRST read: AGENTS.md, docs/2026-10-18-functional-requirements.md, docs/2026-10-18-ai-advisor-domain-model.md — plus any
docs/ files relevant to the feature. Then decompose the feature below into tasks.

Repo rules (apply them): deterministic engine first (constraint checks FC29-FC32 and plan
generation live in plain code — CourseRecommendationValidator, DegreePlanGenerator; the LLM never
does constraint math); route structured lookups to SQLite and semantic search to Chroma (FC9, FC33);
never fabricate academic data; auth is out of scope (FC36).

Output ONLY a JSON object, no prose, no markdown fences:
{
  "objective": "one paragraph restating the feature and its FC IDs",
  "fc_ids": ["FC13"],
  "tasks": [
    {
      "id": "T1",
      "title": "short imperative title",
      "description": "what ONE worker session must do, including FC IDs",
      "files": ["src/main/AI_Assistant.py"],
      "context_files": ["docs/2026-10-18-ai-advisor-domain-model.md"],
      "fc_ids": ["FC13"],
      "depends_on": [],
      "skill": "optional advisor-domain reference"
    }
  ]
}

Constraints: max ${MAX_TASKS} tasks; task descriptions must be self-contained (workers cannot ask
questions); list every file a task may create/modify in files (empty allowed only for pure
doc/exploration tasks paired with a skill); order dependencies realistically. Do not include a
testing task or a documentation task — the pipeline adds those.

Feature: ${feature}
`.trim();

const TASK_PROMPT = (graph: TaskGraph, task: Task) => `
You are ONE implementation worker in an automated pipeline for the Academic AI Advisor repo.
Overall feature: ${graph.objective}
Relevant FCs: ${graph.fc_ids.join(", ") || "(none)"}

YOUR TASK ${task.id}: ${task.title}
${task.description}
Files you may create/modify: ${task.files.join(", ") || "(none)"}
${task.skill ? `Skill to consult: ${task.skill}` : ""}

First read AGENTS.md, .pi/APPEND_SYSTEM.md, and: ${[...new Set(["docs/2026-10-18-functional-requirements.md", ...task.context_files])].join(" ")}.
Repo rules: deterministic engine first; never fabricate academic data; cite FC IDs in code comments
where a requirement is implemented; follow existing code style; do not run destructive commands;
do NOT invoke /build; do not git-commit. Implement ONLY this task.

When finished, print exactly one final line: DONE: <one-sentence summary of what you implemented>.
On failure, print exactly one final line: FAILED: <why>.
`.trim();

const TESTER_PROMPT = (graph: TaskGraph, taskSummaries: string[]) => `
You are the verification phase of an automated pipeline for the Academic AI Advisor repo.
Feature: ${graph.objective}
Implemented by pipeline workers:
${taskSummaries.map((s) => `- ${s}`).join("\n")}

Your job (read + bash only, you CANNOT edit files):
1. Run the project's tests / type checks / linters as appropriate via bash. If no test setup exists,
   write nothing permanent; instead verify the changed files compile/parse and their structure is sane.
2. Audit the implementation against the rules in AGENTS.md, especially: constraint checks live in
   deterministic code (FC29-FC32 ownership in docs/2026-10-18-ai-advisor-domain-model.md §2); the LLM path must
   not bypass CourseRecommendationValidator or DegreePlanGenerator; no fabricated academic data.
3. Report faithfully. A failing audit is more valuable than a passing pipeline.

Your response MUST start with one of: "PASS: " or "FAIL: " followed by a short verdict, then a
bulleted evidence list (commands run, files inspected).
`.trim();

const DOCS_PROMPT = (graph: TaskGraph, taskSummaries: string[], testSummary: string) => `
You are the documentation phase of an automated pipeline for the Academic AI Advisor repo.
Feature: ${graph.objective}
Tasks completed:
${taskSummaries.map((s) => `- ${s}`).join("\n")}
Verification result: ${testSummary}

Update ONLY docs/implementation-log.md (create it with a "# Implementation Log" header if missing):
append today's date and entries for this feature — what was implemented, files touched, FC IDs
implemented, and test outcome. Do NOT modify docs/2026-10-18-functional-requirements.md, docs/2026-10-18-ai-advisor-domain-model.md,
AGENTS.md, or any source file. If the feature implies a domain-model class gap, note it in the log
entry instead of editing the model doc.
`.trim();

// ---------- command ----------

export default function (pi: ExtensionAPI) {
	pi.registerCommand("build", {
		description: "Deterministic pipeline: plan (strong model) → implement per-task → test → document",
		handler: async (args: string, ctx: ExtensionCommandContext) => {
			const notify = (msg: string, type: "info" | "warning" | "error" = "info") => ctx.ui.notify(msg, type);
			const feature = args.trim();

			if (process.env.PI_ORCHESTRATOR_ACTIVE === "1") {
				notify("pipeline invoked via /build is not allowed inside pipeline workers", "error");
				return;
			}
			if (!feature) {
				notify("usage: /build <feature description>", "warning");
				return;
			}
			if (feature.length > 2000) {
				notify("feature description too long (max 2000 chars)", "warning");
				return;
			}

			try {
				const fileCfg = readPipelineConfig();

				// ---- Phase 1: architect / planner ----
				notify(`① architecture & task graph: planning "${feature}" …`);
				const plan = await runPi(
					["--tools", "read,grep,find,ls", ...modelArg(resolveModel(process.env.PI_BUILD_ARCHITECT_MODEL, "architectModel", fileCfg), "high")],
					PLANNER_PROMPT(feature),
					notify,
				);
				if (!plan.ok || !plan.text) {
					notify(`① planning failed${plan.stderr ? `: ${plan.stderr.slice(0, 400)}` : ""}`, "error");
					return;
				}
				let graph: TaskGraph;
				try {
					graph = parseTaskGraph(plan.text);
				} catch (e) {
					notify(`① rejected architect output: ${(e as Error).message}`, "error");
					return;
				}
				notify(`① ${graph.tasks.length} task(s) planned: ${graph.tasks.map((t) => t.id).join(", ")}`);

				// ---- Phase 2: one worker per task, dependency order, sequential ----
				const summaries: string[] = [];
				for (const task of topoOrder(graph.tasks)) {
					notify(`② ${task.id}/${graph.tasks.length}: ${task.title} …`);
					const result = await runPi(
						["--tools", "read,bash,edit,write", ...modelArg(resolveModel(process.env.PI_BUILD_WORKER_MODEL, "workerModel", fileCfg))],
						TASK_PROMPT(graph, task),
						notify,
					);
					const text = result.text || "";
					const failed = !result.ok || /^FAILED:/m.test(text);
					const line = (text.match(/^(?:DONE|FAILED):.*$/m)?.[0] ?? text.slice(0, 120)).trim();
					if (failed) {
						notify(`② ${task.id} failed: ${line}${result.stderr ? ` | ${result.stderr.slice(0, 400)}` : ""}`, "error");
						notify("pipeline stopped before testing; nothing was verified", "warning");
						return;
					}
					summaries.push(`${task.id} (${task.title}): ${line}`);
					notify(`② ${task.id} done — ${line}`);
				}

				// ---- Phase 3: tester (fresh context, read+run only) ----
				notify("③ verification: running tests & FC29-FC32 audit …");
				const test = await runPi(
					["--tools", "bash,read,grep,find,ls", ...modelArg(resolveModel(process.env.PI_BUILD_TESTER_MODEL, "testerModel", fileCfg))],
					TESTER_PROMPT(graph, summaries),
					notify,
				);
				const verdict = test.text.slice(0, 200).replace(/\n/g, " ") || "(empty)";
				if (!test.ok || !test.text.startsWith("PASS:")) {
					notify(`③ verification FAILED — ${verdict}`, "error");
					notify("pipeline stopped before documentation; fix and re-run /build", "warning");
					return;
				}
				notify(`③ ${verdict}`);

				// ---- Phase 4: doc writer (docs log only) ----
				notify("④ updating docs/implementation-log.md …");
				const docs = await runPi(
					["--tools", "read,edit", ...modelArg(resolveModel(process.env.PI_BUILD_DOCS_MODEL, "docsModel", fileCfg))],
					DOCS_PROMPT(graph, summaries, verdict),
					notify,
				);
				if (!docs.ok) {
					notify(`④ documentation failed: ${docs.stderr.slice(0, 400)}`, "warning");
				} else {
					notify("④ docs updated");
				}

				notify(
					`✔ /build complete: ${graph.tasks.length} task(s), tests PASS, docs logged.\n` +
						`Feature: ${feature}\nReview the diff before committing (git diff && git status).`,
					"info",
				);
			} catch (err) {
				notify(`/build pipeline error: ${(err as Error)?.message ?? String(err)}`, "error");
			}
		},
	});
}