import { useEffect, useState, type FormEvent, type KeyboardEvent } from "react";
import { api } from "../api";
import type { QuickLinkSetting, Settings } from "../types";

/** Helpful links are edited as text, one per line: "Label | URL | keyword, keyword" */
const linksToText = (links: QuickLinkSetting[]) =>
  links.map((l) => `${l.label} | ${l.url} | ${l.keywords.join(", ")}`).join("\n");

function parseLinks(text: string): { links: QuickLinkSetting[] } | { error: string } {
  const links: QuickLinkSetting[] = [];
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  for (const [i, line] of lines.entries()) {
    const [label = "", url = "", words = "", ...extra] = line.split("|").map((p) => p.trim());
    const keywords = words.split(",").map((k) => k.trim()).filter(Boolean);
    if (!label || !url || !keywords.length || extra.length) {
      return { error: `Helpful links, line ${i + 1}: use "Label | URL | keyword, keyword".` };
    }
    links.push({ label, url, keywords });
  }
  return { links };
}

export default function SettingsPanel({ settings, onSaved }: { settings: Settings | null; onSaved: (s: Settings) => void }) {
  const [form, setForm] = useState<Settings | null>(settings);
  const [topicDraft, setTopicDraft] = useState("");
  const [linksText, setLinksText] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    setForm(settings);
    setLinksText(linksToText(settings?.quick_links ?? []));
  }, [settings]);
  if (!form) return <section className="panel p-5 text-muted">Loading settings…</section>;

  const set = <K extends keyof Settings>(k: K, v: Settings[K]) => { setForm({ ...form, [k]: v }); setMsg(null); };

  function addTopic() {
    const parts = topicDraft.split(",").map((t) => t.trim()).filter(Boolean);
    if (!parts.length || !form) return;
    set("allowed_topics", Array.from(new Set([...form.allowed_topics, ...parts])));
    setTopicDraft("");
  }

  function onTopicKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addTopic(); }
    if (e.key === "Backspace" && !topicDraft && form) set("allowed_topics", form.allowed_topics.slice(0, -1));
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    const parsed = parseLinks(linksText);
    if ("error" in parsed) {
      setMsg({ ok: false, text: parsed.error });
      return;
    }
    setSaving(true);
    try {
      const saved = await api.putSettings({ ...form, quick_links: parsed.links });
      onSaved(saved);
      setMsg({ ok: true, text: "Settings saved. New chats use them right away." });
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel p-5">
      <h2 className="h2">Bot settings</h2>
      <form onSubmit={save} className="mt-4 space-y-4">
        <div>
          <label className="label" htmlFor="s-company">Company name</label>
          <input id="s-company" className="field" value={form.company_name} onChange={(e) => set("company_name", e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="s-bot">Bot name</label>
          <input id="s-bot" className="field" value={form.bot_name} onChange={(e) => set("bot_name", e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="s-topics">Allowed topics</label>
          <div className="field flex min-h-[44px] flex-wrap items-center gap-1.5 py-1.5">
            {form.allowed_topics.map((t) => (
              <span key={t} className="inline-flex items-center gap-1 rounded-full bg-flame-soft py-0.5 pl-2.5 pr-1 text-sm text-flame-dark">
                {t}
                <button type="button" aria-label={`Remove ${t}`} className="grid h-5 w-5 place-items-center rounded-full hover:bg-flame/15"
                  onClick={() => set("allowed_topics", form.allowed_topics.filter((x) => x !== t))}>×</button>
              </span>
            ))}
            <input id="s-topics" value={topicDraft} onChange={(e) => setTopicDraft(e.target.value)} onKeyDown={onTopicKey}
              onBlur={addTopic} placeholder={form.allowed_topics.length ? "Add another" : "menu, orders, refunds"}
              className="min-w-[8rem] flex-1 bg-transparent py-0.5 outline-none" />
          </div>
          <p className="mt-1 text-xs text-muted">Press Enter or comma to add. Questions outside these are declined.</p>
        </div>
        <div>
          <label className="label" htmlFor="s-contact">Support contact</label>
          <input id="s-contact" className="field" value={form.support_contact} onChange={(e) => set("support_contact", e.target.value)}
            placeholder="support@company.com" />
          <p className="mt-1 text-xs text-muted">Shown when the bot can't answer or a customer asks for a person.</p>
        </div>
        <div>
          <label className="label" htmlFor="s-refusal">Off-topic reply</label>
          <textarea id="s-refusal" className="field min-h-[88px]" value={form.refusal_message}
            onChange={(e) => set("refusal_message", e.target.value)} />
          <p className="mt-1 text-xs text-muted">You can use {"{company_name}"}, {"{bot_name}"} and {"{support_contact}"}.</p>
        </div>
        <details className="rounded-md border border-line px-3 py-2">
          <summary className="cursor-pointer text-sm font-medium">Helpful links</summary>
          <div className="mt-3 space-y-3">
            <div>
              <label className="label" htmlFor="s-order-url">Online ordering link</label>
              <input id="s-order-url" className="field" value={form.order_url ?? ""} placeholder="https://order.company.com"
                onChange={(e) => set("order_url", e.target.value)} />
              <p className="mt-1 text-xs text-muted">Shown as "Order online" when a customer wants to buy something. Leave empty to turn it off.</p>
            </div>
            <div>
              <label className="label" htmlFor="s-links">Self-service links</label>
              <textarea id="s-links" className="field min-h-[150px] font-mono text-xs" value={linksText} spellCheck={false}
                onChange={(e) => { setLinksText(e.target.value); setMsg(null); }} />
              <p className="mt-1 text-xs text-muted">
                One per line: Label | URL | keywords. A link appears under an answer when the question contains one of its
                keywords (up to 3 links per answer). URLs must start with https://, http:// or /.
              </p>
            </div>
          </div>
        </details>
        <details className="rounded-md border border-line px-3 py-2">
          <summary className="cursor-pointer text-sm font-medium">Answer strictness</summary>
          <div className="mt-3">
            <label className="label" htmlFor="s-threshold">
              Minimum match score: <span className="tabular-nums">{form.relevance_threshold.toFixed(2)}</span>
            </label>
            <input id="s-threshold" type="range" min={0} max={0.9} step={0.01} value={form.relevance_threshold}
              onChange={(e) => set("relevance_threshold", Number(e.target.value))} className="w-full accent-flame" />
            <p className="mt-1 text-xs text-muted">
              Higher means the bot says "I don't have that information" more often instead of answering from a weak match.
              Default 0.30.
            </p>
          </div>
        </details>
        {msg && (
          <p role={msg.ok ? "status" : "alert"}
            className={`rounded-md px-3 py-2 text-sm ${msg.ok ? "bg-teal-soft text-teal-dark" : "bg-brick-soft text-brick"}`}>
            {msg.text}
          </p>
        )}
        <button type="submit" disabled={saving} className="btn-primary">{saving ? "Saving…" : "Save settings"}</button>
      </form>
    </section>
  );
}
