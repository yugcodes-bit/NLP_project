import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ResultView } from "@/components/ResultView";
import { CONTRACT_EXAMPLE, NEUTRAL_DUMMY_EXAMPLE, UNSURE_EXAMPLE } from "@/lib/__tests__/fixtures";

describe("ResultView", () => {
  it("shows each active emotion with name, percentage and intensity in words", () => {
    render(<ResultView result={CONTRACT_EXAMPLE} />);

    const sadness = within(screen.getByTestId("emotion-sadness"));
    expect(sadness.getByText("Sadness")).toBeInTheDocument();
    expect(sadness.getByText("Dukh")).toBeInTheDocument();
    expect(sadness.getByText("82%")).toBeInTheDocument();
    expect(sadness.getByText("high")).toBeInTheDocument();

    const anger = within(screen.getByTestId("emotion-anger"));
    expect(anger.getByText("31%")).toBeInTheDocument();
    expect(anger.getByText("low")).toBeInTheDocument();

    expect(screen.queryByTestId("emotion-joy")).not.toBeInTheDocument();
  });

  it("lists emotions in the order the API returned them", () => {
    render(<ResultView result={CONTRACT_EXAMPLE} />);
    const order = screen.getAllByTestId(/^emotion-/).map((row) => row.dataset.testid);
    expect(order).toEqual(["emotion-sadness", "emotion-anger"]);
  });

  it("reveals all seven scores on request", async () => {
    const user = userEvent.setup();
    render(<ResultView result={CONTRACT_EXAMPLE} />);

    const toggle = screen.getByRole("button", { name: "Show all emotions" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);

    const all = within(screen.getByRole("group", { name: "All emotions" }));
    expect(all.getAllByTestId(/^emotion-/)).toHaveLength(7);
    expect(within(all.getByTestId("emotion-joy")).getByText("2%")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show only detected emotions" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("shows the unsure card with the two candidates instead of bars", () => {
    render(<ResultView result={UNSURE_EXAMPLE} />);
    const card = within(screen.getByRole("region", { name: /pakka nahi hai/ }));
    expect(card.getByText("Fear")).toBeInTheDocument();
    expect(card.getByText("35%")).toBeInTheDocument();
    expect(card.getByText("Surprise")).toBeInTheDocument();
    expect(screen.queryByTestId("emotion-fear")).not.toBeInTheDocument();
  });

  it("shows neutral without an intensity", () => {
    render(<ResultView result={NEUTRAL_DUMMY_EXAMPLE} />);
    const neutral = within(screen.getByTestId("emotion-neutral"));
    expect(neutral.getByText("83%")).toBeInTheDocument();
    // Its Hinglish name is also "Neutral"; it must not be printed twice.
    expect(neutral.getAllByText(/Neutral/)).toHaveLength(1);
    for (const word of ["low", "moderate", "high"]) {
      expect(neutral.queryByText(word)).not.toBeInTheDocument();
    }
  });

  it("warns when the answer comes from the placeholder model, and only then", () => {
    const { unmount } = render(<ResultView result={NEUTRAL_DUMMY_EXAMPLE} />);
    expect(screen.getByRole("note")).toHaveTextContent("not real predictions");
    unmount();

    render(<ResultView result={CONTRACT_EXAMPLE} />);
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("renders the code-mix lens with a text tag under every word", () => {
    render(<ResultView result={CONTRACT_EXAMPLE} />);
    const lens = within(screen.getByRole("region", { name: "Code-mix lens" }));
    expect(lens.getByText("CMI 0 · 100% Hindi · 0% English")).toBeInTheDocument();
    expect(lens.getAllByRole("listitem")).toHaveLength(8);
    expect(lens.getAllByText("hi")).toHaveLength(7);
    expect(lens.getByText("univ")).toBeInTheDocument();
  });

  it("leaves the lens out when the API sent no language tags", () => {
    render(<ResultView result={NEUTRAL_DUMMY_EXAMPLE} />);
    expect(screen.queryByRole("region", { name: "Code-mix lens" })).not.toBeInTheDocument();
  });

  it("shows confidence, model version and latency", () => {
    render(<ResultView result={CONTRACT_EXAMPLE} />);
    expect(
      screen.getByText("Confidence 0.82 · Model bhaav-teacher-1.0.0 · 94 ms"),
    ).toBeInTheDocument();
  });
});
