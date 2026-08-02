import type { BoardData, Card } from "@/lib/kanban";

export type CardPatch = {
  title?: string;
  details?: string;
  column_id?: string;
  position?: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const parseOrThrow = async (response: Response) => {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
};

export const getBoard = async (userId: string): Promise<BoardData | null> => {
  const response = await fetch(`${API_BASE_URL}/boards/${userId}`);
  if (response.status === 404) {
    return null;
  }
  return parseOrThrow(response);
};

export const saveBoard = async (
  userId: string,
  board: BoardData
): Promise<BoardData> => {
  const response = await fetch(`${API_BASE_URL}/boards/${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(board),
  });
  return parseOrThrow(response);
};

export const updateCard = async (
  userId: string,
  cardId: string,
  patch: CardPatch
): Promise<Card> => {
  const response = await fetch(
    `${API_BASE_URL}/boards/${userId}/cards/${cardId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }
  );
  return parseOrThrow(response);
};

export const removeCard = async (userId: string, cardId: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/boards/${userId}/cards/${cardId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
};
