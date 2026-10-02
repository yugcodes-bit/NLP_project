import { IntensityDots } from "@/components/IntensityDots";
import { labelInfo } from "@/lib/labels";
import { percent } from "@/lib/text";

export interface BarItem {
  label: string;
  probability: number;
  intensity: number | null;
}

function isLevel(value: number | null): value is 1 | 2 | 3 {
  return value === 1 || value === 2 || value === 3;
}

/** One row per emotion: emoji, name, Hinglish name, bar, percentage, intensity. */
export function EmotionBars({ items }: { items: BarItem[] }) {
  return (
    <ul className="space-y-3">
      {items.map((item) => {
        const info = labelInfo(item.label);
        const value = percent(item.probability);
        return (
          <li key={item.label} data-testid={`emotion-${item.label}`}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-medium">
                <span aria-hidden="true">{info.emoji} </span>
                {info.name}
                {info.hinglish !== info.name ? (
                  <span className="text-muted text-sm font-normal"> {info.hinglish}</span>
                ) : null}
              </span>
              <span className="flex items-baseline gap-3">
                {isLevel(item.intensity) ? <IntensityDots level={item.intensity} /> : null}
                <span className="tabular-nums">{value}%</span>
              </span>
            </div>
            <div aria-hidden="true" className="bg-track mt-1 h-2.5 overflow-hidden rounded-full">
              <div
                className="emotion-bar h-full rounded-full"
                style={{ width: `${value}%`, background: `var(--emo-${item.label})` }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
