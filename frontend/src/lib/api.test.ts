import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getBoard, removeCard, saveBoard, updateCard } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

const BOARD: BoardData = {
  id: "board-1",
  title: "Test",
  columns: [{ id: "col-1", title: "Backlog", cardIds: ["card-1"] }],
  cards: { "card-1": { id: "card-1", title: "One", details: "" } },
};

const jsonResponse = (body: unknown, status = 200) => {
  const response = {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(body),
  };
  return response as unknown as Response;
};

let fetchMock: ReturnType<typeof vi.fn>;

describe("api client", () => {
  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("getBoard returns the board JSON", async () => {
    fetchMock.mockResolvedValue(jsonResponse(BOARD));
    await expect(getBoard("user")).resolves.toEqual(BOARD);
  });

  it("getBoard returns null when the board does not exist", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: "Board not found" }, 404));
    await expect(getBoard("user")).resolves.toBeNull();
  });

  it("getBoard rejects on server error", async () => {
    fetchMock.mockResolvedValue(jsonResponse({}, 500));
    await expect(getBoard("user")).rejects.toThrow();
  });

  it("saveBoard POSTs the board as JSON", async () => {
    fetchMock.mockResolvedValue(jsonResponse(BOARD));
    await saveBoard("user", BOARD);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/boards/user",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(BOARD),
      })
    );
  });

  it("updateCard PATCHes card changes", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ id: "card-1", title: "New", details: "" })
    );
    await updateCard("user", "card-1", { title: "New" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/boards/user/cards/card-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ title: "New" }),
      })
    );
  });

  it("removeCard sends a DELETE request", async () => {
    fetchMock.mockResolvedValue(jsonResponse(null, 204));
    await removeCard("user", "card-1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/boards/user/cards/card-1",
      expect.objectContaining({ method: "DELETE" })
    );
  });
});
