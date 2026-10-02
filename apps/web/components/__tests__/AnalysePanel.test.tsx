import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalysePanel, SLOW_AFTER_MS } from "@/components/AnalysePanel";
import { Disclaimer } from "@/components/Disclaimer";
import { type AnalyzeFn, type AnalyzeResult, ApiError } from "@/lib/api";
import { CONTRACT_EXAMPLE } from "@/lib/__tests__/fixtures";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const input = () => screen.getByLabelText("Your message");
const submit = () => screen.getByRole("button", { name: /^(Analyse|Samajh raha hoon…)$/ });

afterEach(() => {
  vi.useRealTimers();
});

describe("AnalysePanel", () => {
  it("starts with an empty input and a disabled button", () => {
    render(<AnalysePanel analyze={vi.fn()} />);
    expect(input()).toHaveValue("");
    expect(submit()).toBeDisabled();
    expect(screen.getByText("0/1000")).toBeInTheDocument();
  });

  it("sends the text and shows the result", async () => {
    const user = userEvent.setup();
    const analyze = vi.fn<AnalyzeFn>(async () => CONTRACT_EXAMPLE);
    render(<AnalysePanel analyze={analyze} />);

    await user.type(input(), "yaar aaj ka din bahut bekaar tha");
    await user.click(submit());

    expect(analyze).toHaveBeenCalledTimes(1);
    expect(analyze.mock.calls[0]?.[0]).toBe("yaar aaj ka din bahut bekaar tha");
    expect(await screen.findByTestId("emotion-sadness")).toBeInTheDocument();
    expect(submit()).toHaveTextContent("Analyse");
  });

  it("submits with Ctrl+Enter", async () => {
    const user = userEvent.setup();
    const analyze = vi.fn<AnalyzeFn>(async () => CONTRACT_EXAMPLE);
    render(<AnalysePanel analyze={analyze} />);

    await user.type(input(), "kya baat hai");
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(analyze).toHaveBeenCalledTimes(1);
    expect(await screen.findByTestId("emotion-sadness")).toBeInTheDocument();
  });

  it("fills the input from an example chip and shows the script badge", async () => {
    const user = userEvent.setup();
    render(<AnalysePanel analyze={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "सच में बहुत खुश हूँ आज" }));
    expect(input()).toHaveValue("सच में बहुत खुश हूँ आज");
    expect(screen.getByText("देवनागरी")).toBeInTheDocument();
    expect(submit()).toBeEnabled();
  });

  it("counts an emoji as one character", async () => {
    const user = userEvent.setup();
    render(<AnalysePanel analyze={vi.fn()} />);
    await user.type(input(), "😂😂");
    expect(screen.getByText("2/1000")).toBeInTheDocument();
  });

  it("blocks text over the limit and says by how much", async () => {
    const user = userEvent.setup();
    const analyze = vi.fn<AnalyzeFn>();
    render(<AnalysePanel analyze={analyze} />);

    await user.click(input());
    await user.paste("a".repeat(1003));

    expect(screen.getByRole("alert")).toHaveTextContent("Too long by 3 characters");
    expect(input()).toHaveAttribute("aria-invalid", "true");
    expect(submit()).toBeDisabled();
    await user.keyboard("{Control>}{Enter}{/Control}");
    expect(analyze).not.toHaveBeenCalled();
  });

  it("shows a loading label, then explains the cold start after 1.5 s", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const pending = deferred<AnalyzeResult>();
    render(<AnalysePanel analyze={() => pending.promise} />);

    await user.type(input(), "kal interview hai");
    await user.click(submit());
    expect(submit()).toHaveTextContent("Samajh raha hoon…");
    expect(submit()).toBeDisabled();
    expect(screen.queryByText(/Model so raha tha/)).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(SLOW_AFTER_MS + 10);
    });
    expect(screen.getByText(/Model so raha tha/)).toBeInTheDocument();

    await act(async () => {
      pending.resolve(CONTRACT_EXAMPLE);
    });
    expect(screen.queryByText(/Model so raha tha/)).not.toBeInTheDocument();
    expect(screen.getByTestId("emotion-sadness")).toBeInTheDocument();
  });

  it("shows a friendly message for a known error and lets the user retry", async () => {
    const user = userEvent.setup();
    const analyze = vi
      .fn<AnalyzeFn>()
      .mockRejectedValueOnce(new ApiError("NETWORK", null, "network request failed"))
      .mockResolvedValueOnce(CONTRACT_EXAMPLE);
    render(<AnalysePanel analyze={analyze} />);

    await user.type(input(), "kuch bhi");
    await user.click(submit());
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reach the server");

    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByTestId("emotion-sadness")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(analyze).toHaveBeenCalledTimes(2);
  });

  it("falls back to a generic message for an unknown error", async () => {
    const user = userEvent.setup();
    const analyze = vi.fn<AnalyzeFn>().mockRejectedValue(new Error("boom"));
    render(<AnalysePanel analyze={analyze} />);

    await user.type(input(), "kuch bhi");
    await user.click(submit());
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong");
  });
});

describe("Disclaimer", () => {
  it("says Bhaav is not a medical or psychological tool", () => {
    render(<Disclaimer />);
    expect(screen.getByText(/not a medical or psychological tool/)).toBeInTheDocument();
  });
});
