import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { BoardProvider } from "@/lib/BoardContext";
import { initialBoard, type BoardData } from "@/lib/kanban";

vi.mock("@/lib/api", () => ({
  getBoard: vi.fn(),
  saveBoard: vi.fn(),
  updateCard: vi.fn(),
  removeCard: vi.fn(),
}));

import { getBoard, removeCard, saveBoard, updateCard } from "@/lib/api";

const getFirstColumn = async () =>
  (await screen.findAllByTestId(/column-/i))[0];

const renderBoard = () =>
  render(
    <BoardProvider>
      <KanbanBoard />
    </BoardProvider>
  );

describe("KanbanBoard", () => {
  beforeEach(() => {
    vi.mocked(getBoard).mockResolvedValue(initialBoard);
    vi.mocked(saveBoard).mockResolvedValue(initialBoard);
    vi.mocked(updateCard).mockResolvedValue({
      id: "card-1",
      title: "One",
      details: "",
    });
    vi.mocked(removeCard).mockResolvedValue(undefined);
  });

  it("renders five columns fetched from the API", async () => {
    renderBoard();
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("shows a loading state while fetching the board", () => {
    vi.mocked(getBoard).mockReturnValue(
      new Promise<BoardData | null>(() => {})
    );
    renderBoard();
    expect(screen.getByText(/loading board/i)).toBeInTheDocument();
  });

  it("shows an error state when loading fails", async () => {
    vi.mocked(getBoard).mockRejectedValue(new Error("boom"));
    renderBoard();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Failed to load the board."
    );
  });

  it("renames a column and persists the change", async () => {
    renderBoard();
    const column = await getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
    await waitFor(() => expect(saveBoard).toHaveBeenCalled());
  });

  it("adds a card and persists it", async () => {
    renderBoard();
    const column = await getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();
    await waitFor(() => expect(saveBoard).toHaveBeenCalled());
  });

  it("removes a card and calls the API", async () => {
    renderBoard();
    const column = await getFirstColumn();
    const deleteButton = within(column).getByRole("button", {
      name: /delete align roadmap themes/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("Align roadmap themes")).not.toBeInTheDocument();
    await waitFor(() => expect(removeCard).toHaveBeenCalled());
  });
});
