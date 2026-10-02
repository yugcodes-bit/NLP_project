/**
 * Label display data. It comes from configs/label_schema.yaml through the generated JSON, so the
 * web app can never disagree with the model about which labels exist.
 */
import schema from "@/lib/generated/label-schema.json";
import normalization from "@/lib/generated/normalization.json";

export const LABELS: readonly string[] = schema.labels;
export const NEUTRAL: string = schema.neutral_label;
export const MAX_CHARS: number = normalization.max_chars;

const emoji: Record<string, string> = schema.ui.emoji;
const hinglish: Record<string, string> = schema.ui.hinglish_name;
const descriptions: Record<string, string> = schema.descriptions;

export interface LabelInfo {
  label: string;
  /** English name, capitalised: "Sadness". */
  name: string;
  /** Hinglish name: "Dukh". */
  hinglish: string;
  emoji: string;
  description: string;
}

export function labelInfo(label: string): LabelInfo {
  return {
    label,
    name: label.charAt(0).toUpperCase() + label.slice(1),
    hinglish: hinglish[label] ?? label,
    emoji: emoji[label] ?? "",
    description: descriptions[label] ?? "",
  };
}
