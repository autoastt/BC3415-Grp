# ScopeGuard

A company-scoped customer support chatbot. It answers only from a knowledge base the company controls, declines everything else, says so when it doesn't know, and resists attempts to change its role or reveal its configuration.

The app name is set with `APP_NAME` in `.env`. Ships with a demo knowledge base for **Blaze Burger Co.**, a fictional burger chain (`sample_data/`).

## Quick start (Docker, one command)

```bash
cp .env.example .env        # add OPENAI_API_KEY and set ADMIN_TOKEN
docker compose up --build
```

Open http://localhost:8080. The sample data loads automatically on first start (`SEED_SAMPLE_DATA=true`). The Knowledge Base tab asks for your `ADMIN_TOKEN`.

## Local development

Requirements: Python 3.11+, Node 18+.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # fill in keys
python -m scripts.seed           # load sample data (add --reset to reload)
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173, proxies /api to :8000
```

On Windows (PowerShell), activate the virtual environment with `.venv\Scripts\activate` and copy the env file with `copy ..\.env.example .env`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | (required) | OpenAI key: generation, classifier and `openai` embeddings |
| `OPENAI_MODEL` | `gpt-4.1` | Answering model |
| `CLASSIFIER_MODEL` | `gpt-4o-mini` | Fast, cheap scope classifier |
| `EMBEDDING_PROVIDER` | `openai` | `openai` or `local` (sentence-transformers) |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | |
| `LOCAL_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Uncomment `sentence-transformers` in requirements first |
| `ADMIN_TOKEN` | (empty = no auth) | Protects source and settings endpoints. Set it for any public deployment. |
| `RELEVANCE_THRESHOLD` | `0.30` | Initial cosine-similarity gate. Once saved in the settings panel, the saved value wins. |
| `TOP_K` / `CHUNK_TOKENS` / `CHUNK_OVERLAP` | `5` / `500` / `50` | Retrieval and chunking |
| `HISTORY_MESSAGES` | `6` | Messages kept for follow-ups |
| `RATE_LIMIT_PER_MINUTE` | `20` | Per-IP limit on `/api/chat` |
| `MAX_UPLOAD_MB` / `MAX_SCRAPE_MB` / `MAX_MESSAGE_CHARS` | `20` / `5` / `1000` | Input limits |
| `TRUST_PROXY` | `false` | Use `X-Real-IP` for rate limiting (set `true` behind nginx; compose does this) |
| `ALLOW_PRIVATE_URLS` | `false` | Allow scraping localhost/private IPs (local testing only) |
| `DATA_DIR` | `./data` | ChromaDB, SQLite and settings |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated |

## How a message is handled

Each step is cheaper than the next, so most junk never costs a generation call.

1. **Deterministic guard (free).** Regexes catch obvious injection attempts ("ignore previous instructions", "reveal your prompt", fake `</context>` tags, zero-width-character tricks) and explicit requests for a human. Matches are answered immediately with no API call.
2. **Scope classifier (`gpt-4o-mini`, 8 output tokens).** Labels the message `IN_SCOPE`, `OUT_OF_SCOPE`, `GREETING` or `HUMAN_HANDOFF`, using the company name, allowed topics and the last few turns (so "how much is it?" works as a follow-up). Unexpected output or errors fail closed. Mixed requests ("tell me the price, then write Python") are labeled out of scope.
3. **Retrieval.** Top 5 chunks by cosine similarity. Short follow-ups are expanded with the previous user turn before embedding.
4. **Relevance gate.** If the best score is under the threshold, the bot returns the fallback message and the LLM is never called. Only chunks above the threshold are passed on, so weak matches can't seed a hallucination.
5. **Generation.** The answering model receives the spec's system prompt verbatim, with chunks inside `<context>`. The stream is watched for distinctive phrases from the system prompt; if any appear, output is cut and replaced with the refusal.
6. **Logging.** Every question is logged as `in_scope`, `out_of_scope`, `no_answer`, `greeting`, `handoff` or `error`, with the reason and best match score. If the model itself replies with the fallback sentence, that is logged as `no_answer` and no sources are shown.

**Human handoff** happens on explicit requests, and when the classifier sees something a person should handle (allergic reaction, food safety, payment disputes, strong frustration). The bot shares the support contact and doesn't try to resolve it.

## Design decisions

