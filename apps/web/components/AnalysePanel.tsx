"use client";

import { type FormEvent, type KeyboardEvent, useEffect, useId, useRef, useState } from "react";

import { ResultView } from "@/components/ResultView";
import { type AnalyzeFn, type AnalyzeResult, ApiError, analyzeText } from "@/lib/api";
import { MAX_CHARS } from "@/lib/labels";
import { countChars, detectScript, format } from "@/lib/text";
import messages from "@/messages/en.json";

type State =
  | { kind: "idle" }
  | { kind: "loading"; slow: boolean }
  | { kind: "result"; result: AnalyzeResult }
  | { kind: "error"; message: string };

/** After this long without an answer we explain the cold start (NFR-02). */
export const SLOW_AFTER_MS = 1500;

function errorMessage(error: unknown): string {
  const known = messages.errors as Record<string, string>;
  if (error instanceof ApiError && error.code in known) return known[error.code] ?? known.default!;
  return messages.errors.default;
}

export function AnalysePanel({ analyze = analyzeText }: { analyze?: AnalyzeFn }) {
  const [text, setText] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });
  const inFlight = useRef<AbortController | null>(null);
  const inputId = useId();
  const hintId = useId();

  const length = countChars(text);
  const over = length - MAX_CHARS;
  const canSubmit = length > 0 && over <= 0 && state.kind !== "loading";

  useEffect(() => () => inFlight.current?.abort(), []);

  async function run(value: string) {
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    setState({ kind: "loading", slow: false });
    const slowTimer = setTimeout(() => {
      if (!controller.signal.aborted) setState({ kind: "loading", slow: true });
    }, SLOW_AFTER_MS);
    try {
      const result = await analyze(value, { signal: controller.signal });
      if (!controller.signal.aborted) setState({ kind: "result", result });
    } catch (error) {
      if (!controller.signal.aborted) setState({ kind: "error", message: errorMessage(error) });
    } finally {
      clearTimeout(slowTimer);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (canSubmit) void run(text);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && canSubmit) {
      event.preventDefault();
      void run(text);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={onSubmit} className="space-y-3">
        <label htmlFor={inputId} className="block font-medium">
          {messages.analyse.inputLabel}
        </label>
        <textarea
          id={inputId}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={messages.analyse.placeholder}
          aria-describedby={hintId}
          aria-invalid={over > 0}
          rows={4}
          className="border-border bg-surface focus-visible:outline-accent w-full rounded-xl border p-3 text-base focus-visible:outline-2"
        />
        <div
          id={hintId}
          className="text-muted flex flex-wrap items-center justify-between gap-2 text-sm"
        >
          <span>
            {length > 0 ? (
              <span className="border-border mr-2 rounded-full border px-2 py-0.5">
                {messages.script[detectScript(text)]}
              </span>
            ) : null}
            <span className="hidden sm:inline">{messages.analyse.shortcut}</span>
          </span>
          <span className="tabular-nums" role={over > 0 ? "alert" : undefined}>
            {over > 0
              ? format(messages.analyse.tooLong, { count: over })
              : `${length}/${MAX_CHARS}`}
          </span>
        </div>

        <fieldset>
          <legend className="text-muted mb-1 text-sm">{messages.analyse.examplesLabel}</legend>
          <div className="flex flex-wrap gap-2">
            {messages.examples.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => setText(example)}
                className="border-border bg-surface min-h-11 rounded-full border px-3 text-left text-sm"
              >
                {example}
              </button>
            ))}
          </div>
        </fieldset>

        <button
          type="submit"
          disabled={!canSubmit}
          className="bg-accent text-accent-text min-h-11 w-full rounded-xl px-5 font-semibold disabled:opacity-50 sm:w-auto"
        >
          {state.kind === "loading" ? messages.analyse.loading : messages.analyse.button}
        </button>
      </form>

      <div aria-live="polite" aria-busy={state.kind === "loading"}>
        {state.kind === "loading" && state.slow ? (
          <p className="text-muted">{messages.analyse.coldStart}</p>
        ) : null}
        {state.kind === "error" ? (
          <div role="alert" className="border-border bg-surface rounded-xl border p-4">
            <p>{state.message}</p>
            <button
              type="button"
              onClick={() => void run(text)}
              disabled={length === 0 || over > 0}
              className="text-accent mt-2 min-h-11 underline underline-offset-4 disabled:opacity-50"
            >
              {messages.errors.retry}
            </button>
          </div>
        ) : null}
        {state.kind === "result" ? <ResultView result={state.result} /> : null}
      </div>
    </div>
  );
}
