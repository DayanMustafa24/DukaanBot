# STATE (update after every step; keep it short)

Last updated: Mon 23 Nov 2026, ~16:30 PKT. Hard deadline today 23:59 PKT. Target: submit by 23:00.
Read `ARCHITECTURE.md` first for the full design.

## DONE (written, NOT yet run anywhere: expect small fixes on first run)
- Planning docs: ARCHITECTURE.md, PRODUCT_CANVAS.md, tests.json, .env.example, README skeleton.
- Backend (`backend/`): schema.sql (+RLS), seed (21 products), config/db/stores/usage/budget, tools (search_catalog, get_product, calculate_total, propose_order, get_order_status, gated create_order, notify_seller), safety (injection regex, output guard), long-term memory, LangGraph graph (load_context -> guard_router -> sales_agent | order_agent <-> run_tools -> proposal | place_order | cancel_order | refusal -> memory_curator), FastAPI (`/chat`, `/health`, `/store/{slug}`, `/store/{slug}/orders`).
- Scripts: `init_db.py`, `link_owner.py`, `get_telegram_chat_id.py`. Deploy: `Dockerfile`, `.dockerignore`, `HF_SPACE_README.md`.
- `benchmark/run_benchmark.py` (reads tests.json, writes results.md/json).
- Frontend storefront: `/s/[slug]` product grid + chat widget (tool chips, new chat, persisted thread).
- Seller dashboard (written, unrun): `/login`, `/dashboard` (stats), `/orders` (status update, cancel restores stock), `/products` (price/stock edit, active toggle, add), `/conversations` (transcripts + tool calls), `/settings`. Supabase client + RLS; needs NEXT_PUBLIC_SUPABASE_URL/ANON_KEY in frontend/.env.local, a Supabase user, and `python scripts/link_owner.py <email>`.
- Fixed after first run: `tools/__init__.py` set of unhashable StructuredTool -> list; `init_db.py` now closes the pool.

## Implementation notes (differences from ARCHITECTURE.md)
- `confirm_gate` = the fast path inside `guard_router` (deterministic YES/NO reading) + nodes `place_order` / `cancel_order`. Pending order expires after 30 min.
- After `propose_order` succeeds the reply is the tool's summary text (node `proposal`), no extra LLM call.
- Past turns are compressed to plain Human/AI text for the LLM; only the current turn keeps tool blocks.
- Python 3.10+ required (3.11 recommended).

## NOW: first run on user machine (target 16:30-17:15)
From `backend/` (PowerShell):
1. `python -m venv .venv` ; `.venv\Scripts\activate` ; `pip install -r requirements.txt`
2. `.env` must be in the project root (or backend/). Needs DATABASE_URL (Session pooler), ANTHROPIC_API_KEY.
3. `python scripts/init_db.py` (applies schema + seeds demo store)
4. `$env:FAKE_LLM="1"` ; `uvicorn app.main:app --port 7860`
5. Another terminal: `Invoke-RestMethod http://localhost:7860/health` and POST /chat (see README); then `$env:FAKE_LLM="0"`, restart, run `python ..\benchmark\run_benchmark.py http://localhost:7860 --only T01,T04,T06`.
Paste any traceback to Claude; fix, then continue.

## NEXT (in order)
- Phase 1b: fix first-run errors; pass T01-T10 locally with real model (spend <= ~$0.20).
- Phase 2: deploy backend to Hugging Face Space (Docker, port 7860; copy HF_SPACE_README.md as README.md in the Space repo; add secrets); test public /health and /chat.
- Phase 3: deploy frontend to Vercel (root dir `frontend`, env vars), set CORS_ORIGINS on the Space. Dashboard code already written; test it locally first.
- Phase 4: full benchmark run on the deployed URL; README benchmark table; architecture.png; demo GIF.
- Phase 5: demo video (2-3 min), canvas photo, GitHub push (no keys), form + Classroom.
- Phase 6: submit by 23:00. Keep services live until Wed 25 Nov.

## Cut rules
- Dashboard minimal if behind at 20:45: orders table + products list only.
- Never spend real tokens on dev loops; `FAKE_LLM=1` for plumbing.
- Keep >= $1.20 of the $2 for the official evaluation.

## User actions
1. Put `.env` in the project root; confirm DATABASE_URL is the Session pooler string.
2. Run the first-run steps above; send me errors.
3. Git: init, commit, add remote, push (commands in chat).
4. Telegram (optional, not blocking): @BotFather -> /newbot -> token into `TELEGRAM_BOT_TOKEN`; open the bot, press Start, send "hi"; `python scripts/get_telegram_chat_id.py`; put id in `SEED_TELEGRAM_CHAT_ID`; rerun `init_db.py`.
5. Create Hugging Face account + Space (Docker, blank) when we reach Phase 2.
6. Group members on the canvas, photo to Drive.

## Open questions
- Instructor's 5 common attack tests (add to tests.json/benchmark).
- Haiku price per 1M tokens (for PRICE_* in .env).

## Progress log
- 15:30 planning docs done.
- 16:30 backend + storefront code written (unrun). Dashboard not started.
