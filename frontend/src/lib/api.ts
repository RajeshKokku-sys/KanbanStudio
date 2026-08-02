import type { BoardData, Card } from "@/lib/kanban";

export type CardPatch = {
  title?: string;
  details?: string;
  column_id?: string;
  position?: number;
};

export type BoardUpdateType = "add" | "edit" | "move" | "delete";

export type BoardUpdate = {
  type: BoardUpdateType;
  cardId?: string;
  columnId?: string;
  payload?: { title?: string; description?: string; order?: number };
};

export type AiAskResponse = {
  message: string;
  boardUpdates?: BoardUpdate[];
};

export type ChatHistoryItem = {
  role: "user" | "assistant";
  content: string;
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

export const askAi = async (
  question: string,
  history: ChatHistoryItem[]
): Promise<AiAskResponse> => {
  const response = await fetch(`${API_BASE_URL}/ai/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
  return parseOrThrow(response);
};
