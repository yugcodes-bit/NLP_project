/** Small text helpers that must agree with the API. */

export type Script = "roman" | "devanagari" | "mixed";

/**
 * Length as the API counts it: Unicode code points of the trimmed text, so one emoji is one
 * character. (`string.length` counts UTF-16 units and would call most emoji two.)
 */
export function countChars(text: string): number {
  return Array.from(text.trim()).length;
}

const DEVANAGARI = /\p{Script=Devanagari}/u;
const LATIN = /\p{Script=Latin}/u;

/** Same rule as `script_of` in ml/src/bhaav/data/lid.py: no Devanagari at all means "roman". */
export function detectScript(text: string): Script {
  const hasDevanagari = DEVANAGARI.test(text);
  if (hasDevanagari && LATIN.test(text)) return "mixed";
  return hasDevanagari ? "devanagari" : "roman";
}

export function hasDevanagari(text: string): boolean {
  return DEVANAGARI.test(text);
}

/** Fill `{name}` placeholders in a message string. */
export function format(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in values ? String(values[key]) : match,
  );
}

export function percent(probability: number): number {
  return Math.round(probability * 100);
}
