import { describe, expect, it, vi } from "vitest";

import { analyzeResultSchema, analyzeText, ApiError } from "@/lib/api";

import { CONTRACT_EXAMPLE, NEUTRAL_DUMMY_EXAMPLE, UNSURE_EXAMPLE } from "./fixtures";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

async function failure(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof ApiError) return error;
    throw error;
  }
  throw new Error("expected the call to fail");
}

describe("analyzeResultSchema", () => {
  it("accepts the example response from the API contract", () => {
    expect(analyzeResultSchema.parse(CONTRACT_EXAMPLE)).toEqual(CONTRACT_EXAMPLE);
  });

  it("accepts the unsure and neutral shapes", () => {
    expect(analyzeResultSchema.safeParse(UNSURE_EXAMPLE).success).toBe(true);
    expect(analyzeResultSchema.safeParse(NEUTRAL_DUMMY_EXAMPLE).success).toBe(true);
  });

  it("keeps fields added later by the API (additive changes are allowed in /v1)", () => {
    const parsed = analyzeResultSchema.safeParse({ ...CONTRACT_EXAMPLE, new_field: 1 });
    expect(parsed.success).toBe(true);
  });

  it.each([
    ["missing field", { ...CONTRACT_EXAMPLE, top: undefined }],
    ["unknown script", { ...CONTRACT_EXAMPLE, script: "cyrillic" }],
    ["probability above 1", { ...CONTRACT_EXAMPLE, confidence: 1.2 }],
    [
      "intensity 0 on an active emotion",
      {
        ...CONTRACT_EXAMPLE,
        emotions: [{ label: "joy", probability: 0.9, active: true, intensity: 0 }],
      },
    ],
    [
      "unknown language tag",
      {
        ...CONTRACT_EXAMPLE,
        lid: { tokens: [{ text: "x", lang: "fr" }], cmi: 0, lang_share: {} },
      },
    ],
  ])("rejects a response with %s", (_name, payload) => {
    expect(analyzeResultSchema.safeParse(payload).success).toBe(false);
  });
});

describe("analyzeText", () => {
  it("posts the text and returns the parsed result", async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(CONTRACT_EXAMPLE));
    const result = await analyzeText("yaar aaj ka din", {
      baseUrl: "https://api.example",
      fetchImpl,
    });

    expect(result.top).toBe("sadness");
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("https://api.example/v1/analyze");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      text: "yaar aaj ka din",
      options: { explain: false, lid: true, all_scores: true },
    });
  });

  it("turns an API problem response into an ApiError with its code", async () => {
    const problem = {
      type: "about:blank",
      title: "Text too long",
      status: 422,
      detail: "text must be ≤ 1000 characters",
      code: "TEXT_TOO_LONG",
    };
    const error = await failure(
      analyzeText("x", { fetchImpl: async () => jsonResponse(problem, 422) }),
    );
    expect(error.code).toBe("TEXT_TOO_LONG");
    expect(error.status).toBe(422);
  });

  it("reports a network failure as NETWORK", async () => {
    const error = await failure(
      analyzeText("x", {
        fetchImpl: async () => {
          throw new TypeError("fetch failed");
        },
      }),
    );
    expect(error.code).toBe("NETWORK");
    expect(error.status).toBeNull();
  });

  it("reports a non-JSON body as BAD_RESPONSE", async () => {
    const error = await failure(
      analyzeText("x", {
        fetchImpl: async () => new Response("<html>502</html>", { status: 502 }),
      }),
    );
    expect(error.code).toBe("BAD_RESPONSE");
    expect(error.status).toBe(502);
  });

  it("reports a 200 that breaks the contract as BAD_RESPONSE", async () => {
    const error = await failure(
      analyzeText("x", { fetchImpl: async () => jsonResponse({ hello: "world" }) }),
    );
    expect(error.code).toBe("BAD_RESPONSE");
  });

  it("reports an error body that is not a problem document as BAD_RESPONSE", async () => {
    const error = await failure(
      analyzeText("x", { fetchImpl: async () => jsonResponse({ message: "nope" }, 500) }),
    );
    expect(error.code).toBe("BAD_RESPONSE");
    expect(error.status).toBe(500);
  });

  it("lets an abort propagate so a newer request can replace an older one", async () => {
    const controller = new AbortController();
    controller.abort();
    const fetchImpl: typeof fetch = async (_input, init) => {
      init?.signal?.throwIfAborted();
      return jsonResponse(CONTRACT_EXAMPLE);
    };
    await expect(analyzeText("x", { fetchImpl, signal: controller.signal })).rejects.toMatchObject({
      name: "AbortError",
    });
  });
});
