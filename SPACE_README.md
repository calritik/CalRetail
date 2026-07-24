---
title: CalRetail AI Console
emoji: 🛍️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# CalRetail — Retail AI Capability Console

Thirty AI capabilities across five domains — customer experience, merchandising,
operational efficiency, customer support, and first-party data monetisation —
implementing slides 4-8 of the Calsoft *Retail AI Solutions* deck. Every card is
computed live from ~2M rows of real retail data (orders, sessions, returns,
support tickets, competitor pricing); none of it is generated or mocked.

**Architecture:** a FastAPI backend (internal, 43 REST endpoints) and a Dash
console run as two processes in this one container. The console is a
notebook-delegated system — the 20 original + 10 added capability notebooks
are the single source of truth, dynamically executed by the backend.

**LLM features** (the AI Assistant router, the conversational buying assistant,
the support chatbot) use Gemini/Groq/OpenAI when a matching key is set as a
Space secret, and fall back to a deterministic rule-based engine when none is
configured — every other capability is unaffected either way.

First click on any capability compiles its notebook once (a few seconds);
every click after that is served from cache.
