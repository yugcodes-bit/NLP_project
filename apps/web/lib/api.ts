/**
 * Typed client for the Bhaav API. The schemas mirror docs/14_api_contract.md and are the single
 * `AnalyzeResult` type the UI consumes, in Server mode now and Privacy Mode later.
 */
import { z } from "zod";

export const LANGS = ["hi", "en", "univ", "ne", "other"] as const;
export type Lang = (typeof LANGS)[number];

const emotionSchema = z.object({
  label: z.string(),
  probability: z.number().min(0).max(1),
  active: z.boolean(),
  intensity: z.number().int().min(1).max(3).nullable(),
});

const candidateSchema = z.object({
  label: z.string(),
  probability: z.number().min(0).max(1),
});

const lidSchema = z.object({
  tokens: z.array(z.object({ text: z.string(), lang: z.enum(LANGS) })),
  cmi: z.number().min(0).max(100),
  lang_share: z.record(z.string(), z.number()),
});

const explanationSchema = z.object({
  target: z.string(),
  method: z.literal("occlusion"),
  words: z.array(z.object({ text: z.string(), score: z.number() })),
});

export const analyzeResultSchema = z.object({
  text_normalized: z.string(),
  script: z.enum(["roman", "devanagari", "mixed"]),
  emotions: z.array(emotionSchema),
  scores: z.record(z.string(), z.number()).nullable(),
  top: z.string().nullable(),
  abstained: z.boolean(),
  candidates: z.array(candidateSchema).nullable(),
  confidence: z.number().min(0).max(1),
  lid: lidSchema.nullable(),
  explanation: explanationSchema.nullable(),
  wellbeing: z.object({ show: z.boolean() }),
  model_version: z.string(),
  mode: z.enum(["server", "browser"]),
  latency_ms: z.number(),
});

export type AnalyzeResult = z.infer<typeof analyzeResultSchema>;
export type Emotion = z.infer<typeof emotionSchema>;

const problemSchema = z.object({
  title: z.string(),
  status: z.number(),
  detail: z.string(),
  code: z.string(),
});

/** An error the UI can show. `code` is an API error code, or NETWORK / BAD_RESPONSE. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number | null;

  constructor(code: string, status: number | null, message: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

/** A cancelled request. Checked by name: `instanceof DOMException` fails across realms. */
function isAbort(error: unknown): boolean {
  return (
    typeof error === "object" && error !== null && "name" in error && error.name === "AbortError"
  );
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export interface AnalyzeOptions {
  signal?: AbortSignal;
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}

export type AnalyzeFn = (text: string, options?: AnalyzeOptions) => Promise<AnalyzeResult>;

export const analyzeText: AnalyzeFn = async (text, options = {}) => {
  const { signal, baseUrl = API_URL, fetchImpl = fetch } = options;

  let response: Response;
  try {
    response = await fetchImpl(`${baseUrl}/v1/analyze`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, options: { explain: false, lid: true, all_scores: true } }),
      signal,
    });
  } catch (error) {
    if (isAbort(error)) throw error;
    throw new ApiError("NETWORK", null, "network request failed");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError("BAD_RESPONSE", response.status, "response was not JSON");
  }

  if (!response.ok) {
    const problem = problemSchema.safeParse(payload);
    if (problem.success) {
      throw new ApiError(problem.data.code, response.status, problem.data.detail);
    }
    throw new ApiError("BAD_RESPONSE", response.status, "unrecognised error response");
  }

  const result = analyzeResultSchema.safeParse(payload);
  if (!result.success) {
    throw new ApiError("BAD_RESPONSE", response.status, "response did not match the contract");
  }
  return result.data;
};
