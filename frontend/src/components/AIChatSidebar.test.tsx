import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AIChatSidebar } from "@/components/AIChatSidebar";
import { BoardProvider } from "@/lib/BoardContext";
import { initialBoard } from "@/lib/kanban";

vi.mock("@/lib/api", () => ({
  getBoard: vi.fn(),
  saveBoard: vi.fn(),
  updateCard: vi.fn(),
  removeCard: vi.fn(),
  askAi: vi.fn(),
}));

import { askAi, getBoard, type AiAskResponse } from "@/lib/api";

const renderSidebar = (initialOpen = true) =>
  render(
    <BoardProvider>
      <AIChatSidebar initialOpen={initialOpen} />
    </BoardProvider>
  );

const openSidebar = async (user: ReturnType<typeof userEvent.setup>) => {
  renderSidebar(false);
  await user.click(screen.getByRole("button", { name: /ask the ai/i }));
};

describe("AIChatSidebar", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getBoard).mockResolvedValue(initialBoard);
    vi.mocked(askAi).mockResolvedValue({ message: "Done." });
  });

  it("renders collapsed by default with a toggle button", () => {
    renderSidebar(false);
    expect(
      screen.getByRole("button", { name: /ask the ai/i })
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("AI chat assistant")).not.toBeInTheDocument();
  });

  it("opens and closes the drawer", async () => {
    const user = userEvent.setup();
    await openSidebar(user);
    expect(
      screen.getByLabelText("AI chat assistant")
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByLabelText("AI chat assistant")).not.toBeInTheDocument();
  });

  it("displays the user question and the assistant reply", async () => {
    const user = userEvent.setup();
    renderSidebar();
    vi.mocked(askAi).mockResolvedValue({ message: "Cards updated." });
    await user.type(screen.getByLabelText("Message the assistant"), "Add a card");
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText("Cards updated.")).toBeInTheDocument();
    expect(within(screen.getByTestId("message-user")).getByText("Add a card")).toBeInTheDocument();
    expect(askAi).toHaveBeenCalledWith("Add a card", []);
  });

  it("sends conversation history with subsequent queries", async () => {
    const user = userEvent.setup();
    renderSidebar();
    await user.type(screen.getByLabelText("Message the assistant"), "First");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByText("Done.");

    await user.type(screen.getByLabelText("Message the assistant"), "Second");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() =>
      expect(askAi).toHaveBeenLastCalledWith(
        "Second",
        expect.arrayContaining([
          { role: "user", content: "First" },
          { role: "assistant", content: "Done." },
        ])
      )
    );
  });

  it("refreshes the board when board updates are returned", async () => {
    const user = userEvent.setup();
    renderSidebar();
    vi.mocked(getBoard).mockClear();
    vi.mocked(askAi).mockResolvedValue({
      message: "Card added to Backlog.",
      boardUpdates: [
        {
          type: "add",
          columnId: "col-backlog",
          cardId: "card-new-1",
          payload: { title: "Via AI", description: "Created by assistant" },
        },
      ],
    });
    await user.type(screen.getByLabelText("Message the assistant"), "Add a card");
    await user.click(screen.getByRole("button", { name: /send/i }));
    expect(await screen.findByText("Card added to Backlog.")).toBeInTheDocument();
    await waitFor(() => expect(getBoard).toHaveBeenCalledWith("user"));
  });

  it("shows a loading spinner while awaiting a reply", async () => {
    const user = userEvent.setup();
    renderSidebar();
    let resolve: (value: AiAskResponse) => void = () => {};
    vi.mocked(askAi).mockReturnValue(
      new Promise((res) => {
        resolve = res;
      })
    );
    await user.type(screen.getByLabelText("Message the assistant"), "Hello");
    await user.click(screen.getByRole("button", { name: /send/i }));
    expect(screen.getByTestId("loading")).toBeInTheDocument();
    resolve({ message: "Done.", boardUpdates: [] });
    expect(await screen.findByText("Done.")).toBeInTheDocument();
  });

  it("shows an error when the request fails", async () => {
    const user = userEvent.setup();
    renderSidebar();
    vi.mocked(askAi).mockRejectedValue(new Error("boom"));
    await user.type(screen.getByLabelText("Message the assistant"), "Hello");
    await user.click(screen.getByRole("button", { name: /send/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The AI service could not be reached."
    );
  });

  it("does not send an empty message", async () => {
    const user = userEvent.setup();
    renderSidebar();
    await user.click(screen.getByRole("button", { name: /send/i }));
    expect(askAi).not.toHaveBeenCalled();
  });
});