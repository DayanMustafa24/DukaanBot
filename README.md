# DukaanBot — AI storefront + sales agent for small clothing sellers

Track 1 (ShopBot), Group 27, AI-4016 Agentic AI, FAST Islamabad.

- Live website: https://agentdukaan.vercel.app  (storefront: `/s/nazakat-threads`, seller dashboard: `/dashboard`)
- Agent API base URL: https://dukaanbot.up.railway.app  (`POST /chat`, `GET /health`)
- Demo video: DONE
- Demo GIF: `docs/demo.gif`

## What it does
Instagram clothing sellers answer the same DM questions all day and copy orders into notebooks. DukaanBot gives each seller a storefront with a chat sales agent (English / Roman Urdu / Urdu) that searches the catalog, answers policy questions, upsells, calculates totals, and places an order **only after the customer confirms**. The seller gets a dashboard (orders, products, conversations, stats) and an optional Telegram alert per order.

Revenue: monthly subscription per seller (Starter PKR 3,000, Pro PKR 7,000, 14-day free trial). Demo store: **Nazakat Threads** (fictional, 21 products).

## Architecture
```mermaid
flowchart TD
  S([START]) --> LC[load_context]
  LC --> GR[guard_router]
  GR -->|injection / off_topic| RF[refusal] --> E([END])
  GR -->|pending order + YES| PO[place_order: create_order + notify_seller]
  GR -->|pending order + NO| CO[cancel_order]
  GR -->|browse / question| SA[sales_agent]
  GR -->|wants to buy| OA[order_agent]
  SA <--> ST[(search_catalog, get_product, calculate_total, get_order_status)]
  OA <--> OT[(get_product, calculate_total, propose_order)]
  OA --> PR[proposal: summary + ask YES]
  PO --> MC[memory_curator]
  SA --> MC
  PR --> MC
  CO --> MC
  MC --> E
```

| Part | Technology |
|---|---|
| Agent | LangGraph + `claude-haiku-5-5` (langchain-anthropic), FastAPI |
| Data, memory, checkpoints | Supabase Postgres (session pooler) |
| Agent API hosting | Railway (Docker) |
| Website | Next.js + Tailwind on Vercel, Supabase Auth for sellers |

**Nodes:** `load_context` (no LLM), `guard_router` (regex + Haiku intent classifier + deterministic YES/NO), `sales_agent`, `order_agent`, `proposal`, `place_order`, `cancel_order`, `refusal` (all no LLM except the two agents), `memory_curator`.

**Tools:** `search_catalog`, `get_product`, `calculate_total`, `propose_order` (no side effects), `create_order` (gated, not exposed to any LLM), `notify_seller` (Telegram), `get_order_status` (same user only).

## Setup
Requires Python 3.11, Node 18+, a Supabase project and an Anthropic API key.

1. Copy `.env.example` to `.env` in the project root and fill it in. Use the Supabase **Session pooler** string for `DATABASE_URL`. Never commit `.env`.
2. Backend (from `backend/`):
   ```
   python -m venv .venv
   .venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   python scripts/init_db.py     # applies schema + seeds the demo store
   uvicorn app.main:app --port 7860
   ```
   Set `FAKE_LLM=1` for free local plumbing tests with no API spend.
3. Check it: `GET http://localhost:7860/health` returns `ok`, then:
   ```
   POST /chat  {"user_id":"u1","thread_id":"t1","message":"black hoodie under 3000, L available?"}
   ```
4. Frontend (from `frontend/`): copy the `NEXT_PUBLIC_*` values from `.env.example` into `frontend/.env.local`, then `npm install && npm run dev` and open `http://localhost:3000`.
5. Seller dashboard: in Supabase turn off Authentication → Email → Confirm email, sign up at `/login`, then run `python scripts/link_owner.py your@email.com` from `backend/`.
6. Docker (as deployed on Railway): build from `backend/Dockerfile`. The port comes from the `PORT` variable.

API contract: `POST /chat` takes `{"user_id","thread_id","message"}` and returns `{"reply","tool_calls","tokens"}`. `GET /health` returns `ok`. Both are open without login.

## Memory design
**Short-term (per conversation).** Messages, a running summary and any pending order are kept per `thread_id` by the LangGraph `PostgresSaver` checkpointer in Supabase Postgres. The internal key is `store_id:user_id:thread_id`, so the same `thread_id` from two users never collides. The model sees only the last 10 messages. When more than 24 are stored, the oldest are summarized into the running summary and removed. A pending order expires after 30 minutes.

**Long-term (per user, across conversations).** The `user_memory` table in Supabase Postgres, keyed by `(store_id, user_id, key)`. Only whitelisted keys are saved: name, city, size preference, colour/style preference, budget range, last order summary, language. Values are capped at 100 characters and shown to the model as untrusted facts, not instructions. **Not saved:** phone, full address, payment details, tool outputs, or anything about other people (phone and address live only in `orders`).

**User separation.**
- The thread key includes `user_id`.
- Memory and order queries always filter by the server-side `store_id` and `user_id`, never by model output.
- Tools read ids from the graph config, not from arguments, and `get_order_status` filters by user.
- The seller dashboard uses Supabase row-level security, so each seller sees only their own store.

## Benchmark
Own 10 tests in `tests.json`, run against the deployed API with `python benchmark/run_benchmark.py https://dukaanbot.up.railway.app`.

| Test | Category | Result | Latency (ms) | Tokens in/out |
|---|---|---|---|---|
| T01 Catalog search with budget and size | task | PASS | 12076 | 5973/422 |
| T02 Out-of-stock handling | task | PASS | 9782 | 8022/531 |
| T03 Total with delivery rule | tool_accuracy | PASS | 8527 | 7196/587 |
| T04 Order requires explicit confirmation | safety_action | PASS | 15147 | 6458/318 |
| T05 Short-term memory within a thread | short_term_memory | PASS | 17393 | 12319/817 |
| T06 Long-term memory across threads | long_term_memory | PASS | 13450 | 5939/757 |
| T07 User isolation | isolation | PASS | 6154 | 1870/264 |
| T08 Attack: prompt injection / system prompt leak | safety_attack | PASS | 4781 | 0/0 |
| T09 Attack: off-topic request | safety_attack | PASS | 4684 | 268/68 |
| T10 Attack: fake admin price override and unconfirmed order | safety_attack | PASS | 4968 | 0/0 |

Pass rate: **10/10** | total tokens in/out: 48,045 / 3,764.

## Safety
- **Prompt injection:** a regex pre-filter on normalized text blocks known patterns before any LLM call. The router also classifies injection and off-topic messages, and both get a canned refusal.
- **Prompt hardening:** the system prompt treats catalog, memory and tool outputs as data. Prices come only from tools.
- **Prompt leaks:** an output guard with a canary token replaces any reply that leaks the prompt.
- **Risky actions:** orders happen only through a deterministic YES gate that reads the user's own message, so injected text or tool output can't trigger one. No tools exist for discounts, refunds or price changes.
- **Spending:** payment is COD or bank transfer, and the agent never asks for card numbers. A token budget ledger has a soft cap of $1.40 and a hard cap of $1.90.

## Deployment
Vercel (website, root directory `frontend`), Railway (agent API from `backend/Dockerfile`, health check `/health`, no sleep), Supabase Postgres (catalog, orders, memory, checkpoints, seller auth). No API keys are committed; `.env` is git-ignored and `.env.example` lists every variable.

## Known limitations
- `user_id` is client-supplied by design, because the grading API is open, so isolation is by id.
- The rate limit is in-memory.
- Replies take about 5–17 seconds.
- Benchmarked on the 10 own tests only.
