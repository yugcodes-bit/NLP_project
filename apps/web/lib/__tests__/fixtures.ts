import type { AnalyzeResult } from "@/lib/api";

/** The example response from docs/14_api_contract.md, field for field. */
export const CONTRACT_EXAMPLE = {
  text_normalized: "yaar aaj ka din bahut bekaar tha 😩",
  script: "roman",
  emotions: [
    { label: "sadness", probability: 0.82, active: true, intensity: 3 },
    { label: "anger", probability: 0.31, active: true, intensity: 1 },
  ],
  scores: {
    anger: 0.31,
    disgust: 0.04,
    fear: 0.06,
    joy: 0.02,
    sadness: 0.82,
    surprise: 0.03,
    neutral: 0.05,
  },
  top: "sadness",
  abstained: false,
  candidates: null,
  confidence: 0.82,
  lid: {
    tokens: [
      { text: "yaar", lang: "hi" },
      { text: "aaj", lang: "hi" },
      { text: "ka", lang: "hi" },
      { text: "din", lang: "hi" },
      { text: "bahut", lang: "hi" },
      { text: "bekaar", lang: "hi" },
      { text: "tha", lang: "hi" },
      { text: "😩", lang: "univ" },
    ],
    cmi: 0.0,
    lang_share: { hi: 1.0, en: 0.0 },
  },
  explanation: {
    target: "sadness",
    method: "occlusion",
    words: [
      { text: "bekaar", score: 0.41 },
      { text: "😩", score: 0.22 },
      { text: "bahut", score: 0.08 },
    ],
  },
  wellbeing: { show: false },
  model_version: "bhaav-teacher-1.0.0",
  mode: "server",
  latency_ms: 94,
} satisfies AnalyzeResult;

export const UNSURE_EXAMPLE = {
  ...CONTRACT_EXAMPLE,
  emotions: [],
  top: null,
  abstained: true,
  candidates: [
    { label: "fear", probability: 0.35 },
    { label: "surprise", probability: 0.32 },
  ],
  confidence: 0.35,
  explanation: null,
} satisfies AnalyzeResult;

export const NEUTRAL_DUMMY_EXAMPLE = {
  ...CONTRACT_EXAMPLE,
  emotions: [{ label: "neutral", probability: 0.83, active: true, intensity: null }],
  top: "neutral",
  confidence: 0.83,
  lid: null,
  explanation: null,
  model_version: "bhaav-dummy-0.1.0",
} satisfies AnalyzeResult;
