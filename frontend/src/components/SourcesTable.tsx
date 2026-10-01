import { useState } from "react";
import { api } from "../api";
import type { KBSource } from "../types";

const TYPE_LABEL: Record<string, string> = {
  text: "Text", pdf: "PDF", docx: "Word", txt: "Plain text", md: "Markdown", csv: "CSV", url: "Web page",
};

export default function SourcesTable({ sources, loading, onDeleted }: {
  sources: KBSource[]; loading: boolean; onDeleted: (id: string) => void;
}) {
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function remove(id: string) {
    setDeletingId(id);
    setError(null);
    try {
      await api.deleteSource(id);
      onDeleted(id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeletingId(null);
      setConfirmId(null);
    }
  }

  const totalChunks = sources.reduce((n, s) => n + s.chunk_count, 0);

  return (
    <section className="panel">
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-5 pt-5">
        <h2 className="h2">Sources</h2>
        <p className="text-sm text-muted">{sources.length} sources, {totalChunks} chunks</p>
      </div>
      {error && <p role="alert" className="mx-5 mt-3 rounded-md bg-brick-soft px-3 py-2 text-sm text-brick">{error}</p>}
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="border-y border-line bg-paper/70 text-muted">
            <tr>
              <th className="px-5 py-2 font-medium">Title</th>
              <th className="px-3 py-2 font-medium">Type</th>
              <th className="px-3 py-2 text-right font-medium">Chunks</th>
              <th className="px-3 py-2 font-medium">Added</th>
              <th className="px-5 py-2"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {loading && sources.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-6 text-muted">Loading sources…</td></tr>
            )}
            {!loading && sources.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-6 text-muted">
                Nothing here yet. Add your menu, hours or policies above so the bot has something to answer from.
              </td></tr>
            )}
            {sources.map((s) => (
              <tr key={s.id} className="border-b border-line last:border-0">
                <td className="max-w-[260px] px-5 py-2.5">
                  <p className="truncate font-medium" title={s.title}>{s.title}</p>
                  {s.origin && <p className="truncate text-xs text-muted" title={s.origin}>{s.origin}</p>}
                </td>
                <td className="px-3 py-2.5">{TYPE_LABEL[s.type] ?? s.type}</td>
                <td className="px-3 py-2.5 text-right tabular-nums">{s.chunk_count}</td>
                <td className="whitespace-nowrap px-3 py-2.5 text-muted">
                  {new Date(s.created_at).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}
                </td>
                <td className="whitespace-nowrap px-5 py-2.5 text-right">
                  {confirmId === s.id ? (
                    <span className="inline-flex gap-2">
                      <button onClick={() => remove(s.id)} disabled={deletingId === s.id}
                        className="btn bg-brick px-3 py-1 text-white hover:bg-brick/90">
                        {deletingId === s.id ? "Deleting…" : "Delete"}
                      </button>
                      <button onClick={() => setConfirmId(null)} className="btn-ghost px-3 py-1">Keep</button>
                    </span>
                  ) : (
                    <button onClick={() => setConfirmId(s.id)} className="btn-ghost px-3 py-1 hover:border-brick hover:text-brick"
                      aria-label={`Delete ${s.title}`}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
