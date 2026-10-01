import { useCallback, useEffect, useState, type FormEvent } from "react";
import { adminToken, api, ApiError } from "../api";
import type { KBSource, Meta, Settings } from "../types";
import AddSource from "./AddSource";
import QuestionLog from "./QuestionLog";
import SettingsPanel from "./SettingsPanel";
import SourcesTable from "./SourcesTable";

interface Props {
  meta: Meta | null;
  settings: Settings | null;
  onSettingsSaved: (s: Settings) => void;
  active: boolean;
}

export default function KnowledgeBaseTab({ meta, settings, onSettingsSaved, active }: Props) {
  const [sources, setSources] = useState<KBSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsToken, setNeedsToken] = useState(false);
  const [tokenDraft, setTokenDraft] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(() => {
    setLoading(true);
    api.listSources()
      .then((s) => { setSources(s); setError(null); setNeedsToken(false); })
      .catch((e: ApiError) => { if (e.status === 401) setNeedsToken(true); else setError(e.message); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (active) { load(); setRefreshKey((k) => k + 1); }
  }, [active, load]);

  function saveToken(e: FormEvent) {
    e.preventDefault();
    adminToken.set(tokenDraft.trim());
    setTokenDraft("");
    load();
    setRefreshKey((k) => k + 1);
  }

  if (needsToken) {
    return (
      <div className="mx-auto max-w-md px-4 py-16">
        <form onSubmit={saveToken} className="panel p-6">
          <h2 className="h2">Admin access</h2>
          <p className="mt-1 text-sm text-muted">
            Managing the knowledge base needs the admin token set in the server's ADMIN_TOKEN variable.
          </p>
          <label htmlFor="admin-token" className="label mt-4">Admin token</label>
          <input id="admin-token" type="password" autoComplete="off" className="field" value={tokenDraft}
            onChange={(e) => setTokenDraft(e.target.value)} />
          <button type="submit" disabled={!tokenDraft.trim()} className="btn-primary mt-4 w-full">Unlock</button>
        </form>
      </div>
    );
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-5 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="min-w-0 space-y-5">
        <AddSource maxMb={meta?.max_upload_mb ?? 20} onAdded={(s) => setSources((xs) => [s, ...xs])} />
        {error && <p role="alert" className="rounded-md bg-brick-soft px-3 py-2 text-sm text-brick">{error}</p>}
        <SourcesTable sources={sources} loading={loading}
          onDeleted={(id) => setSources((xs) => xs.filter((x) => x.id !== id))} />
        <QuestionLog refreshKey={refreshKey} />
      </div>
      <div className="min-w-0 lg:sticky lg:top-6 lg:self-start">
        <SettingsPanel settings={settings} onSaved={onSettingsSaved} />
        {meta?.admin_required && (
          <button onClick={() => { adminToken.set(""); setNeedsToken(true); }} className="mt-3 text-sm text-muted underline hover:text-ink">
            Lock admin access
          </button>
        )}
      </div>
    </div>
  );
}
