import { Fragment, useState, type ReactNode } from "react";
import type { ChatMessage } from "../types";
import RouteTag from "./RouteTag";

/** Minimal, safe formatting: **bold** and line breaks. No HTML injection possible. */
function formatText(text: string): ReactNode {
  return text.split("\n").map((line, i, arr) => (
    <Fragment key={i}>
      {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
        part.startsWith("**") && part.endsWith("**") && part.length > 4 ? (
          <strong key={j} className="font-semibold">{part.slice(2, -2)}</strong>
        ) : (
          <Fragment key={j}>{part}</Fragment>
        ),
      )}
      {i < arr.length - 1 && <br />}
    </Fragment>
  ));
}

interface Props {
  message: ChatMessage;
  showRouting: boolean;
}

export default function MessageBubble({ message, showRouting }: Props) {
  const [open, setOpen] = useState(false);
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-teal px-4 py-2.5 text-white sm:max-w-[75%]">
          {message.content}
        </div>
      </div>
    );
  }

  const sources = message.sources ?? [];
  const streaming = message.status === "streaming";

  return (
    <div className="flex justify-start">
      <div className="max-w-[92%] sm:max-w-[80%]">
        <div
          className={`break-words rounded-2xl rounded-bl-md border px-4 py-2.5 ${
            message.status === "error" ? "border-brick/40 bg-brick-soft text-brick" : "border-line bg-white"
          }`}
          aria-live={streaming ? "polite" : undefined}
        >
          {message.content ? formatText(message.content) : streaming ? <span className="text-muted">Checking…</span> : null}
          {streaming && message.content && <span aria-hidden className="caret ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 bg-teal" />}
        </div>

        {(showRouting && message.classification) || sources.length > 0 ? (
          <div className="mt-1.5 flex flex-wrap items-center gap-2 pl-1">
            {showRouting && message.classification && <RouteTag value={message.classification} />}
            {sources.length > 0 && (
              <button
                onClick={() => setOpen((o) => !o)}
                aria-expanded={open}
                className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold text-mustard-deep hover:bg-mustard-soft"
              >
                <span aria-hidden className="h-2 w-2 rounded-full bg-mustard" />
                {open ? "Hide sources" : `Sources (${sources.length})`}
              </button>
            )}
          </div>
        ) : null}

        {open && sources.length > 0 && (
          <ul className="mt-2 space-y-2 border-l-2 border-mustard pl-3">
            {sources.map((s) => (
              <li key={`${s.source_id}-${s.chunk_index}`} className="text-sm">
                <p className="font-semibold">
                  {s.title}
                  <span className="ml-2 font-normal text-muted">
                    part {s.chunk_index + 1}, match {Math.round(s.score * 100)}%
                  </span>
                </p>
                <p className="mt-0.5 line-clamp-4 text-muted">{s.snippet}</p>
              </li>
            ))}
          </ul>
        )}

      </div>
    </div>
  );
}
