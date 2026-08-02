"use client";

import { useRef, useState, type FormEvent } from "react";
import clsx from "clsx";
import { askAi, type ChatHistoryItem } from "@/lib/api";
import { useBoard } from "@/lib/BoardContext";

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
};

let nextId = 1;

export const AIChatSidebar = ({ initialOpen = false }: { initialOpen?: boolean }) => {
  const { refreshBoard } = useBoard();
  const [open, setOpen] = useState(initialOpen);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const history: ChatHistoryItem[] = messages.map((message) => ({
    role: message.role,
    content: message.content,
  }));

  const handleToggle = () => {
    setOpen((previous) => !previous);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const question = input.trim();
    if (!question || loading) {
      return;
    }
    setMessages((previous) => [
      ...previous,
      { id: nextId++, role: "user", content: question },
    ]);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const data = await askAi(question, history);
      setMessages((previous) => [
        ...previous,
        { id: nextId++, role: "assistant", content: data.message },
      ]);
      if (data.boardUpdates && data.boardUpdates.length > 0) {
        await refreshBoard();
      }
    } catch {
      setError("The AI service could not be reached.");
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={open}
        aria-controls="ai-chat-drawer"
        className="fixed right-5 top-5 z-40 rounded-full bg-[var(--secondary-purple)] px-5 py-3 text-sm font-semibold text-white shadow-[var(--shadow)] transition hover:opacity-90"
      >
        {open ? "Close assistant" : "Ask the AI"}
      </button>

      {open && (
        <aside
          id="ai-chat-drawer"
          aria-label="AI chat assistant"
          className="fixed right-5 top-[4.75rem] z-30 flex h-[calc(100vh-6rem)] w-[min(24rem,calc(100vw-3rem))] flex-col overflow-hidden rounded-3xl border border-[var(--stroke)] bg-[var(--surface-strong)] shadow-[var(--shadow)]"
        >
          <div className="flex items-center justify-between border-b border-[var(--stroke)] bg-white/80 px-5 py-4">
            <div className="flex items-center gap-3">
              <span className="h-2.5 w-2.5 rounded-full bg-[var(--accent-yellow)]" />
              <h2 className="font-display text-lg font-semibold text-[var(--navy-dark)]">
                AI Assistant
              </h2>
            </div>
            <button
              type="button"
              onClick={handleToggle}
              aria-label="Close"
              className="rounded-full px-2 py-1 text-sm font-semibold text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
            >
              Close
            </button>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
            {messages.length === 0 && (
              <p className="text-sm leading-6 text-[var(--gray-text)]">
                Tell the assistant what to change on the board. It can add, edit,
                move, or delete cards.
              </p>
            )}
            {messages.map((message) => (
              <div
                key={message.id}
                className={clsx(
                  "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6",
                  message.role === "user"
                    ? "ml-auto bg-[var(--primary-blue)] text-white"
                    : "bg-[var(--surface)] text-[var(--navy-dark)]"
                )}
                data-testid={`message-${message.role}`}
              >
                {message.content}
              </div>
            ))}
            {loading && (
              <div
                role="status"
                aria-live="polite"
                className="flex items-center gap-3 px-2 text-sm text-[var(--gray-text)]"
                data-testid="loading"
              >
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-[var(--primary-blue)] border-t-transparent" />
                Thinking...
              </div>
            )}
            {error && (
              <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
                {error}
              </p>
            )}
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 border-t border-[var(--stroke)] p-3"
          >
            <label htmlFor="ai-chat-input" className="sr-only">
              Message the assistant
            </label>
            <input
              id="ai-chat-input"
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask the assistant..."
              className="min-w-0 flex-1 rounded-full border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              autoComplete="off"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              Send
            </button>
          </form>
        </aside>
      )}
    </>
  );
};