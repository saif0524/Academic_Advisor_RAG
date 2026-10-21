/**
 * Display helper shared by planner/search/chat components (not a component —
 * no CSS/story needed). Seed corpus titles are stored uppercase
 * (data/course-desc.jsonl); they are displayed in title case per product
 * convention. Keep original casing for acronyms ("cse" → "CSE", "iot" → "IoT")
 * — plain title-casing would mangle them.
 */
const SMALL_WORDS = new Set([
  'a', 'an', 'the', 'and', 'or', 'for', 'to', 'in', 'of', 'on', 'with', 'via',
]);
const DISPLAY_ACRONYMS: Record<string, string> = { cse: 'CSE', iot: 'IoT', 'c++': 'C++', soc: 'SoC', sql: 'SQL' };

function displayWord(word: string, isFirst: boolean): string {
  const acronym = DISPLAY_ACRONYMS[word];
  if (acronym) return acronym;
  if (!isFirst && SMALL_WORDS.has(word)) return word;
  return word.replace(/(^|[-/])(\w)/g, (_, separator: string, letter: string) => separator + letter.toUpperCase());
}

/** "INFORMATION SECURITY" → "Information Security"; leaves acronyms intact. */
export function toTitleCase(title: string): string {
  return String(title)
    .trim()
    .replace(/\.$/, '')
    .toLowerCase()
    .split(/\s+/)
    .map((word, index) => displayWord(word, index === 0))
    .join(' ');
}