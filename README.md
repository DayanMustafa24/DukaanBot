# DukaanBot — AI storefront + sales agent for small clothing sellers

Track 1 (ShopBot), Group 27, AI-4016 Agentic AI, FAST Islamabad.

- Live website: TODO
- Agent API base URL: TODO  (`POST /chat`, `GET /health`)
- Demo video: TODO
- Demo GIF: `docs/demo.gif` (TODO)

## What it does
Sellers get a storefront with a chat sales agent (English / Roman Urdu) that searches the catalog, upsells, calculates totals, and places orders only after the customer confirms. Sellers get a dashboard and Telegram alerts.

## Architecture
TODO: embed `docs/architecture.png` (source: mermaid diagram in `ARCHITECTURE.md` section 6).

## Setup
TODO: filled after Phase 1 (backend: `pip install -r backend/requirements.txt`, apply `backend/sql/schema.sql` + `seed.sql`, copy `.env.example` to `.env`, `uvicorn app.main:app --port 7860`; frontend: `npm install && npm run dev`).

## Memory design
TODO: short note (copy from `ARCHITECTURE.md` section 8: short-term = LangGraph PostgresSaver keyed by store:user:thread; long-term = `user_memory` table keyed by store+user, whitelisted keys; isolation rules).

## Benchmark
| Test | Category | Result | Latency | Tokens in/out |
|---|---|---|---|---|
| TODO: filled by `benchmark/run_benchmark.py` | | | | |

Pass rate: TODO (10 own tests + 5 common attack tests).

## Safety
Regex + router guard, hardened prompt, deterministic confirm gate for orders, server-injected ids, output canary check.

## Deployment
Vercel (frontend), Hugging Face Space Docker (agent API), Supabase Postgres (data, memory, checkpoints).
