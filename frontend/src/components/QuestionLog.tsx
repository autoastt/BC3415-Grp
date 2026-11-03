import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Classification, LogResponse } from "../types";
import RouteTag from "./RouteTag";

const FILTERS: { id: string; label: string }[] = [
  { id: "", label: "All" },
  { id: "no_answer", label: "Not in knowledge base" },
  { id: "out_of_scope", label: "Declined" },
  { id: "in_scope", label: "Answered" },
  { id: "handoff", label: "Handed off" },
];

export default function QuestionLog({ refreshKey }: { refreshKey: number }) {
  const [filter, setFilter] = useState("no_answer");
  const [data, setData] = useState<LogResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.logs(filter || undefined).then((d) => { setData(d); setError(null); }).catch((e: Error) => setError(e.message));
  }, [filter]);
  useEffect(load, [load, refreshKey]);

  const s = data?.summary ?? {};
  const known = new Set(["in_scope", "out_of_scope", "no_answer", "greeting", "handoff", "error"]);

  return (
    <section className="panel">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-5">
        <div>
          <h2 className="h2">Customer questions</h2>
          {data && (
            <p className="mt-0.5 text-sm text-muted">
              {s.in_scope ?? 0} answered, {s.no_answer ?? 0} not in knowledge base, {s.out_of_scope ?? 0} declined, {s.handoff ?? 0} handed off
            </p>
          )}
          {data?.encryption && (
            <p className={`mt-0.5 text-xs ${data.encryption.key_source === "env" ? "text-muted" : "text-mustard-deep"}`}>
              {data.encryption.key_source === "env"
                ? "Questions are encrypted at rest. Visitor IPs are kept only as a one-way hash."
                : "Questions are encrypted at rest, but with a key generated next to the data. Set LOG_ENCRYPTION_KEY for stronger protection."}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="log-filter" className="sr-only">Filter</label>
          <select id="log-filter" value={filter} onChange={(e) => setFilter(e.target.value)} className="field w-auto py-1.5 text-sm">
            {FILTERS.map((f) => <option key={f.id} value={f.id}>{f.label}</option>)}
          </select>
          <button onClick={load} className="btn-ghost px-3 py-1.5">Refresh</button>
        </div>
      </div>
      {filter === "no_answer" && (
        <p className="px-5 pt-2 text-sm text-muted">
          These are real questions the bot couldn't answer. Adding content for them closes the gaps.
        </p>
      )}
      {error && <p role="alert" className="mx-5 mt-3 rounded-md bg-brick-soft px-3 py-2 text-sm text-brick">{error}</p>}
      <div className="mt-3 max-h-[420px] overflow-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="sticky top-0 border-y border-line bg-paper text-muted">
            <tr>
              <th className="px-5 py-2 font-medium">Question</th>
              <th className="px-3 py-2 font-medium">Outcome</th>
              <th className="px-3 py-2 text-right font-medium">Best match</th>
              <th className="px-5 py-2 font-medium">When</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.length === 0 && (
              <tr><td colSpan={4} className="px-5 py-6 text-muted">No questions in this view yet.</td></tr>
            )}
            {data?.items.map((r) => (
              <tr key={r.id} className="border-b border-line last:border-0 align-top">
                <td className="max-w-[340px] px-5 py-2.5 break-words">{r.question}</td>
                <td className="px-3 py-2.5">
                  {known.has(r.classification) ? <RouteTag value={r.classification as Classification} /> : r.classification}
                  {r.reason && <p className="mt-1 text-xs text-muted">{r.reason.replace(/_/g, " ")}</p>}
                </td>
                <td className="px-3 py-2.5 text-right tabular-nums text-muted">
                  {r.top_score === null ? "" : `${Math.round(r.top_score * 100)}%`}
                </td>
                <td className="whitespace-nowrap px-5 py-2.5 text-muted">
                  {new Date(r.ts).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
