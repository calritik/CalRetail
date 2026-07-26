---
title: CalRetail AI Console
emoji: 🛍️
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# CalRetail — Retail AI Capability Console

Sixteen AI capabilities across four domains — customer experience,
merchandising, operational efficiency and customer support — implementing the
Calsoft *Retail AI Solutions* deck. Every card is computed live from the
transaction log; nothing on the console is mocked or seeded.

## Architecture

A FastAPI backend (internal, on `127.0.0.1:8000`) and a Dash console run as two
processes in one container. Only Dash is bound to `0.0.0.0`, on the port this
Space routes to.

The console is **notebook-delegated**: the sixteen capability notebooks are the
single source of truth for capability logic, dynamically executed by the backend
and cached in memory after first load. The first click on a capability compiles
its notebook once (a few seconds); every click after that is served from cache.

## Data

All data lives in one committed SQLite database — 31 tables, 38 indexes,
~68 MB — so this Space boots straight into a warm dataset with no build step.
The database is opened **read-only**, one connection per thread, so a request
can never mutate it.

It is a demo-scale build: the catalogue and customer base are full size
(10,000 customers, 5,000 products, 150 stores, 30 distribution centres,
25,000 stock positions) while the behavioural event logs are scaled down to keep
the file inside GitHub's file-size limit. Rebuild at any scale with
`python -m notebooks.build_db --scale full`.

## LLM features

The AI Assistant router, the conversational buying assistant and the support
chatbot use Gemini, Groq or OpenAI when a matching key is set as a Space secret
(`GOOGLE_API_KEY`, `GROQ_API_KEY` or `OPENAI_API_KEY`). With no key configured
they fall back to a deterministic rule-based engine, and every other capability
is unaffected either way.
