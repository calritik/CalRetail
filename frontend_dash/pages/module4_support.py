"""
Domain 04 — Customer Support (notebooks 13–16).

Four capability cards — all data-driven, served by FastAPI:
  1. 24x7 AI Chatbots           (nb 13)
  2. Intelligent Ticket Triage  (nb 14)
  3. Agent Assist               (nb 15)
  4. Voice of Customer          (nb 16)
"""
from __future__ import annotations

from collections import Counter

import dash
from dash import Input, Output, State, callback, dcc, html

from frontend_dash.components import cards as C
from frontend_dash.components.layout import module_page
from frontend_dash.services.api import api_get, api_post
from frontend_dash.services.capabilities import SUPPORT as D
from frontend_dash.services.capabilities import cap
from frontend_dash.theme import chart_theme as T
from frontend_dash.theme import colors

dash.register_page(__name__, path=D.path, name=D.title)

CAP = {c.key: c for c in D.capabilities}

PRIORITY_LEVEL = {"Critical": "high", "High": "high", "Medium": "medium", "Low": "low"}


def _customer_options(limit: int = 60):
    rows = api_get("/api/v1/customer-experience/customers", {"limit": limit}) or []
    return [{"label": f"{r['name']} ({r['segment']})",
             "value": r["customer_id"]} for r in rows]


def _product_options(limit: int = 50):
    """Fetched live — options for Voice of Customer product filter."""
    rows = api_get("/api/v1/merchandising/products", {"limit": limit}) or []
    return [{"label": f"{r.get('product_name', r['product_id'])} ({r.get('category', '')})",
             "value": r["product_id"]} for r in rows]


def _conf_tone(v: float) -> str:
    return "ok" if v >= .6 else "warn" if v >= .35 else "danger"


# ══════════════════════════════════════════════════════════════════════════════
# 1 — 24x7 AI Chatbots  (notebook 13)
# ══════════════════════════════════════════════════════════════════════════════

PROMPTS = ["Where is my order?", "My jacket arrived damaged",
           "How do I return an item?", "Do you have this in size M?"]


def _card_chatbot(opts):
    return C.card(
        cap("support", "chatbot").title,
        [
            html.Div(
                [
                    dcc.Dropdown(id="su-chat-cust", options=opts,
                                 value=opts[0]["value"] if opts else None,
                                 clearable=False, className="dash-dropdown",
                                 style={"minWidth": "190px"},
                                 placeholder="Select a customer"),
                    dcc.Input(id="su-chat-msg", className="cp-input grow", debounce=True,
                              placeholder="Ask the support bot anything…",
                              value=PROMPTS[0]),
                    html.Button("Send", id="su-chat-go", className="cp-go", n_clicks=0),
                ],
                className="cp-row",
            ),
            html.Div([html.Span(p, className="chip", id={"type": "su-chip", "i": i})
                      for i, p in enumerate(PROMPTS)], className="mb-10"),
            html.Div(id="su-chat-out"),
        ],
        caption="Tier-0 deflection — the bot resolves order, returns and product questions against the customer's own history.",
        info="<b>Flow:</b> intent classification → answer from live customer order and catalogue records.",
    )


@callback(Output("su-chat-msg", "value"),
          Input({"type": "su-chip", "i": dash.ALL}, "n_clicks"),
          prevent_initial_call=True)
def _chip_to_input(_clicks):
    trig = dash.callback_context.triggered_id
    if isinstance(trig, dict) and trig.get("i") is not None:
        return PROMPTS[trig["i"]]
    return dash.no_update


@callback(Output("su-chat-out", "children"),
          Input("su-chat-go", "n_clicks"), Input("su-chat-msg", "value"),
          State("su-chat-cust", "value"))
