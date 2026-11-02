# ScopeGuard

A company-scoped customer support chatbot. It answers only from a knowledge base the company controls, declines everything else, says so when it doesn't know, and resists attempts to change its role or reveal its configuration.

The app name is set with `APP_NAME` in `.env`. Ships with a demo knowledge base for **Blaze Burger Co.**, a fictional burger chain (`sample_data/`), and a matching sample company website (`frontend/public/sample-site.html`) that the bot links to.

## Problem statement

Blaze Burger Co. runs two outlets in Singapore and a delivery service. Like Shopify in the assignment's case study, most customer contacts are the same few questions: prices, opening hours, delivery fees, refunds and loyalty points. Answering them by phone, email or social media takes staff away from the kitchen and counter, doesn't happen after hours, and gives different answers depending on who replies.

Off-the-shelf chatbots answer instantly but bring new problems. They make up prices and policies, can be talked into off-topic or harmful replies, and often store customer messages, which can include phone numbers, order details and allergies, with little protection.

**The problem we solve:** how can a small food business give customers instant, accurate, round-the-clock answers from its own policies, point them to the right page to order or help themselves, and hand cases a person must handle to staff, without hallucinations, misuse or careless handling of personal data?

## Business value

| Benefit | How ScopeGuard delivers it |
|---|---|
| **Instant answers, 24/7** | Routine questions are answered in seconds, with the sources shown, instead of waiting for staff. |
| **Lower support cost** | Answered questions cost 2 chat calls plus 1 embedding call: roughly half a US cent at OpenAI's 2025 list prices (check current pricing before quoting it). Off-topic questions cost one cheap classifier call, and blocked jailbreaks cost nothing. |
| **Fewer wrong answers** | The bot answers only from company documents and says "I don't have that information" instead of guessing. |
| **Questions turn into orders** | When a customer shows they want to buy, the reply includes an **Order online** link. Other replies link to the matching self-service page (menu, outlets, rewards, refund form). |
| **Staff time goes where it's needed** | Allergic reactions, payment disputes and angry customers go straight to a person with the support contact. |
| **Knows what's missing** | The "Not in knowledge base" log shows real questions the bot couldn't answer, so staff know which document to add next. |
| **Trust and compliance** | Customer questions are encrypted at rest and IP addresses are stored only as a one-way hash. This supports the PDPA's requirement that organisations make reasonable security arrangements for personal data. |

**Illustrative example** (assumed numbers, not measured): if staff spend 3 minutes on each routine question and the bot answers 300 of them a week, that's about 15 staff hours a week back, for under US$2 of API cost.

**KPIs to track** (targets are illustrative):

| KPI | Where to see it | Target |
|---|---|---|
| Answer rate: answered ÷ (all questions − greetings) | Question log summary | 70% or more |
| No-answer rate | "Not in knowledge base" view | Falling week on week as content is added |
| Handoff rate | "Handed off" view | Only cases a person must handle |
| Declined rate | "Declined" view | Stable; spikes mean misuse or topics set too narrow |
| Cost per answered question | OpenAI usage dashboard ÷ answered count | Under 1 US cent |

## Team and roles

> **Edit before submitting:** replace `[Name]` with each member's name, and adjust the responsibilities so they match who actually built what.

| Member | Role | Responsible for | Video segment |
|---|---|---|---|
| [Name] | Project lead and architecture | Problem framing, business case, system design, Docker setup, README | 1: problem, solution, tech stack |
| [Name] | Knowledge base and retrieval | Ingestion and chunking (`ingestion.py`), embeddings, ChromaDB (`vectorstore.py`), web scraper, sample data | 2: how documents get into RAG |
| [Name] | Chat pipeline and LLM | Answer pipeline (`rag.py`), OpenAI calls and classifier (`llm.py`), system prompt (`prompts.py`), helpful links (`links.py`) | 3: how a question is answered |
| [Name] | Safety and privacy | Injection guard (`guard.py`), admin auth, rate limiting, log encryption (`log_crypto.py`) | 4: guardrails and handoff |
| [Name] | Frontend, testing and evaluation | React UI, sample company website, offline tests, live evaluation script, question log | 5: testing, insights, business value |

The demo video plan is in [docs/VIDEO_WALKTHROUGH.md](docs/VIDEO_WALKTHROUGH.md). Known gaps and next steps are in [docs/GAPS_AND_FUTURE_WORK.md](docs/GAPS_AND_FUTURE_WORK.md).

## Quick start (Docker, one command)

```bash
cp .env.example .env        # add OPENAI_API_KEY, set ADMIN_TOKEN and LOG_ENCRYPTION_KEY
docker compose up --build
```

Open http://localhost:8080. The sample data loads automatically on first start (`SEED_SAMPLE_DATA=true`). The Knowledge Base tab asks for your `ADMIN_TOKEN`. The sample company website is at http://localhost:8080/sample-site.html.

Generate a `LOG_ENCRYPTION_KEY` with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

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
| `LOG_ENCRYPTION_KEY` | (empty = key generated in `DATA_DIR`) | Fernet key that encrypts questions in the question log. Comma-separate several keys to rotate (the first encrypts, all decrypt). Set it for any real deployment. |
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
6. **Helpful links (free).** Answers and "don't know" fallbacks get up to 3 links, never refusals or handoffs. If the customer wants to buy something ("I'd like two Classic Blazes", "how do I order?") or asks about delivery, the first link is **Order online**. Other links are matched by keyword (a price question gets "Full menu and prices"; a refund question gets "Refund request form"). Admins edit the links under **Bot settings → Helpful links**. By default they point at the bundled sample website.
7. **Logging.** Every question is logged as `in_scope`, `out_of_scope`, `no_answer`, `greeting`, `handoff` or `error`, with the reason and best match score. The question text is encrypted and the visitor's IP is stored only as a keyed hash. If the model itself replies with the fallback or the refusal, that is logged as `no_answer` or `out_of_scope` and no sources are shown. This works in any language: a second system message asks the model to start those replies with `[NO_ANSWER]` or `[REFUSED]`, and the server strips the marker before the customer sees it. The English sentences are still checked in case the model forgets the marker.

