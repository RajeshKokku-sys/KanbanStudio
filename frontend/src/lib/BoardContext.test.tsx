import { act, render, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BoardProvider, useBoard, type BoardContextValue } from "@/lib/BoardContext";
import { initialBoard, type BoardData } from "@/lib/kanban";

vi.mock("@/lib/api", () => ({
  getBoard: vi.fn(),
  saveBoard: vi.fn(),
  updateCard: vi.fn(),
  removeCard: vi.fn(),
}));

import { getBoard, removeCard, saveBoard, updateCard } from "@/lib/api";

const TEST_BOARD: BoardData = {
  id: "board-1",
  title: "Test",
  columns: [
    { id: "col-a", title: "A", cardIds: ["card-1", "card-2"] },
    { id: "col-b", title: "B", cardIds: ["card-3"] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "One", details: "" },
    "card-2": { id: "card-2", title: "Two", details: "" },
    "card-3": { id: "card-3", title: "Three", details: "" },
  },
};

let context: BoardContextValue | null = null;

const Probe = () => {
  const value = useBoard();
  useEffect(() => {
    context = value;
  });
  return null;
};

const renderWithContext = () =>
  render(
    <BoardProvider>
      <Probe />
    </BoardProvider>
  );

const awaitBoard = () =>
  waitFor(() => expect(context?.board).not.toBeNull());

describe("BoardProvider", () => {
  beforeEach(() => {
    context = null;
    vi.mocked(getBoard).mockReset();
    vi.mocked(saveBoard).mockReset();
    vi.mocked(updateCard).mockReset();
    vi.mocked(removeCard).mockReset();
    vi.mocked(saveBoard).mockResolvedValue(TEST_BOARD);
    vi.mocked(updateCard).mockResolvedValue({
      id: "card-2",
      title: "Two",
      details: "",
    });
    vi.mocked(removeCard).mockResolvedValue(undefined);
  });

  it("loads an existing board from the API", async () => {
    vi.mocked(getBoard).mockResolvedValue(TEST_BOARD);
    renderWithContext();
    await awaitBoard();
    expect(getBoard).toHaveBeenCalledWith("user");
    expect(context?.board).toEqual(TEST_BOARD);
    expect(context?.loading).toBe(false);
  });

  it("creates and saves a default board when none exists", async () => {
    vi.mocked(getBoard).mockResolvedValue(null);
    renderWithContext();
    await awaitBoard();
    expect(saveBoard).toHaveBeenCalledWith("user", initialBoard);
    expect(context?.board).toEqual(TEST_BOARD);
  });

  it("surfaces an error when loading fails", async () => {
    vi.mocked(getBoard).mockRejectedValue(new Error("boom"));
    renderWithContext();
    await waitFor(() => expect(context?.error).toBe("Failed to load the board."));
    expect(context?.loading).toBe(false);
  });

  it("renames a column optimistically and persists the board", async () => {
    vi.mocked(getBoard).mockResolvedValue(TEST_BOARD);
    renderWithContext();
    await awaitBoard();

    act(() => context?.renameColumn("col-a", "Backlog"));

    expect(context?.board?.columns[0].title).toBe("Backlog");
    await waitFor(() =>
      expect(saveBoard).toHaveBeenCalledWith(
        "user",
        expect.objectContaining({
          columns: expect.arrayContaining([
            expect.objectContaining({ id: "col-a", title: "Backlog" }),
          ]),
        })
      )
    );
  });

  it("adds a card optimistically and persists the board", async () => {
    vi.mocked(getBoard).mockResolvedValue(TEST_BOARD);
    renderWithContext();
    await awaitBoard();

    act(() => context?.addCard("col-b", "New card", "Notes"));

    const newCard = context?.board?.cards[
      Object.keys(context?.board?.cards ?? {}).find(
        (id) => id.startsWith("card-") && !(id in TEST_BOARD.cards)
      ) ?? ""
    ];
    expect(newCard?.title).toBe("New card");
    expect(context?.board?.columns[1].cardIds).toContain(newCard?.id);
    await waitFor(() => expect(saveBoard).toHaveBeenCalled());
  });

  it("deletes a card optimistically and calls the API", async () => {
    vi.mocked(getBoard).mockResolvedValue(TEST_BOARD);
    renderWithContext();
    await awaitBoard();

    act(() => context?.deleteCard("col-a", "card-1"));

    expect(context?.board?.cards["card-1"]).toBeUndefined();
    expect(context?.board?.columns[0].cardIds).toEqual(["card-2"]);
    expect(removeCard).toHaveBeenCalledWith("user", "card-1");
  });

  it("moves a card optimistically and persists via the PATCH endpoint", async () => {
    vi.mocked(getBoard).mockResolvedValue(TEST_BOARD);
    renderWithContext();
    await awaitBoard();

    act(() => context?.moveCard("card-2", "col-b"));

    expect(context?.board?.columns[0].cardIds).toEqual(["card-1"]);
    expect(context?.board?.columns[1].cardIds).toEqual(["card-3", "card-2"]);
    expect(updateCard).toHaveBeenCalledWith("user", "card-2", {
      column_id: "col-b",
      position: 1,
    });
  });

  it("ignores a move that does not change anything", async () => {
    vi.mocked(getBoard).mockResolvedValue(TEST_BOARD);
    renderWithContext();
    await awaitBoard();

    act(() => context?.moveCard("card-1", "card-1"));

    expect(updateCard).not.toHaveBeenCalled();
    expect(context?.board).toEqual(TEST_BOARD);
  });
});