def _chatbot(_n, message, customer_id):
    if not message or not customer_id:
        return C.empty("Pick a customer and ask a question to open a session.")
    data = api_post("/api/v1/support/chatbot",
                    {"customer_id": customer_id, "message": message})
    if not data:
        return C.empty("Chatbot unavailable.")

    escalate = bool(data.get("escalate"))
    pills = [C.pill(f"intent · {data.get('intent', '—')}", "info"),
             C.pill("escalate · yes" if escalate else "escalate · no",
                    "high" if escalate else "low")]

    return [
        html.Div([html.Div(data.get("query", message), className="chat-bubble-user copilot-in"),
                  html.Div(data.get("response", "—"), className="chat-bubble-ai copilot-in")],
                 className="chat-stream mb-10"),
        html.Div(pills, className="row-wrap mb-10"),
        html.Div(f"Powered by {data.get('powered_by', '—')} · session "
                 f"{data.get('session_id', '—')}", className="small muted"),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# 2 — Intelligent Ticket Triage  (notebook 14)
# ══════════════════════════════════════════════════════════════════════════════

TRIAGE_SAMPLE = ("My order arrived with the wrong size and the box was torn open. "
                 "I need a replacement before the weekend.")


def _card_triage(opts):
    return C.card(
        cap("support", "triage").title,
        [
            dcc.Textarea(id="su-tri-text", className="cp-input mb-10", rows=3,
                         value=TRIAGE_SAMPLE, placeholder="Paste the raw ticket text…"),
            html.Div(
                [
                    dcc.Dropdown(id="su-tri-cust", options=opts,
                                 value=opts[0]["value"] if opts else None,
                                 clearable=False, className="dash-dropdown grow"),
                    html.Button("Triage", id="su-tri-go", className="cp-go", n_clicks=0),
                ],
                className="cp-row",
            ),
            html.Div(id="su-tri-out"),
        ],
        caption="Category, priority and owning team predicted from raw ticket text.",
        info="<b>Models:</b> two classifiers (category and priority) run over the ticket text — "
             "overall confidence is their blend, shown as-is.",
    )


@callback(Output("su-tri-out", "children"),
          Input("su-tri-go", "n_clicks"), State("su-tri-text", "value"),
          State("su-tri-cust", "value"))
def _triage(_n, ticket_text, customer_id):
    if not ticket_text:
        return C.empty("Paste a ticket to route it.")
    data = api_post("/api/v1/support/ticket-triage",
                    {"ticket_description": ticket_text, "customer_id": customer_id})
    if not data:
        return C.empty("Triage unavailable.")

    prio = data.get("assigned_priority") or data.get("predicted_priority") or "—"
    cat_c = float(data.get("category_confidence", 0) or 0)
    pri_c = float(data.get("priority_confidence", 0) or 0)
    all_c = float(data.get("overall_confidence", 0) or 0)

    return [
        C.kpi_grid([
            C.kpi("Category", data.get("predicted_category", "—")),
            C.kpi("Routed to", data.get("routing_department") or data.get("recommended_team", "—")),
            C.kpi("Overall confidence", f"{all_c * 100:.0f}%", "blend of both models"),
        ]),
        html.Div([C.pill(f"priority · {prio}", PRIORITY_LEVEL.get(prio, "neutral")),
                  C.pill(f"team · {data.get('recommended_team', '—')}", "info")],
                 className="row-wrap mt-14 mb-10"),
        C.bar_row("Category", f"{cat_c:.2f}", cat_c * 100, _conf_tone(cat_c)),
        C.bar_row("Priority", f"{pri_c:.2f}", pri_c * 100, _conf_tone(pri_c)),
        C.bar_row("Overall", f"{all_c:.2f}", all_c * 100, _conf_tone(all_c)),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# 3 — Agent Assist  (notebook 15)
# ══════════════════════════════════════════════════════════════════════════════

AGENT_QUERIES = [
    "Customer says item never arrived but tracking shows delivered",
    "Refund was promised 5 days ago but not received",
    "How do I process an exchange for a different size?",
    "Customer claims discount code didn't apply at checkout",
]


def _card_agent_assist(opts):
    return C.card(
        cap("support", "agent_assist").title,
        [
            html.Div(
                [
                    dcc.Dropdown(id="su-aa-cust", options=opts,
                                 value=opts[0]["value"] if opts else None,
                                 clearable=False, className="dash-dropdown",
                                 style={"minWidth": "190px"},
                                 placeholder="Select a customer"),
                    dcc.Input(id="su-aa-query", className="cp-input grow", debounce=True,
                              placeholder="Describe the live agent's query…",
                              value=AGENT_QUERIES[0]),
                    html.Button("Assist", id="su-aa-go", className="cp-go", n_clicks=0),
                ],
                className="cp-row",
            ),
            html.Div([html.Span(q, className="chip", id={"type": "su-aa-chip", "i": i})
                      for i, q in enumerate(AGENT_QUERIES)], className="mb-10"),
            html.Div(id="su-aa-out"),
        ],
        caption="Real-time resolution suggestion and relevant SOP retrieval for the live agent — all from the knowledge base.",
        info=(
            "<b>Source:</b> notebook 15 encodes the support knowledge base and retrieves "
            "relevant SOPs + resolution steps from real ticket history. "
            "Customer context is pulled live from the backend."
        ),
    )


@callback(Output("su-aa-query", "value"),
          Input({"type": "su-aa-chip", "i": dash.ALL}, "n_clicks"),
          prevent_initial_call=True)
def _aa_chip_to_input(_clicks):
    trig = dash.callback_context.triggered_id
    if isinstance(trig, dict) and trig.get("i") is not None:
        return AGENT_QUERIES[trig["i"]]
    return dash.no_update


@callback(Output("su-aa-out", "children"),
          Input("su-aa-go", "n_clicks"), Input("su-aa-query", "value"),
          State("su-aa-cust", "value"))
def _agent_assist(_n, query_text, customer_id):
    if not query_text or not customer_id:
        return C.empty("Enter a query and pick a customer to get agent assistance.")
    data = api_post("/api/v1/support/agent-assist",
                    {"query_text": query_text, "customer_id": customer_id})
    if not data:
        return C.empty("Agent assist unavailable — is the backend running?")

    # The notebook returns: suggested_response, matched_sop, confidence, similar_cases
    sop         = data.get("matched_sop") or data.get("sop", "")
    confidence  = float(data.get("confidence", 0) or 0)
    response    = data.get("suggested_response") or data.get("resolution", "—")
    cases       = data.get("similar_cases") or []

    pills = []
    category = data.get("category") or data.get("ticket_category")
    if category:
        pills.append(C.pill(f"category · {category}", "info"))
    if confidence:
        tone = "ok" if confidence >= 0.7 else "warn" if confidence >= 0.4 else "danger"
        pills.append(C.pill(f"confidence · {confidence:.0%}", tone))

    parts = [html.Div(pills, className="row-wrap mb-10")] if pills else []

    if sop:
        parts.append(html.Div([
            html.Div("Matched SOP", className="card-sub"),
            html.Div(sop, className="chat-bubble-ai copilot-in mt-6"),
        ], className="mb-10"))

    parts.append(html.Div([
        html.Div("Suggested response", className="card-sub"),
        html.Div(response, className="chat-bubble-ai copilot-in mt-6"),
    ], className="mb-10"))

    if cases:
        rows = [[c.get("ticket_id", "—"), c.get("issue_summary", "—"),
                 c.get("resolution_summary", "—"),
                 f"{float(c.get('similarity', 0)):.2f}"] for c in cases[:5]]
        parts.append(C.table(
            ["Ticket", "Issue", "Resolution", "Similarity"],
            rows, numeric={3},
        ))

    if confidence:
        parts.append(C.bar_row("Retrieval confidence", f"{confidence:.0%}",
                                confidence * 100, _conf_tone(confidence)))
    return parts


# ══════════════════════════════════════════════════════════════════════════════
# 4 — Voice of Customer  (notebook 16)
# ══════════════════════════════════════════════════════════════════════════════

def _card_voc(prod_opts):
    return C.card(
        cap("support", "voc").title,
        [
            html.Div(
                [
                    dcc.Dropdown(id="su-voc-prod", options=prod_opts,
                                 value=None, clearable=True,
                                 className="dash-dropdown grow",
                                 placeholder="All products — network-wide"),
                    dcc.Input(id="su-voc-from", placeholder="From date (YYYY-MM-DD)",
                              className="cp-input", style={"width": "150px"}),
                    dcc.Input(id="su-voc-to", placeholder="To date (YYYY-MM-DD)",
                              className="cp-input", style={"width": "150px"}),
                    html.Button("Mine reviews", id="su-voc-go", className="cp-go", n_clicks=0),
                ],
                className="cp-row",
            ),
            html.Div(id="su-voc-out"),
        ],
        caption="Sentiment, aspect and trend analysis mined from real product reviews — all data driven.",
        info=(
            "<b>Source:</b> notebook 16 runs aspect-level sentiment analysis on the product "
            "review dataset. Sentiment distribution, aspect scores and monthly rating trends "
            "are all computed live from the raw review records — nothing is hardcoded."
        ),
        span=2,
    )


@callback(Output("su-voc-out", "children"),
          Input("su-voc-go", "n_clicks"),
          State("su-voc-prod", "value"),
          State("su-voc-from", "value"),
          State("su-voc-to", "value"))
def _voc(_n, product_id, date_from, date_to):
    params = {}
    if product_id:
        params["product_id"] = product_id
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    data = api_get("/api/v1/support/voice-of-customer", params or None)
    if not data or not data.get("total_reviews"):
        return C.empty("No reviews found for this filter — try removing the date range or product filter.")

    total   = data.get("total_reviews", 0)
    avg_r   = float(data.get("avg_rating", 0))
    alert   = bool(data.get("alert"))
    sent    = data.get("sentiment_distribution") or {}
    aspects = data.get("aspect_analysis") or {}
    monthly = data.get("monthly_trend") or []

    # ── KPIs ──────────────────────────────────────────────────────────────────
    kpis = C.kpi_grid([
        C.kpi("Reviews analysed", f"{total:,}"),
        C.kpi("Avg rating", f"{avg_r:.2f} / 5.0",
              "⚠ Below threshold" if alert else "Within healthy range",
              "down" if alert else "up"),
        C.kpi("Positive reviews",
              f"{sent.get('Positive', 0):,}",
              f"{sent.get('Positive', 0) / total * 100:.1f}% of total" if total else ""),
        C.kpi("Negative reviews",
              f"{sent.get('Negative', 0):,}",
              f"{sent.get('Negative', 0) / total * 100:.1f}% of total" if total else "",
              "down" if sent.get("Negative", 0) > sent.get("Positive", 0) else ""),
    ])

    # ── Monthly rating trend chart ─────────────────────────────────────────────
    chart_block = []
    if monthly:
        months = [m["month"] for m in monthly]
        ratings = [m["avg_rating"] for m in monthly]
        fig = T.figure(height=190, margin=dict(l=8, r=8, t=4, b=4))
        fig.add_scatter(x=months, y=ratings, mode="lines+markers",
                        line=dict(color=colors.BRAND, width=2.5, shape="spline"),
                        marker=dict(color=colors.BRAND, size=5),
                        hovertemplate="%{x}<br>avg rating %{y:.2f}<extra></extra>")
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(title="Avg rating", showgrid=True, gridcolor=colors.LIGHT["grid"],
                       range=[1, 5.2]),
        )
        chart_block = [html.Div("Monthly rating trend", className="card-sub mt-14"),
                       C.graph(fig, 190)]

    # ── Aspect analysis ────────────────────────────────────────────────────────
    aspect_block = []
    if aspects:
        aspect_rows = [
            [asp,
             f"{info['mention_count']:,}",
             f"{info['avg_rating']:.2f}",
             C.bar_row("", f"{info['pct_positive']:.0f}%", info["pct_positive"],
                       "ok" if info["pct_positive"] >= 70 else
                       "warn" if info["pct_positive"] >= 40 else "danger")]
            for asp, info in sorted(aspects.items(),
                                    key=lambda kv: kv[1]["mention_count"], reverse=True)
        ]
        aspect_block = [html.Div("Aspect analysis", className="card-sub mt-14"),
                        C.table(["Aspect", "Mentions", "Avg rating", "% Positive"],
                                aspect_rows, numeric={1, 2})]

    return [kpis, *chart_block, *aspect_block]


# ══════════════════════════════════════════════════════════════════════════════

def layout():
    opts      = _customer_options()
    prod_opts = _product_options()
    banner = [] if opts else [C.offline_banner()]
    return module_page(
        D.index, D.title, D.summary,
        banner + [
            html.Div(
                [
                    _card_chatbot(opts),
                    _card_triage(opts),
                    _card_agent_assist(opts),
                    _card_voc(prod_opts),
                ],
                className="grid-2",
            )
        ],
    )
