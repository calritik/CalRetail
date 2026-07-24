"""
Domain 04 — Customer Support (Calsoft Retail AI deck, slide 7).

Six capability cards, all six served by FastAPI.

Cards 2 and 4 both POST to /api/v1/support/agent-assist but read the same
payload differently — card 2 is the auto-resolution proposal (SOP + knowledge
base), card 4 is the similarity surface a live agent watches while typing.
They keep separate ids and separate callbacks so one never blanks the other.
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

# Backend priority labels -> .pill severity modifier.
PRIORITY_LEVEL = {"Critical": "high", "High": "high", "Medium": "medium", "Low": "low"}


def _customer_options(limit: int = 60):
    rows = api_get("/api/v1/customer-experience/customers", {"limit": limit}) or []
    return [{"label": f"{r['name']} ({r['segment']})",
             "value": r["customer_id"]} for r in rows]


def _conf_tone(v: float) -> str:
    """Triage confidence thresholds. Deliberately strict — the classifiers score
    0.13-0.41 on this dataset, and a bar that reads green at 0.3 would sell a
    confidence the model does not have."""
    return "ok" if v >= .6 else "warn" if v >= .35 else "danger"


# ══════════════════════════════════════════════════════════════════════════════
# 1 — 24x7 AI Chatbots
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
        info="<b>Flow:</b> the message is classified into an <b>intent</b>, then answered from "
             "the customer's live order and catalogue records. <b>Escalate</b> flips high when "
             "the intent needs a human. The <b>powered by</b> line names the engine actually "
             "used — an LLM when a key is configured, the rule-based fallback otherwise.",
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
# 2 — Intelligent Ticket Triage
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
        caption="Category, priority and owning team predicted from raw ticket text — with the classifier's own confidence shown as-is.",
        info="<b>Models:</b> two classifiers (category and priority) run over the ticket text; "
             "<b>overall</b> is their blend. Confidence on this dataset sits between 0.13 and "
             "0.41, so the bars stay amber or red — that is the honest reading, and the reason "
             "triage output is a suggestion a human still confirms.",
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
            C.kpi("Routed to", data.get("routing_department")
                  or data.get("recommended_team", "—")),
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

def layout():
    opts = _customer_options()
    banner = [] if opts else [C.offline_banner()]
    return module_page(
        D.index, D.title, D.summary,
        banner + [
            html.Div(
                [
                    _card_chatbot(opts),
                    _card_triage(opts),
                ],
                className="grid-2",
            )
        ],
    )
