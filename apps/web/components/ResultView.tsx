"use client";

import { useState } from "react";

import { CodeMixLens } from "@/components/CodeMixLens";
import { type BarItem, EmotionBars } from "@/components/EmotionBars";
import { UnsureCard } from "@/components/UnsureCard";
import type { AnalyzeResult } from "@/lib/api";
import { LABELS } from "@/lib/labels";
import { format, hasDevanagari } from "@/lib/text";
import messages from "@/messages/en.json";

const DUMMY_PREFIX = "bhaav-dummy";

function allScores(result: AnalyzeResult): BarItem[] {
  const intensity = new Map(result.emotions.map((e) => [e.label, e.intensity]));
  return LABELS.filter((label) => result.scores !== null && label in result.scores).map(
    (label) => ({
      label,
      probability: result.scores?.[label] ?? 0,
      intensity: intensity.get(label) ?? null,
    }),
  );
}

export function ResultView({ result }: { result: AnalyzeResult }) {
  const [showAll, setShowAll] = useState(false);
  const isDummy = result.model_version.startsWith(DUMMY_PREFIX);

  return (
    <div className="space-y-5">
      {isDummy ? (
        <p role="note" className="bg-warn-bg text-warn-text rounded-lg px-3 py-2 text-sm">
          <strong>{messages.dummy.title}.</strong> {messages.dummy.body}
        </p>
      ) : null}

      <section aria-labelledby="results-heading">
        <h2 id="results-heading" className="mb-3 text-lg font-semibold">
          {messages.analyse.resultsHeading}
        </h2>
        {result.abstained ? (
          <UnsureCard candidates={result.candidates ?? []} />
        ) : (
          <EmotionBars items={result.emotions} />
        )}

        {result.scores !== null ? (
          <div className="mt-3">
            <button
              type="button"
              aria-expanded={showAll}
              onClick={() => setShowAll((open) => !open)}
              className="text-accent min-h-11 text-sm underline underline-offset-4"
            >
              {showAll ? messages.analyse.hideAll : messages.analyse.showAll}
            </button>
            {showAll ? (
              <div className="mt-2" aria-label={messages.analyse.allScoresHeading} role="group">
                <EmotionBars items={allScores(result)} />
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

      {result.lid !== null ? <CodeMixLens lid={result.lid} /> : null}

      <section aria-labelledby="normalised-heading" className="text-sm">
        <h3 id="normalised-heading" className="text-muted">
          {messages.analyse.normalisedHeading}
        </h3>
        <p lang={hasDevanagari(result.text_normalized) ? "hi" : undefined} className="break-words">
          {result.text_normalized}
        </p>
      </section>

      <p className="text-muted text-sm">
        {format(messages.analyse.confidence, { value: result.confidence.toFixed(2) })}
        {" · "}
        {format(messages.analyse.meta, { version: result.model_version, ms: result.latency_ms })}
      </p>
    </div>
  );
}
