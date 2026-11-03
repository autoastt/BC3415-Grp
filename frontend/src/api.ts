import type { KBSource, KBSourceDetail, LogResponse, Meta, Settings, StreamEvent } from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
const TOKEN_KEY = "scopeguard-admin-token";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

export const adminToken = {
  get: () => sessionStorage.getItem(TOKEN_KEY) ?? "",
  set: (t: string) => (t ? sessionStorage.setItem(TOKEN_KEY, t) : sessionStorage.removeItem(TOKEN_KEY)),
};

function authHeaders(): Record<string, string> {
  const t = adminToken.get();
  return t ? { "X-Admin-Token": t } : {};
}

async function errorFrom(res: Response): Promise<ApiError> {
  let message = res.status >= 500
    ? "The server isn't responding right now. Check that the backend is running, then try again."
    : `Request failed (HTTP ${res.status}).`;
  try {
    const body = await res.json();
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) {
      message = body.detail
        .map((d: { msg?: string; loc?: string[] }) => `${d.loc?.slice(-1)[0] ?? "field"}: ${d.msg ?? "invalid"}`)
        .join("; ");
    }
  } catch {
    /* non-JSON error body */
  }
  if (res.status === 401) message = "Enter the admin token to manage the knowledge base.";
  return new ApiError(message, res.status);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, { ...init, headers: { ...authHeaders(), ...(init.headers ?? {}) } });
  } catch {
    throw new ApiError("Can't reach the server. Check that the backend is running.", 0);
  }
  if (!res.ok) throw await errorFrom(res);
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  body: JSON.stringify(body),
  headers: { "Content-Type": "application/json" },
});

export const api = {
  meta: () => request<Meta>("/api/meta"),
  getSettings: () => request<Settings>("/api/settings"),
  putSettings: (s: Settings) => request<Settings>("/api/settings", { method: "PUT", ...json(s) }),
  listSources: () => request<KBSource[]>("/api/sources"),
  addText: (title: string, content: string) =>
    request<KBSource>("/api/sources/text", { method: "POST", ...json({ title, content }) }),
  addUrl: (url: string) => request<KBSource>("/api/sources/url", { method: "POST", ...json({ url }) }),
  getSource: (id: string) => request<KBSourceDetail>(`/api/sources/${id}`),
  updateSource: (id: string, content: string) =>
    request<KBSource>(`/api/sources/${id}`, { method: "PUT", ...json({ content }) }),
  deleteSource: (id: string) => request<{ deleted: string }>(`/api/sources/${id}`, { method: "DELETE" }),
  logs: (classification?: string) =>
    request<LogResponse>(`/api/logs?limit=100${classification ? `&classification=${classification}` : ""}`),
};

/** Upload with real progress for the transfer; processing time is reported via onStage. */
export function uploadFile(
  file: File,
  onProgress: (pct: number) => void,
  onStage: (stage: "uploading" | "processing") => void,
): Promise<KBSource> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);
    xhr.open("POST", BASE + "/api/sources/file");
    Object.entries(authHeaders()).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
    xhr.upload.onload = () => onStage("processing");
    xhr.onerror = () => reject(new ApiError("Can't reach the server. Check that the backend is running.", 0));
    xhr.onload = async () => {
      const res = new Response(xhr.responseText, { status: xhr.status });
      if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
      else reject(await errorFrom(res));
    };
    onStage("uploading");
    xhr.send(form);
  });
}

/** POST /api/chat and parse the NDJSON event stream. */
export async function streamChat(
  message: string,
  history: { role: "user" | "assistant"; content: string }[],
  onEvent: (e: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(BASE + "/api/chat", { method: "POST", signal, ...json({ message, history }) });
  } catch (e) {
    if ((e as Error).name === "AbortError") return;
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
  }
  if (!res.ok || !res.body) throw await errorFrom(res);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) if (line.trim()) onEvent(JSON.parse(line) as StreamEvent);
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer) as StreamEvent);
}
