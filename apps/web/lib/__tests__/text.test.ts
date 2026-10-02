import { describe, expect, it } from "vitest";

import { labelInfo, LABELS, MAX_CHARS, NEUTRAL } from "@/lib/labels";
import { countChars, detectScript, format, percent } from "@/lib/text";

describe("countChars", () => {
  it("counts code points, so an emoji is one character like in the API", () => {
    expect("😂".length).toBe(2);
    expect(countChars("😂")).toBe(1);
    expect(countChars("😂".repeat(1000))).toBe(1000);
  });

  it("ignores leading and trailing whitespace like the API does", () => {
    expect(countChars("  yaar  ")).toBe(4);
    expect(countChars("   ")).toBe(0);
  });

  it("counts Devanagari by code point", () => {
    expect(countChars("खुश")).toBe(3);
  });
});

describe("detectScript", () => {
  // The same cases as test_detect_script in ml/tests/test_lid.py.
  it.each([
    ["yaar aaj bahut khush hu", "roman"],
    ["सच में बहुत खुश हूँ आज", "devanagari"],
    ["बहुत khush हूँ yaar", "mixed"],
    ["खुशhoon", "mixed"],
    ["😂😂 !!", "roman"],
    ["", "roman"],
    ["१२३ बजे", "devanagari"],
  ])("%s → %s", (text, script) => {
    expect(detectScript(text)).toBe(script);
  });
});

describe("format and percent", () => {
  it("fills placeholders and leaves unknown ones alone", () => {
    expect(format("CMI {cmi} · {hi}% Hindi", { cmi: 46, hi: 58 })).toBe("CMI 46 · 58% Hindi");
    expect(format("{missing} stays", {})).toBe("{missing} stays");
  });

  it("rounds probabilities to whole percentages", () => {
    expect(percent(0.82)).toBe(82);
    expect(percent(0.005)).toBe(1);
    expect(percent(0)).toBe(0);
  });
});

describe("labels from the generated schema", () => {
  it("has the seven labels in model order", () => {
    expect(LABELS).toEqual(["anger", "disgust", "fear", "joy", "sadness", "surprise", "neutral"]);
    expect(NEUTRAL).toBe("neutral");
    expect(MAX_CHARS).toBe(1000);
  });

  it("gives display data for every label", () => {
    for (const label of LABELS) {
      const info = labelInfo(label);
      expect(info.emoji).not.toBe("");
      expect(info.hinglish).not.toBe("");
      expect(info.description).not.toBe("");
    }
    expect(labelInfo("sadness")).toMatchObject({ name: "Sadness", hinglish: "Dukh", emoji: "😢" });
  });
});
