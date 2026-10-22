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

const ROMAN_NUMERALS = new Set(['ii', 'iii', 'iv', 'vi', 'vii']);

function displayWord(word: string, isFirst: boolean): string {
  const acronym = DISPLAY_ACRONYMS[word];
  if (acronym) return acronym;
  if (ROMAN_NUMERALS.has(word)) return word.toUpperCase();
  if (!isFirst && SMALL_WORDS.has(word)) return word;
  return word.replace(/(^|[-/])(\w)/g, (_, separator: string, letter: string) => separator + letter.toUpperCase());
}

/**
 * Display code for a canonical course id: catalog-backed CSE courses are
 * stored as 4-digit corpus ids ("3310" → "CSE 3310"); every other id is
 * already a full code ("HIST 1311") and is returned unchanged.
 */
export function formatCourseCode(id: string): string {
  return /^\d{4}$/.test(id) ? `CSE ${id}` : id;
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