**Human handoff** happens on explicit requests, and when the classifier sees something a person should handle (allergic reaction, food safety, payment disputes, strong frustration). The bot shares the support contact and doesn't try to resolve it.

## Design decisions

- **Streaming format is NDJSON** (`application/x-ndjson`), one JSON event per line: `token`, `replace`, `done` (classification, sources, handoff flag, links) or `error`. SSE is awkward with POST bodies; NDJSON is trivial to parse with `fetch`. Sources arrive in `done` because they depend on how the answer turned out.
- **Admin token on knowledge-base writes.** Without it, any visitor could upload a document saying "all burgers are free" and the bot would repeat it as fact. This is the most important control beyond the spec.
- **Links come from an allowlist, never from the model.** The model doesn't write URLs. Links are picked by code from the admin's settings and sent as structured data in the `done` event, so a reply can't contain an invented link or a phishing link planted by a prompt injection. URLs must be `https://`, `http://` or a path on this site (no `javascript:` or `//other-host`), and this is checked both when settings are saved and again in the browser before a link is rendered.
- **The question log is encrypted at rest.** Customers type phone numbers, order numbers and allergies into support chats. Questions are encrypted with Fernet (AES-128-CBC with an HMAC-SHA256 integrity check) before they reach SQLite and decrypted only for the admin log view. Client IPs are replaced with a keyed one-way hash, so repeat visitors can still be counted but the IP can't be recovered. A copied `app.db` or backup reveals neither. Rows logged before encryption was added are encrypted automatically at startup. A bad key stops the app at startup rather than failing on the first message.
- **Knowledge-base content is untrusted too.** Chunks can't close the `<context>` block (tags are neutralized), the scraper removes hidden-by-CSS text (a common indirect-injection trick), and zero-width characters are stripped on ingest.
- **Scraper SSRF protection.** Only http(s); every redirect hop is re-resolved and rejected if it points at a private, loopback, link-local or metadata address; responses are size-capped.
- **Uploads** are checked by extension and by file signature (a renamed `.exe` won't pass as `.pdf`), and read in 1 MB pieces so a 20 MB limit actually holds.
- **Chunking is paragraph-aware.** Whole paragraphs are packed up to 500 tokens with a 50-token overlap; oversized paragraphs fall back to a sliding window. CSV rows become self-describing lines (`Item: Classic; Price: 9.90`) so a retrieved row still makes sense without its header.
- **One collection per embedding model.** Vectors from different models aren't comparable, so switching provider starts a fresh collection rather than silently returning nonsense. Re-add sources after switching.
- **Threshold tuning.** 0.30 suits `text-embedding-3-small` with the sample corpus. Watch the "Not in knowledge base" view in the question log: if good questions land there with scores just below the threshold, lower it a little; if off-base answers appear, raise it. The gate is applied twice -- the best score decides whether the LLM is called at all, and the same number then filters which chunks are passed on. A question can therefore clear the gate on one chunk while the chunk that actually holds the answer is filtered out just below it, which is what 0.35 did to "Is the Garden Ember vegan?" (best 0.382, menu chunk 0.342).

## Testing

```bash
cd backend

# 1. Offline suite: no API keys needed (LLM mocked, hash embedder). 110 tests.
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

The offline suite checks chunking, cleaning, CSV handling, file validation, SSRF blocking, HTML sanitizing, injection and handoff detection, history normalization, reply-marker stripping, prompt-boundary escaping, rate limiting, purchase-intent and keyword link matching, link URL safety, and log encryption (round trip, wrong key, IP hashing, encrypting old plaintext rows). Through the real API it also checks that replies to purchase questions carry the order link while refusals and handoffs carry none, that no question is stored in plaintext, and that off-topic and jailbreak messages make **zero generation calls**, injection patterns make **zero calls of any kind**, below-threshold questions never reach the LLM, leaked prompt text gets replaced, translated fallbacks and refusals are logged correctly, admin auth is enforced, and deleting a source removes its chunks from retrieval.

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
| GET | `/api/logs?classification=no_answer` | admin | question log (decrypted), plus `encryption.key_source` (`env` or `file`) |
| GET | `/api/meta`, `/api/health` | public | |

Admin requests send `X-Admin-Token`.

## Known limitations

- **Single process.** The rate limiter is in memory, so run one worker (the entrypoint does). For several workers, move it to Redis.
- **History is client-supplied.** A crafted client could send a fake assistant turn. The impact is limited because every turn is still classified and every answer still needs retrieved context, but a production deployment should store conversations server-side keyed by session.
- **DNS rebinding.** The scraper checks resolved IPs before connecting, but a hostile DNS server could change the answer between check and connect. Scraping is admin-only, which keeps the risk low.
- **JavaScript-rendered pages** scrape as empty. Paste the text or upload a file instead.
- Ingestion runs inside the request. Very large PDFs may take a while; a job queue would be the next step.
- **Generated encryption key.** Without `LOG_ENCRYPTION_KEY`, the key is written to `DATA_DIR/log_encryption.key`, next to the database. That protects a copied `app.db` but not a copy of the whole data folder. Set the variable (ideally from a secrets manager) for real deployments, and keep a copy of the key: losing it makes old log entries unreadable.
- **Link matching is keyword-based.** It's predictable and free, but it can miss unusual phrasings or add a loosely related link. The sample website's menu and policies are hard-coded to match `sample_data/`, so update both together.
