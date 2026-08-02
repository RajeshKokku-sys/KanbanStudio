"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  createId,
  findColumnId,
  initialBoard,
  moveCard as computeMove,
  type BoardData,
} from "@/lib/kanban";
import { getBoard, removeCard, saveBoard, updateCard } from "@/lib/api";

const USER_ID = "user";

export type BoardContextValue = {
  board: BoardData | null;
  loading: boolean;
  error: string | null;
  renameColumn: (columnId: string, title: string) => void;
  addCard: (columnId: string, title: string, details: string) => void;
  moveCard: (activeId: string, overId: string) => void;
  deleteCard: (columnId: string, cardId: string) => void;
};

const BoardContext = createContext<BoardContextValue | null>(null);

export const useBoard = () => {
  const context = useContext(BoardContext);
  if (!context) {
    throw new Error("useBoard must be used within a BoardProvider");
  }
  return context;
};

export const BoardProvider = ({ children }: { children: ReactNode }) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const boardRef = useRef<BoardData | null>(null);

  useEffect(() => {
    boardRef.current = board;
  }, [board]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        let data = await getBoard(USER_ID);
        if (data === null) {
          data = await saveBoard(USER_ID, initialBoard);
        }
        if (!cancelled) {
          setBoard(data);
        }
      } catch {
        if (!cancelled) {
          setError("Failed to load the board.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const persistBoard = async (next: BoardData) => {
    try {
      await saveBoard(USER_ID, next);
    } catch {
      setError("Failed to save changes.");
    }
  };

  const renameColumn = (columnId: string, title: string) => {
    const prev = boardRef.current;
    if (!prev) {
      return;
    }
    const next: BoardData = {
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    };
    setBoard(next);
    void persistBoard(next);
  };

  const addCard = (columnId: string, title: string, details: string) => {
    const prev = boardRef.current;
    if (!prev) {
      return;
    }
    const id = createId("card");
    const next: BoardData = {
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    };
    setBoard(next);
    void persistBoard(next);
  };

  const moveCard = (activeId: string, overId: string) => {
    const prev = boardRef.current;
    if (!prev) {
      return;
    }
    const columns = computeMove(prev.columns, activeId, overId);
    if (columns === prev.columns) {
      return;
    }
    const next: BoardData = { ...prev, columns };
    setBoard(next);
    const columnId = findColumnId(columns, activeId);
    if (columnId) {
      const column = columns.find((c) => c.id === columnId);
      const position = column ? column.cardIds.indexOf(activeId) : 0;
      void updateCard(USER_ID, activeId, { column_id: columnId, position }).catch(
        () => setError("Failed to save the move.")
      );
    }
  };

  const deleteCard = (columnId: string, cardId: string) => {
    const prev = boardRef.current;
    if (!prev) {
      return;
    }
    const next: BoardData = {
      ...prev,
      cards: Object.fromEntries(
        Object.entries(prev.cards).filter(([id]) => id !== cardId)
      ),
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: column.cardIds.filter((id) => id !== cardId) }
          : column
      ),
    };
    setBoard(next);
    void removeCard(USER_ID, cardId).catch(() =>
      setError("Failed to delete the card.")
    );
  };

  return (
    <BoardContext.Provider
      value={{
        board,
        loading,
        error,
        renameColumn,
        addCard,
        moveCard,
        deleteCard,
      }}
    >
      {children}
    </BoardContext.Provider>
  );
};
