/**
 * /architect — scoping & documentation command (NO source-code changes).
 *
 * Runs ONE isolated `pi --print` subprocess on a stronger model to:
 *   1. Ground itself in the project docs (FRs, domain model, log).
 *   2. Scope the feature: affected layers/FCs, options with pros/cons, recommendation.
 *   3. Write the analysis to docs/feature-proposals/YYYY-MM-DD-<slug>.md (and, rarely,
 *      append new top-level entries to AGENTS.md repo map).
 *
 * It is deliberately headless: it cannot have a conversation. Discuss interactively in
 * your normal session first, then run /architect with the crux in the feature text —
 * or run `/architect <text> --no-write` for analysis-only, iterate on the description.
 *
 * The command itself is plain TypeScript: subprocess + post-run path gate. Violating
 * files (anything the phase wrote outside docs/) are reported, not reverted.
 *
 * Environment (all optional):
 *   PI_ARCHITECT_MODEL          model pattern (overrides the committed
 *                               .pi/pipeline.json architectModel, which is the team default)
 *   PI_ARCHITECT_TIMEOUT_MS     subprocess timeout (default: 900000)
 */

import { execFile, spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { promisify } from "node:util";
import type { ExtensionAPI, ExtensionCommandContext } from "@earendil-works/pi-coding-agent";

const execFileAsync = promisify(execFile);

const TIMEOUT_MS = Number(process.env.PI_ARCHITECT_TIMEOUT_MS ?? 900_000);

let piCommand: string[] | null = null;

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

interface ArchRun {
	ok: boolean;
	text: string;
	stderr: string;
}

async function runArchitectPi(
	args: string[],
	prompt: string,
	notify: (msg: string, type?: "info" | "warning" | "error") => void,
): Promise<ArchRun> {
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
			notify("architect phase timed out", "error");
			return { ok: false, text: "", stderr: `timed out after ${TIMEOUT_MS}ms` };
		}
		return {
			ok: false,
			text: String(err?.stdout ?? "").trim(),
			stderr: String(err?.stderr ?? err?.message ?? "").trim(),
		};
	}
}

// ---------- helpers ----------

function makeSlug(feature: string): string {
	const slug =
		feature
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, "-")
			.replace(/^-+|-+$/g, "")
			.slice(0, 48) || "untitled-feature";
	const date = new Date().toISOString().slice(0, 10);
	return `${date}-${slug}`;
}

/** Deterministic gate: verify the phase only touched whitelisted doc paths. */
function checkTouchedPaths(notify: (m: string, t?: "info" | "warning" | "error") => void): void {
	try {
		const { stdout } = spawnSync("git", ["status", "--porcelain"], { cwd: process.cwd(), timeout: 10_000 });
		const changed = stdout
			.toString()
			.split("\n")
			.map((l) => l.slice(3).trim().replace(/^"|"$/g, ""))
			.filter(Boolean);
		const allowed = ["docs/", "AGENTS.md"];
	 const unexpected = changed.filter((p) => !allowed.some((pre) => p === pre || p.startsWith(pre)));
		if (unexpected.length > 0) {
			notify(`architect wrote outside docs/ (NOT auto-reverted): ${unexpected.join(", ")}`, "warning");
		}
	} catch {
		notify("could not check git status for out-of-scope writes (git unavailable?)", "warning");
	}
}

// ---------- prompt ----------

const ARCHITECT_PROMPT = (feature: string, proposalPath: string, writeMode: boolean) => `
You are the architect of the Academic AI Advisor repo. You SCOPE and DOCUMENT — you never
write or modify source code in this phase.

## Step 1 — Ground (read before deciding anything)
Read AGENTS.md, .pi/APPEND_SYSTEM.md, docs/functional-requirements.md, docs/ai_advisor_domain_model.md,
and docs/implementation-log.md if present. Grep/read anything else needed from data/ and src/.

## Step 2 — Analyze the feature
- Scope: affected FC IDs (cite existing ones; if the feature implies NEW requirements, list them as
  "proposed: FC-new-1 …" — do NOT reword or edit existing FC rows), affected layers
  (React UI / LangChain agent / SQLite / Chroma / deterministic validator engine), and domain-model
  classes touched (new classes vs. new methods on existing ones).
- Present 2–3 viable approaches with honest pros/cons (effort, risk, how well they respect the
  deterministic-engine-first rule). Recommend one and say why in terms of the repo rules.
- List open questions the team must answer.

## Step 3 — Document ${writeMode ? "" : "(SKIPPED — analysis-only run)"}
${
	writeMode
		? `Write the full analysis to: ${proposalPath}
   Required sections: Summary; Approaches & trade-offs; Recommendation; Scope & affected layers
   (table of FCs/layers/classes); Open questions; Suggested build order (an ordered bullet list of
   implementation tasks, each citing FCs — this is the input for a later /build run).
