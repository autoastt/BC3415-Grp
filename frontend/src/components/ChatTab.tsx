import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { streamChat } from "../api";
import type { ChatMessage, Settings } from "../types";
import MessageBubble from "./MessageBubble";

const HISTORY_LIMIT = 6;
const uid = () => Math.random().toString(36).slice(2);

export default function ChatTab({ settings, maxChars }: { settings: Settings | null; maxChars: number }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [showRouting, setShowRouting] = useState(true);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const patch = (id: string, fn: (m: ChatMessage) => ChatMessage) =>
    setMessages((ms) => ms.map((m) => (m.id === id ? fn(m) : m)));

  async function send(text: string) {
    const question = text.trim();
    if (!question || busy) return;

    // Only completed, successful turns count as history (last 6 messages).
    const history = messages
      .filter((m) => m.status === "done" && m.content)
      .slice(-HISTORY_LIMIT)
      .map(({ role, content }) => ({ role, content }));

    const botId = uid();
    setMessages((ms) => [
      ...ms,
      { id: uid(), role: "user", content: question, status: "done" },
      { id: botId, role: "assistant", content: "", status: "streaming" },
    ]);
    setInput("");
    setBusy(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      await streamChat(question, history, (e) => {
        if (e.type === "token") patch(botId, (m) => ({ ...m, content: m.content + e.text }));
        else if (e.type === "replace") patch(botId, (m) => ({ ...m, content: e.text }));
        else if (e.type === "done")
          patch(botId, (m) => ({
            ...m, status: "done", classification: e.classification, sources: e.sources, handoff: e.handoff, links: e.links ?? [],
          }));
        else if (e.type === "error")
          patch(botId, (m) => ({ ...m, status: "error", content: e.message, classification: "error" }));
      }, ctrl.signal);
      // Stream closed without a done event (e.g. connection dropped mid-answer)
      patch(botId, (m) => (m.status === "streaming"
        ? { ...m, status: "error", content: m.content || "The answer was interrupted. Please ask again.", classification: "error" }
        : m));
    } catch (err) {
      patch(botId, (m) => ({ ...m, status: "error", content: (err as Error).message, classification: "error" }));
    } finally {
      setBusy(false);
      abortRef.current = null;
      inputRef.current?.focus();
    }
  }

  function clearChat() {
    abortRef.current?.abort();
    setMessages([]);
    setBusy(false);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    send(input);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send(input);
    }
  }

  const botName = settings?.bot_name ?? "Assistant";
  const suggestions = (settings?.allowed_topics ?? []).slice(0, 4);
  const over = input.length > maxChars;

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-4 sm:px-6">
      <div className="flex items-center justify-between gap-3 py-3">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={showRouting} onChange={(e) => setShowRouting(e.target.checked)} className="accent-teal" />
          Show how each reply was routed
        </label>
        <button onClick={clearChat} disabled={messages.length === 0} className="btn-ghost px-3 py-1.5">
          Clear chat
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pb-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col justify-center py-10">
            <h1 className="font-display text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl">
              Hi, I'm {botName}.
            </h1>
            <p className="mt-3 max-w-[52ch] text-lg text-muted">
              Ask me anything about {settings?.company_name ?? "us"}. I answer from the company's own information,
              and I'll tell you when I don't know.
            </p>
            {suggestions.length > 0 && (
              <div className="mt-6 flex flex-wrap gap-2">
                {suggestions.map((t) => (
                  <button
                    key={t}
                    onClick={() => send(`What can you tell me about your ${t}?`)}
                    className="rounded-full border border-line bg-white px-3.5 py-1.5 text-sm hover:border-teal hover:text-teal-dark"
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4 pt-2">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} showRouting={showRouting} />
            ))}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <form onSubmit={onSubmit} className="border-t border-line py-3">
        <div className="flex items-end gap-2">
          <label htmlFor="chat-input" className="sr-only">Your message</label>
          <textarea
            id="chat-input"
            ref={inputRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={`Message ${botName}`}
            className="field max-h-40 min-h-[44px] resize-none"
          />
          <button type="submit" disabled={busy || !input.trim() || over} className="btn-primary h-[44px]">
            {busy ? "Answering…" : "Send"}
          </button>
        </div>
        <p className={`mt-1 text-xs ${over ? "text-brick" : "text-muted"}`}>
          {over ? `Messages can be up to ${maxChars} characters (${input.length} now).` : "Enter to send, Shift+Enter for a new line"}
        </p>
      </form>
    </div>
  );
}
