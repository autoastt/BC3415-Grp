import type { Classification } from "../types";

const STYLES: Record<Classification, { label: string; cls: string; title: string }> = {
  in_scope: { label: "Answered from knowledge base", cls: "bg-teal-soft text-teal-dark", title: "Grounded in retrieved company content" },
  out_of_scope: { label: "Declined", cls: "border border-ink/25 text-ink", title: "Outside allowed topics or an attempt to change the bot's rules" },
  no_answer: { label: "Not in knowledge base", cls: "border border-dashed border-muted/60 text-muted", title: "Nothing relevant enough was found, so the bot didn't guess" },
  handoff: { label: "Handed to a person", cls: "border border-teal text-teal-dark", title: "Routed to human support" },
  greeting: { label: "Greeting", cls: "text-muted", title: "Small talk, no lookup needed" },
  error: { label: "Error", cls: "bg-brick-soft text-brick", title: "Something failed" },
};

export default function RouteTag({ value }: { value: Classification }) {
  const s = STYLES[value];
  return (
    <span title={s.title} className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${s.cls}`}>
      {s.label}
    </span>
  );
}
