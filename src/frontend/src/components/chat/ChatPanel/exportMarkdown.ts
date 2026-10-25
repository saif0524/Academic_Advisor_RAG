import type { ChatMessage, StreamCheck } from '../../../api/types';

/** Status words/icons used in the exported transcript (FC24, FC29–FC32, FC39). */
const STATUS: Record<'pass' | 'fail' | 'skip', string> = {
  pass: '✅ passed',
  fail: '❌ failed',
  skip: '❔ skipped (data not on record)',
};

function statusOf(check: StreamCheck): 'pass' | 'fail' | 'skip' {
  if (check.passed === true) return 'pass';
  if (check.passed === false) return 'fail';
  return 'skip';
}

/** Keep table cells on one line and keep literal pipes from breaking the table. */
function cell(text: string | null | undefined): string {
  return (text ?? '').replace(/\s*\n\s*/g, ' ').replace(/\|/g, '\\|').trim() || '—';
}

function checksSection(checks: StreamCheck[]): string[] {
  const validator = checks.filter((c) => c.kind === 'check');
  const steps = checks.filter((c) => c.kind === 'step');
  const lines: string[] = [];
  if (validator.length) {
    const counts = { pass: 0, fail: 0, skip: 0 };
    validator.forEach((c) => { counts[statusOf(c)] += 1; });
    lines.push(
      `**Deterministic checks run (${validator.length}): ` +
      `${counts.pass} passed · ${counts.fail} failed · ${counts.skip} skipped**`,
      '',
      '| Course | Check | Status | Reason |',
      '| --- | --- | --- | --- |',
      ...validator.map((c) =>
        `| ${cell(c.course)} | ${cell(c.checkId)}: ${cell(c.description)} | ${STATUS[statusOf(c)]} | ${cell(c.reason)} |`),
      '',
    );
  }
  if (steps.length) {
    lines.push('Data lookups:', ...steps.map((s) => `- ${s.description}`), '');
  }
  return lines;
}

export interface ExportMeta {
  sessionId?: string | null;
  exportedAt?: Date;
}

/**
 * Render a conversation as Markdown for graders and advisors: every turn in
 * order, plus — under each advisor turn — the deterministic checks that ran and
 * their status (✅ passed, ❌ failed, ❔ skipped). Pure function; no I/O.
 */
export function chatToMarkdown(messages: ChatMessage[], meta: ExportMeta = {}): string {
  const when = (meta.exportedAt ?? new Date()).toISOString();
  const allChecks = messages.flatMap((m) => (m.checks ?? []).filter((c) => c.kind === 'check'));
  const failed = allChecks.filter((c) => c.passed === false).length;
  const skipped = allChecks.filter((c) => c.passed === null).length;

  const lines: string[] = [
    '# Academic AI Advisor — chat transcript',
    '',
    `- Exported: ${when}`,
    ...(meta.sessionId ? [`- Session: \`${meta.sessionId}\``] : []),
    `- Turns: ${messages.length}`,
    `- Deterministic checks across the conversation: ${allChecks.length} ` +
      `(${allChecks.length - failed - skipped} passed, ${failed} failed, ${skipped} skipped)`,
    '',
    '---',
    '',
  ];
  messages.forEach((message, index) => {
    const speaker = message.role === 'user' ? 'Student' : 'Advisor';
    lines.push(`## ${index + 1}. ${speaker}${message.createdAt ? ` — ${message.createdAt}` : ''}`, '');
    lines.push(message.text.trim() || '_(no text)_', '');
    if (message.checks?.length) lines.push(...checksSection(message.checks));
    if (message.action) {
      lines.push(
        `> **Action proposed (needs the student's confirmation):** ${message.action.summary}` +
          (message.action.actionId ? ` (\`${message.action.actionId}\`)` : ''),
        '',
      );
    }
  });
  return `${lines.join('\n').trimEnd()}\n`;
}

/** Browser download of a text file (used by the chat drawer's Export button). */
export function downloadTextFile(filename: string, text: string, mime = 'text/markdown'): void {
  const url = URL.createObjectURL(new Blob([text], { type: `${mime};charset=utf-8` }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function exportFilename(date: Date = new Date()): string {
  const stamp = date.toISOString().slice(0, 19).replace(/[:T]/g, '-');
  return `advisor-chat-${stamp}.md`;
}