Rules: create only that proposal file; append to AGENTS.md repo map ONLY if the feature introduces
new top-level paths; never touch docs/functional-requirements.md, docs/ai_advisor_domain_model.md,
AGENTS.md sections other than the repo map, or anything under src/, data/, or .pi/.`
		: ""
}

## Reporting (exact final lines, always)
PROPOSAL: <the proposal path, or "none">
DOCS: <comma-separated list of every file you created/modified, or "none">
`.trim();

// ---------- command ----------

export default function (pi: ExtensionAPI) {
	pi.registerCommand("architect", {
		description:
			"Scoping & docs only (stronger model): analyze feature, weigh options, write proposal to docs/feature-proposals/. Append --no-write for analysis without edits.",
		handler: async (args: string, ctx: ExtensionCommandContext) => {
			const notify = (msg: string, type: "info" | "warning" | "error" = "info") => ctx.ui.notify(msg, type);

			if (process.env.PI_ORCHESTRATOR_ACTIVE === "1") {
				notify("/architect cannot run inside pipeline workers", "error");
				return;
			}

			const writeMode = !args.includes("--no-write");
			const feature = args
				.replace(/--no-write/g, " ")
				.replace(/\s+/g, " ")
				.trim();

			if (!feature) {
				notify("usage: /architect <feature description> [--no-write]", "warning");
				return;
			}
			if (feature.length > 2000) {
				notify("feature description too long (max 2000 chars)", "warning");
				return;
			}

			const proposalPath = `docs/feature-proposals/${makeSlug(feature)}.md`;
			try {
				notify(`architect: scoping "${feature}"${writeMode ? "" : " (analysis-only)"} …`);
				const model = resolveArchitectModel();
				const result = await runArchitectPi(
					writeMode
						? ["--tools", "read,grep,find,ls,edit,write", ...modelFlags(model)]
						: ["--tools", "read,grep,find,ls", ...modelFlags(model)],
					ARCHITECT_PROMPT(feature, proposalPath, writeMode),
					notify,
				);
				if (!result.ok || !result.text) {
					notify(`architect failed${result.stderr ? `: ${result.stderr.slice(0, 400)}` : ""}`, "error");
					return;
				}

				const proposal = result.text.match(/^PROPOSAL:\s*(.+)$/m)?.[1]?.trim() ?? "none";
				const docs = result.text.match(/^DOCS:\s*(.+)$/m)?.[1]?.trim() ?? "none";
				if (writeMode) checkTouchedPaths(notify);

				notify(
					`architect complete.\nProposal: ${proposal}\nDocs touched: ${docs}\n` +
						(writeMode ? "Review the diff (git diff), then run /build with the approved feature." : "Analysis-only: no files were written."),
					"info",
				);
			} catch (err) {
				notify(`/architect error: ${(err as Error)?.message ?? String(err)}`, "error");
			}
		},
	});
}

function resolveArchitectModel(): string | undefined {
	if (process.env.PI_ARCHITECT_MODEL) return process.env.PI_ARCHITECT_MODEL;
	try {
		const raw = readFileSync(join(process.cwd(), ".pi", "pipeline.json"), "utf8");
		const parsed = JSON.parse(raw);
		if (parsed?.architectModel) return String(parsed.architectModel);
	} catch {
		// missing or unparseable config - PI_BUILD_ARCHITECT_MODEL / pi default applies
	}
	return process.env.PI_BUILD_ARCHITECT_MODEL;
}

function modelFlags(model: string | undefined): string[] {
	const flags: string[] = [];
	if (model) flags.push("--model", model);
	flags.push("--thinking", "high");
	return flags;
}