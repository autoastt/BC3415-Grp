import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { KBSource, KBSourceDetail } from "../types";

/** Shows a source's saved text. Markdown, plain text and pasted text can be edited and re-indexed. */
export default function SourceViewer({ sourceId, onClose, onSaved }: {
  sourceId: string; onClose: () => void; onSaved: (s: KBSource) => void;
}) {
  const [detail, setDetail] = useState<KBSourceDetail | null>(null);
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const dirty = editing && detail?.content != null && draft !== detail.content;

  useEffect(() => {
    let live = true;
    api.getSource(sourceId)
      .then((d) => { if (live) { setDetail(d); setDraft(d.content ?? ""); } })
      .catch((e: Error) => live && setError(e.message));
    return () => { live = false; };
  }, [sourceId]);

  useEffect(() => { dialogRef.current?.focus(); }, []);

  function close() {
    if (dirty && !window.confirm("Discard your unsaved changes?")) return;
    onClose();
  }

  async function save() {
    if (!detail) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateSource(detail.id, draft);
      const fresh = await api.getSource(detail.id);
      setDetail(fresh);
      setDraft(fresh.content ?? "");
      setEditing(false);
      setNotice(`Saved. The bot now answers from the new text (${updated.chunk_count} chunks).`);
      onSaved(updated);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" onMouseDown={(e) => {
      if (e.target === e.currentTarget) close();
    }}>
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="source-viewer-title" tabIndex={-1}
        onKeyDown={(e) => e.key === "Escape" && close()}
        className="panel flex max-h-[90vh] w-full max-w-3xl flex-col shadow-xl focus:outline-none">
        <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <h2 id="source-viewer-title" className="h2 truncate">{detail?.title ?? "Loading…"}</h2>
            {detail && (
              <p className="mt-0.5 truncate text-xs text-muted">
                {detail.origin ?? "Pasted text"}
                {detail.updated_at && ` · edited ${new Date(detail.updated_at).toLocaleString()}`}
              </p>
            )}
          </div>
          <button onClick={close} className="btn-ghost px-3 py-1" aria-label="Close">Close</button>
        </div>

        <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
          {error && <p role="alert" className="mb-3 rounded-md bg-brick-soft px-3 py-2 text-sm text-brick">{error}</p>}
          {notice && !editing && <p role="status" className="mb-3 rounded-md bg-paper px-3 py-2 text-sm">{notice}</p>}
          {!detail && !error && <p className="text-sm text-muted">Loading content…</p>}
          {detail && detail.content === null && (
            <p className="text-sm text-muted">
              This source was added before uploads kept their text, so there is nothing to show.
              Delete it and upload the file again to view or edit it.
            </p>
          )}
          {detail && detail.content !== null && (editing ? (
            <>
              <label htmlFor="source-edit" className="sr-only">Source text</label>
              <textarea id="source-edit" value={draft} onChange={(e) => setDraft(e.target.value)}
                spellCheck className="field min-h-[50vh] resize-y font-mono text-sm leading-relaxed" />
            </>
          ) : (
            <pre className="whitespace-pre-wrap break-words font-mono text-sm leading-relaxed text-ink">{detail.content}</pre>
          ))}
        </div>

        {detail && detail.content !== null && (
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-line px-5 py-3">
            {!detail.editable && (
              <p className="mr-auto text-xs text-muted">Text pulled from the file. Only Markdown and plain text can be edited.</p>
            )}
            {detail.editable && !editing && (
              <button onClick={() => { setEditing(true); setNotice(null); }} className="btn-primary">Edit</button>
            )}
            {editing && (
              <>
                <p className="mr-auto text-xs text-muted">Saving re-indexes this source for the bot.</p>
                <button onClick={() => { setDraft(detail.content ?? ""); setEditing(false); setError(null); }}
                  disabled={saving} className="btn-ghost">Cancel</button>
                <button onClick={save} disabled={saving || !dirty || !draft.trim()} className="btn-primary">
                  {saving ? "Saving…" : "Save"}
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
