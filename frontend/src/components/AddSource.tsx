import { useRef, useState, type FormEvent } from "react";
import { api, uploadFile } from "../api";
import type { KBSource } from "../types";

type Mode = "text" | "file" | "url";
const ACCEPT = ".pdf,.docx,.txt,.md,.csv";
const EXTS = ACCEPT.split(",");

interface Progress { label: string; pct: number | null }

export default function AddSource({ maxMb, onAdded }: { maxMb: number; onAdded: (s: KBSource) => void }) {
  const [mode, setMode] = useState<Mode>("text");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function pickFile(f: File | null) {
    setError(null);
    if (!f) return setFile(null);
    const ext = "." + (f.name.split(".").pop() ?? "").toLowerCase();
    if (!EXTS.includes(ext)) return setError("Choose a PDF, DOCX, TXT, MD or CSV file.");
    if (f.size > maxMb * 1024 * 1024) return setError(`Files must be ${maxMb} MB or smaller.`);
    setFile(f);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    try {
      let added: KBSource;
      if (mode === "text") {
        setProgress({ label: "Reading and indexing", pct: null });
        added = await api.addText(title.trim(), content);
        setTitle("");
        setContent("");
      } else if (mode === "url") {
        setProgress({ label: "Fetching the page and indexing", pct: null });
        added = await api.addUrl(url.trim());
        setUrl("");
      } else {
        if (!file) return;
        added = await uploadFile(
          file,
          (pct) => setProgress({ label: "Uploading", pct }),
          (stage) => stage === "processing" && setProgress({ label: "Reading and indexing", pct: null }),
        );
        setFile(null);
        if (fileRef.current) fileRef.current.value = "";
      }
      onAdded(added);
      setNotice(`Added "${added.title}" as ${added.chunk_count} ${added.chunk_count === 1 ? "chunk" : "chunks"}.`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setProgress(null);
    }
  }

  const canSubmit =
    !progress &&
    ((mode === "text" && title.trim() && content.trim()) ||
      (mode === "url" && /^https?:\/\/.+/i.test(url.trim())) ||
      (mode === "file" && file));

  const modes: { id: Mode; label: string }[] = [
    { id: "text", label: "Paste text" },
    { id: "file", label: "Upload a file" },
    { id: "url", label: "Scrape a web page" },
  ];

  return (
    <section className="panel p-5">
      <h2 className="h2">Add information</h2>
      <p className="mt-1 text-sm text-muted">The bot can only answer from what you add here.</p>

      <div role="tablist" aria-label="Source type" className="mt-4 inline-flex rounded-md border border-line p-0.5">
        {modes.map((m) => (
          <button
            key={m.id}
            role="tab"
            type="button"
            aria-selected={mode === m.id}
            onClick={() => { setMode(m.id); setError(null); setNotice(null); }}
            className={`rounded px-3 py-1.5 text-sm font-medium ${mode === m.id ? "bg-ink text-white" : "text-muted hover:text-ink"}`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="mt-4 space-y-3">
        {mode === "text" && (
          <>
            <div>
              <label className="label" htmlFor="src-title">Title</label>
              <input id="src-title" className="field" value={title} maxLength={200}
                onChange={(e) => setTitle(e.target.value)} placeholder="Holiday opening hours" />
            </div>
            <div>
              <label className="label" htmlFor="src-content">Content</label>
              <textarea id="src-content" className="field min-h-[160px]" value={content}
                onChange={(e) => setContent(e.target.value)} placeholder="Paste policies, menus, FAQs…" />
            </div>
          </>
        )}

        {mode === "file" && (
          <label
            htmlFor="src-file"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); pickFile(e.dataTransfer.files[0] ?? null); }}
            className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-line bg-paper/60 px-4 py-8 text-center hover:border-flame"
          >
            <span className="font-semibold">{file ? file.name : "Drop a file here or click to choose"}</span>
            <span className="mt-1 text-sm text-muted">
              {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : `PDF, DOCX, TXT, MD or CSV, up to ${maxMb} MB`}
            </span>
            <input id="src-file" ref={fileRef} type="file" accept={ACCEPT} className="sr-only"
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)} />
          </label>
        )}

        {mode === "url" && (
          <div>
            <label className="label" htmlFor="src-url">Page address</label>
            <input id="src-url" className="field" type="url" value={url} onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/faq" />
            <p className="mt-1 text-xs text-muted">Scripts, menus, headers and footers are removed. Pages that need JavaScript to load may come back empty.</p>
          </div>
        )}

        {progress && (
          <div aria-live="polite">
            <div className="flex justify-between text-sm">
              <span>{progress.label}…</span>
              {progress.pct !== null && <span className="text-muted">{progress.pct}%</span>}
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-flame-soft">
              {progress.pct !== null ? (
                <div className="h-full bg-flame transition-[width]" style={{ width: `${progress.pct}%` }} />
              ) : (
                <div className="bar-indeterminate h-full w-2/5 bg-flame" />
              )}
            </div>
          </div>
        )}
        {error && <p role="alert" className="rounded-md bg-brick-soft px-3 py-2 text-sm text-brick">{error}</p>}
        {notice && <p className="rounded-md bg-teal-soft px-3 py-2 text-sm text-teal-dark">{notice}</p>}

        <button type="submit" disabled={!canSubmit} className="btn-primary">
          {mode === "url" ? "Scrape and add" : "Add to knowledge base"}
        </button>
      </form>
    </section>
  );
}