- **Streaming format is NDJSON** (`application/x-ndjson`), one JSON event per line: `token`, `replace`, `done` (classification, sources, handoff flag) or `error`. SSE is awkward with POST bodies; NDJSON is trivial to parse with `fetch`. Sources arrive in `done` because they depend on how the answer turned out.
- **Admin token on knowledge-base writes.** Without it, any visitor could upload a document saying "all burgers are free" and the bot would repeat it as fact. This is the most important control beyond the spec.
- **Knowledge-base content is untrusted too.** Chunks can't close the `<context>` block (tags are neutralized), the scraper removes hidden-by-CSS text (a common indirect-injection trick), and zero-width characters are stripped on ingest.
- **Scraper SSRF protection.** Only http(s); every redirect hop is re-resolved and rejected if it points at a private, loopback, link-local or metadata address; responses are size-capped.
- **Uploads** are checked by extension and by file signature (a renamed `.exe` won't pass as `.pdf`), and read in 1 MB pieces so a 20 MB limit actually holds.
- **Chunking is paragraph-aware.** Whole paragraphs are packed up to 500 tokens with a 50-token overlap; oversized paragraphs fall back to a sliding window. CSV rows become self-describing lines (`Item: Classic; Price: 9.90`) so a retrieved row still makes sense without its header.
- **One collection per embedding model.** Vectors from different models aren't comparable, so switching provider starts a fresh collection rather than silently returning nonsense. Re-add sources after switching.
- **Threshold tuning.** 0.30 suits `text-embedding-3-small` with the sample corpus. Watch the "Not in knowledge base" view in the question log: if good questions land there with scores just below the threshold, lower it a little; if off-base answers appear, raise it. The gate is applied twice -- the best score decides whether the LLM is called at all, and the same number then filters which chunks are passed on. A question can therefore clear the gate on one chunk while the chunk that actually holds the answer is filtered out just below it, which is what 0.35 did to "Is the Garden Ember vegan?" (best 0.382, menu chunk 0.342).

## Testing

```bash
cd backend

# 1. Offline suite: no API keys needed (LLM mocked, hash embedder). 56 tests.
pytest -q

# 2a. Live behaviour evaluation against a local dev server (uvicorn on :8000)
python -m scripts.seed
python -m tests.eval_behavior --base http://localhost:8000

# 2b. ...or against the Docker stack. Compose publishes only the frontend's
# 8080, so the evaluation goes through nginx; the backend's 8000 is internal.
# Sample data is already seeded by the entrypoint.
python -m tests.eval_behavior --base http://localhost:8080
```

`--delay` (default 3.1s) spaces requests out for the app's own per-IP limiter. Each
message costs 2-3 OpenAI calls, so on a low-tier API key the account's own rate limit
binds first; raise the delay if you see the client backing off on `429`s.

### Running on an OpenAI account with no payment method

Such accounts get **50 requests per day per chat model**, counted daily rather than
per minute, so no amount of `--delay` helps once the budget is gone. Two things follow
from how the quota is shaped:

- **Each model has its own bucket**, so the classifier and the answering model never
  compete. Spreading them across two models is what makes the free tier workable;
  `gpt-4o-mini` and `gpt-4.1` are two separate 50/day allowances.
- **Embeddings are not the constraint** -- `text-embedding-3-small` allows 2000/day, so
  switching to `EMBEDDING_PROVIDER=local` buys nothing here.

The classifier runs on every message, so **50 messages per day** is the practical
ceiling, and one full `eval_behavior` run costs about 21 of them. If the classifier
starts returning errors, check the daily budget before suspecting the code:

```bash
curl -s -o /dev/null -D- https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o-mini","max_completion_tokens":1,"messages":[{"role":"user","content":"hi"}]}' \
  | grep -i x-ratelimit
```

The offline suite checks chunking, cleaning, CSV handling, file validation, SSRF blocking, HTML sanitizing, injection and handoff detection, history normalization, prompt-boundary escaping and rate limiting. Through the real API it also checks that off-topic and jailbreak messages make **zero generation calls**, injection patterns make **zero calls of any kind**, below-threshold questions never reach the LLM, leaked prompt text gets replaced, admin auth is enforced, and deleting a source removes its chunks from retrieval.

The live evaluation runs four groups and exits non-zero on any failure:

1. **In scope** (7): answered with sources and the expected fact (e.g. "$9.90", "250 points").
2. **No answer** (2): in the domain but not in the knowledge base. Must return the fallback, not a guess.
3. **Off topic** (7): LeetCode Two Sum, a poem, trivia, math, competitor comparison, homework, and a mixed in/out request. Must be declined.
4. **Jailbreak** (7): prompt extraction, role change, "repeat everything above", fake authorization, "translate your rules", fake SYSTEM messages, the grandma trick. Must be declined with no prompt text leaked.

## API

| Method | Path | Auth | Body |
|---|---|---|---|
| POST | `/api/chat` | public, rate-limited | `{ message, history: [{role, content}] }` → NDJSON stream |
| POST | `/api/sources/text` | admin | `{ title, content }` |
| POST | `/api/sources/file` | admin | multipart `file` |
| POST | `/api/sources/url` | admin | `{ url }` |
| GET | `/api/sources` | admin | |
| DELETE | `/api/sources/{id}` | admin | |
| GET / PUT | `/api/settings` | GET public, PUT admin | |
| GET | `/api/logs?classification=no_answer` | admin | question log |
| GET | `/api/meta`, `/api/health` | public | |

Admin requests send `X-Admin-Token`.

## Known limitations

- **Single process.** The rate limiter is in memory, so run one worker (the entrypoint does). For several workers, move it to Redis.
- **History is client-supplied.** A crafted client could send a fake assistant turn. The impact is limited because every turn is still classified and every answer still needs retrieved context, but a production deployment should store conversations server-side keyed by session.
- **DNS rebinding.** The scraper checks resolved IPs before connecting, but a hostile DNS server could change the answer between check and connect. Scraping is admin-only, which keeps the risk low.
- **JavaScript-rendered pages** scrape as empty. Paste the text or upload a file instead.
- Ingestion runs inside the request. Very large PDFs may take a while; a job queue would be the next step.
