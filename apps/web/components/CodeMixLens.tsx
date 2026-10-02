import type { AnalyzeResult, Lang } from "@/lib/api";
import { format, hasDevanagari } from "@/lib/text";
import messages from "@/messages/en.json";

type Lid = NonNullable<AnalyzeResult["lid"]>;

const UNDERLINE: Record<Lang, string> = {
  hi: "lang-hi",
  en: "lang-en",
  univ: "",
  ne: "lang-ne",
  other: "lang-other",
};

/**
 * Each word with its language tag (docs/13 §1). The tag is printed under the word as text, so
 * the underline colour is decoration, not the only signal.
 */
export function CodeMixLens({ lid }: { lid: Lid }) {
  const summary = format(messages.codeMix.summary, {
    cmi: Math.round(lid.cmi),
    hi: Math.round((lid.lang_share.hi ?? 0) * 100),
    en: Math.round((lid.lang_share.en ?? 0) * 100),
  });
  return (
    <section aria-labelledby="code-mix-heading">
      <h3 id="code-mix-heading" className="font-semibold">
        {messages.codeMix.heading}
      </h3>
      <p className="text-muted text-sm" title={messages.codeMix.cmiHelp}>
        {summary}
      </p>
      <ol className="mt-2 flex flex-wrap gap-x-3 gap-y-2">
        {lid.tokens.map((token, index) => (
          <li key={index} className="flex flex-col items-center">
            <span
              lang={hasDevanagari(token.text) ? "hi" : undefined}
              className={UNDERLINE[token.lang]}
            >
              {token.text}
            </span>
            <span className="text-muted text-xs" title={messages.codeMix.lang[token.lang]}>
              {token.lang}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
