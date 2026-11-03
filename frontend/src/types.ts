export type Classification = "in_scope" | "out_of_scope" | "no_answer" | "greeting" | "handoff" | "error";

export interface Source {
  source_id: string;
  title: string;
  type: string;
  chunk_index: number;
  score: number;
  snippet: string;
}

/** A link shown under an answer. URLs come from admin settings, never from the model. */
export interface ReplyLink {
  label: string;
  url: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: "streaming" | "done" | "error";
  classification?: Classification;
  sources?: Source[];
  handoff?: boolean;
  links?: ReplyLink[];
}

export type StreamEvent =
  | { type: "token"; text: string }
  | { type: "replace"; text: string }
  | { type: "done"; classification: Classification; sources: Source[]; handoff: boolean; links?: ReplyLink[] }
  | { type: "error"; message: string };

export interface KBSource {
  id: string;
  title: string;
  type: string;
  origin: string | null;
  chunk_count: number;
  created_at: string;
  updated_at?: string | null;
}

/** One source with its saved text. content is null for sources added before text was kept. */
export interface KBSourceDetail extends KBSource {
  content: string | null;
  editable: boolean;
}

export interface Settings {
  company_name: string;
  bot_name: string;
  allowed_topics: string[];
  support_contact: string;
  refusal_message: string;
  relevance_threshold: number;
  /** Shown as "Order online" when a customer wants to buy something. Empty turns it off. */
  order_url: string;
  quick_links: QuickLinkSetting[];
}

export interface QuickLinkSetting {
  label: string;
  url: string;
  keywords: string[];
}

export interface Meta {
  app_name: string;
  admin_required: boolean;
  max_upload_mb: number;
  max_message_chars: number;
}

export interface LogItem {
  id: number;
  ts: string;
  question: string;
  classification: string;
  reason: string | null;
  top_score: number | null;
}

export interface LogResponse {
  summary: Record<string, number>;
  items: LogItem[];
  /** "env": key from LOG_ENCRYPTION_KEY. "file": key generated in the data directory. */
  encryption?: { key_source: "env" | "file" };
}
