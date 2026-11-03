import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import ChatTab from "./components/ChatTab";
import KnowledgeBaseTab from "./components/KnowledgeBaseTab";
import type { Meta, Settings } from "./types";

type Tab = "chat" | "kb";

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadSettings = useCallback(() => {
    api.getSettings().then(setSettings).catch((e: Error) => setLoadError(e.message));
  }, []);

  useEffect(() => {
    api.meta().then((m) => {
      setMeta(m);
      document.title = m.app_name;
    }).catch((e: Error) => setLoadError(e.message));
    loadSettings();
  }, [loadSettings]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "chat", label: "Chat" },
    { id: "kb", label: "Knowledge base" },
  ];

  return (
    <div className="flex h-[100dvh] flex-col">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span aria-hidden className="grid h-8 w-8 place-items-center rounded-lg bg-flame">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12.5l4.5 4.5L19 7.5" />
              </svg>
            </span>
            <div className="leading-tight">
              <p className="font-display text-lg font-bold tracking-tight">{meta?.app_name ?? "ScopeGuard"}</p>
              {settings && <p className="text-xs text-muted">Support for {settings.company_name}</p>}
            </div>
          </div>
          <nav className="flex gap-1" role="tablist" aria-label="Sections">
            {tabs.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={`rounded-md px-3.5 py-1.5 text-sm font-semibold transition-colors ${
                  tab === t.id ? "bg-flame-soft text-flame-dark" : "text-muted hover:text-ink"
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {loadError && (
        <div role="alert" className="border-b border-brick/30 bg-brick-soft px-6 py-2 text-sm text-brick">
          {loadError}
        </div>
      )}

      <main className="min-h-0 flex-1">
        {/* Both tabs stay mounted so the chat survives a trip to the knowledge base */}
        <div hidden={tab !== "chat"} className="h-full">
          <ChatTab settings={settings} maxChars={meta?.max_message_chars ?? 1000} />
        </div>
        <div hidden={tab !== "kb"} className="h-full overflow-y-auto">
          <KnowledgeBaseTab meta={meta} settings={settings} onSettingsSaved={setSettings} active={tab === "kb"} />
        </div>
      </main>
    </div>
  );
}
