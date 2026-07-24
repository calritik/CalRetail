"""
Domain 01 — Customer Experience (Calsoft Retail AI deck, slide 4).

All six capability cards are served by FastAPI over the real retail datasets.
This page is the reference implementation the other four domains follow.
"""
from __future__ import annotations

import dash
from dash import Input, Output, State, callback, dcc, html

from frontend_dash.components import cards as C
from frontend_dash.components.layout import module_page
from frontend_dash.services.api import api_get, api_post
from frontend_dash.services.capabilities import CUSTOMER_EXPERIENCE as D
from frontend_dash.services.capabilities import cap
from frontend_dash.theme import chart_theme as T
from frontend_dash.theme import colors

dash.register_page(__name__, path=D.path, name=D.title)

CAP = {c.key: c for c in D.capabilities}


def _customer_options(limit: int = 60):
    rows = api_get("/api/v1/customer-experience/customers", {"limit": limit}) or []
    return [{"label": f"{r['name']} ({r['segment']})",
             "value": r["customer_id"]} for r in rows]


def _segment_options():
    """Persona segments shared by the segmentation, NBO and churn cards, so the
    page reads as one continuous story keyed off the same vocabulary."""
    d = api_get("/api/v1/customer-experience/segmentation") or {}
    return [{"label": s["segment"], "value": s["segment"]} for s in (d.get("segments") or [])]


# ══════════════════════════════════════════════════════════════════════════════
# 1 — Customer Segmentation (Admin View)
# ══════════════════════════════════════════════════════════════════════════════

def _card_segmentation():
    d = api_get("/api/v1/customer-experience/segmentation")
    segs = (d or {}).get("segments") or []
    if not segs:
        return C.card(cap("cx", "recommendations").title,
                      C.empty("Segmentation unavailable."), span=2)

    # Bubble map: recency (x) against average spend (y), bubble area = segment
    # size — the standard RFM read, one glance tells you which segments are big,
    # loyal (low recency) and high-value (high spend).
    sizes = [s["customers"] for s in segs]
    smax = max(sizes) or 1
    fig = T.figure(height=250, margin=dict(l=8, r=8, t=8, b=6))
    fig.add_scatter(
        x=[s["avg_recency_days"] for s in segs],
        y=[s["avg_monetary"] / 100000 for s in segs],
        mode="markers+text",
        text=[s["segment"] for s in segs], textposition="top center",
        textfont=dict(size=9.5), cliponaxis=False,
        marker=dict(size=sizes, sizemode="area", sizeref=2.0 * smax / (46 ** 2), sizemin=7,
                    color=[colors.CATEGORICAL[i % len(colors.CATEGORICAL)] for i in range(len(segs))],
                    line=dict(width=1, color="rgba(255,255,255,.75)")),
        customdata=[[s["customers"], s["avg_frequency"], s["avg_churn_risk_pct"]] for s in segs],
        hovertemplate="<b>%{text}</b><br>%{customdata[0]:,} customers · recency %{x:.0f}d<br>"
                      "avg spend ₹%{y:.1f}L · %{customdata[1]:.0f} orders · churn %{customdata[2]}%<extra></extra>",
    )
    fig.update_layout(hovermode="closest",
                      xaxis=dict(title="Avg recency (days)", showgrid=True, gridcolor=colors.LIGHT["grid"]),
                      yaxis=dict(title="Avg spend (₹L)", showgrid=True, gridcolor=colors.LIGHT["grid"]))

    rows = []
    for s in segs:
        risk = s["avg_churn_risk_pct"]
        lvl = "high" if risk >= 35 else "medium" if risk >= 15 else "low"
        rows.append([
            s["segment"], f"{s['customers']:,}", f"{s['pct_of_total']}%",
            f"{s['avg_recency_days']:.0f}d", f"{s['avg_frequency']:.0f}",
            C.money(s["avg_monetary"]), C.pill(f"{risk}%", lvl),
        ])

    return C.card(
        cap("cx", "recommendations").title,
        [
            C.kpi_grid([
                C.kpi("Customers", f"{d['total_customers']:,}"),
                C.kpi("Segments", d["n_segments"]),
                C.kpi("Book value", C.money(d["total_value"]), "lifetime spend"),
                C.kpi("Top-value segment", segs[0]["segment"], f"{segs[0]['customers']:,} customers"),
            ]),
            html.Div(C.graph(fig, 250), className="mt-14"),
            C.table(["Segment", "Customers", "% base", "Avg recency", "Avg orders", "Avg spend", "Churn risk"],
                    rows, numeric={1, 2, 3, 4, 5}),
        ],
        caption="Every customer bucketed into a behavioural persona and profiled by recency, "
                "frequency and spend — the base each offer and retention play on this page targets.",
        info="<b>Source:</b> real order history joined to customer records. Bubble position is "
             "average recency (x) vs. average spend (y); bubble area is the number of customers "
             "in the segment. These are the same personas the offer and churn cards below key off.",
        span=2,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2 — Personalized Buying Assistants
# ══════════════════════════════════════════════════════════════════════════════

SUGGESTED = ["red jackets under 3000", "formal shirts for office",
             "running shoes below 5000", "ethnic wear for a wedding"]


def _card_assistant(opts):
    return C.card(
        cap("cx", "assistant").title,
        [
            html.Div(
                [
                    dcc.Dropdown(id="cx-asst-cust", options=opts,
                                 value=opts[0]["value"] if opts else None,
                                 clearable=False, className="dash-dropdown",
                                 style={"minWidth": "190px"}),
                    dcc.Input(id="cx-asst-msg", className="cp-input grow", debounce=True,
                              placeholder="Ask for a product in plain English…",
                              value=SUGGESTED[0]),
                    html.Button("Ask", id="cx-asst-go", className="cp-go", n_clicks=0),
                ],
                className="cp-row",
            ),
            html.Div([html.Span(s, className="chip", id={"type": "cx-chip", "i": i})
                      for i, s in enumerate(SUGGESTED)], className="mb-10"),
            html.Div(id="cx-asst-out"),
        ],
        caption="Natural-language intent extraction — category, colour and price ceiling are parsed, then matched against stock.",
        info="<b>Flow:</b> the LLM (or a rule-based fallback when no key is set) extracts "
             "<b>intent</b>, <b>category</b> and <b>max price</b>, which become a catalogue filter.",
    )


@callback(Output("cx-asst-msg", "value"),
          Input({"type": "cx-chip", "i": dash.ALL}, "n_clicks"),
          prevent_initial_call=True)
def _chip_to_input(_clicks):
    trig = dash.callback_context.triggered_id
    if isinstance(trig, dict) and trig.get("i") is not None:
        return SUGGESTED[trig["i"]]
    return dash.no_update


@callback(Output("cx-asst-out", "children"),
          Input("cx-asst-go", "n_clicks"), Input("cx-asst-msg", "value"),
          State("cx-asst-cust", "value"))
def _assistant(_n, message, customer_id):
    if not message or not customer_id:
        return C.empty("Ask a question to see how the assistant interprets it.")
    data = api_post("/api/v1/customer-experience/buying-assistant",
                    {"customer_id": customer_id, "message": message})
    if not data:
        return C.empty("Assistant unavailable.")

    chips = []
    if data.get("detected_category"):
        chips.append(C.pill(data["detected_category"], "info"))
    if data.get("max_price"):
        chips.append(C.pill(f"under ₹{data['max_price']:,.0f}", "neutral"))
    if data.get("intent"):
        chips.append(C.pill(f"intent · {data['intent']}", "neutral"))

    out = [
        html.Div([html.Div(message, className="chat-bubble-user copilot-in"),
                  html.Div(data.get("response", "—"), className="chat-bubble-ai copilot-in")],
                 className="chat-stream mb-10"),
        html.Div(chips, className="row-wrap mb-10"),
    ]

    sugg = data.get("product_suggestions") or []
    if sugg:
        out.append(C.table(
            ["Product", "Brand", "Price"],
            [[s.get("product_name", "—"), s.get("brand", "—"), f"₹{s.get('price', 0):,.0f}"]
             for s in sugg],
            numeric={2},
        ))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 3 — Next-Best-Offer Engines
# ══════════════════════════════════════════════════════════════════════════════

def _card_nbo(seg_opts):
    return C.card(
        cap("cx", "nbo").title,
        [
            html.Div(
                [
                    dcc.Dropdown(id="cx-nbo-seg", options=seg_opts,
                                 value=seg_opts[0]["value"] if seg_opts else None,
                                 clearable=False, className="dash-dropdown grow",
                                 placeholder="Select a segment"),
                    html.Button("Plan offers", id="cx-nbo-go", className="cp-go", n_clicks=0),
                ],
                className="cp-row",
            ),
            html.Div(id="cx-nbo-out"),
        ],
        caption="The offers most worth pushing to a whole segment, ranked by fit and predicted uplift.",
        info="<b>Campaign-planning view:</b> active promotions are scored against the segment's "
             "dominant preferred category and channel and whether they on-target the segment, then "
             "ranked. This answers 'what do we push to this segment', not 'what for one shopper'.",
    )


@callback(Output("cx-nbo-out", "children"),
          Input("cx-nbo-go", "n_clicks"), Input("cx-nbo-seg", "value"))
def _nbo(_n, segment):
    if not segment:
        return C.empty("Pick a segment to plan its offers.")
    d = api_get("/api/v1/customer-experience/next-best-offer/segment",
                {"segment": segment, "top_n": 6})
    offers = (d or {}).get("offers") or []
    if not offers:
        return C.empty("No active offers matched this segment.")

    chips = [
        C.pill(f"{d['segment_size']:,} customers", "info"),
        C.pill(f"prefers {d.get('preferred_category', '—')}", "neutral"),
        C.pill(f"via {d.get('preferred_channel', '—')}", "neutral"),
    ]
    rows = [
        [o["promo_type"], C.pill(o["category"], "info"), f"{o['discount_pct']:.0f}%",
         C.pill("on-target", "low") if o["on_target"] else C.pill(o["target_segment"], "neutral"),
         f"{o['predicted_uplift_pct']:.0f}%"]
        for o in offers
    ]
    return [
        html.Div(chips, className="row-wrap mb-10"),
        C.table(["Offer", "Category", "Discount", "Targeting", "Pred. uplift"], rows, numeric={2, 4}),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# 4 — Churn & Loyalty Propensity
# ══════════════════════════════════════════════════════════════════════════════

def _card_churn(seg_opts):
    d = api_get("/api/v1/customer-experience/churn-propensity", {"top_n": 6})
    if not d:
        return C.card(cap("cx", "churn").title, C.empty("Churn scoring unavailable."),
                      span=2)

    by_seg = d.get("by_segment") or []

    # Value at risk grouped by segment — where the retention budget goes first,
    # as a chart instead of a raw per-customer list (the drill-down below opens
    # the individual customers for whichever segment you pick).
    order = sorted(by_seg, key=lambda s: s["clv_at_risk"])
    fig = T.figure(height=210, margin=dict(l=8, r=8, t=6, b=6))
    fig.add_bar(
        x=[s["clv_at_risk"] / 10000000 for s in order],
        y=[s["segment"] for s in order], orientation="h",
        marker=dict(color=colors.ACCENT, cornerradius=6),
        customdata=[[s["churn_risk_pct"], s["customers"]] for s in order],
        hovertemplate="<b>%{y}</b><br>₹%{x:.2f}Cr at risk · churn %{customdata[0]}%"
                      " · %{customdata[1]:,} customers<extra></extra>",
    )
    fig.update_layout(hovermode="closest", bargap=.34,
                      xaxis=dict(title="Value at risk (₹Cr)", showgrid=True,
                                 gridcolor=colors.LIGHT["grid"]))

    seg_rows = []
    for s in by_seg:
        risk = s["churn_risk_pct"]
        lvl = "high" if risk >= 35 else "medium" if risk >= 15 else "low"
        seg_rows.append([
            s["segment"], f"{s['customers']:,}", C.pill(f"{risk}%", lvl),
            C.money(s["clv_at_risk"]), f"{s['avg_recency_days']:.0f}d",
            html.Span(s["action"], className="small muted"),
        ])

    return C.card(
        cap("cx", "churn").title,
        [
            C.kpi_grid([
                C.kpi("Customers scored", f"{d['customers_scored']:,}", f"as of {d['as_of']}"),
                C.kpi("At risk", f"{d['at_risk_customers']:,}", "risk ≥ 35%", "down"),
                C.kpi("Value at risk", C.money(d["clv_at_risk_total"]), "spend × P(churn)", "down"),
                C.kpi("Model AUC", f"{d['model_auc']}", f"base rate {d['holdout_base_rate_pct']}%"),
            ]),
            html.Div("Value at risk by segment", className="card-sub mt-14"),
            C.graph(fig, 210),
            C.table(["Segment", "Customers", "Churn risk", "Value at risk", "Avg recency", "Triggered action"],
                    seg_rows, numeric={1, 3, 4}),
            html.Div("Drill into a segment — its highest-value at-risk customers",
                     className="card-sub mt-14"),
            html.Div(
                dcc.Dropdown(id="cx-churn-seg", options=seg_opts,
                             value=seg_opts[0]["value"] if seg_opts else None,
                             clearable=False, className="dash-dropdown grow"),
                className="cp-row",
            ),
            html.Div(id="cx-churn-drill"),
        ],
        caption="Churn scored against each customer's own buying cadence, grouped by segment so "
                "retention budget lands where the most spend is actually at stake.",
        info="<b>Model:</b> gradient-boosted classifier trained on a 90-day holdout — a customer "
             "active in the year before the cutoff but silent during it is labelled churned, so "
             "the label never leaks into the features. <b>Lapse ratio</b> (silence ÷ that "
             "customer's median inter-purchase gap) is the key feature: a monthly shopper quiet "
             "for 90 days is in trouble, a twice-yearly shopper is not.",
        span=2,
    )


@callback(Output("cx-churn-drill", "children"), Input("cx-churn-seg", "value"))
def _churn_drill(segment):
    if not segment:
        return C.empty("Pick a segment to see its at-risk customers.")
    d = api_get("/api/v1/customer-experience/churn-propensity/segment",
                {"segment": segment, "top_n": 12})
    custs = (d or {}).get("customers") or []
    if not custs:
        return C.empty("No at-risk customers in this segment.")

    head = html.Div(
        [
            C.pill(f"{d['segment_size']:,} in segment", "neutral"),
            C.pill(f"{d['at_risk_customers']:,} at risk ≥ 35%", "high"),
            C.pill(f"{C.money(d['clv_at_risk'])} at risk", "info"),
        ],
        className="row-wrap mb-10",
    )
    rows = [
        [c.get("name", c["customer_id"]),
         C.pill(f"{c['churn_risk_pct']}%", "high" if c["churn_risk_pct"] >= 35 else "medium"),
         f"{c['recency_days']}d", f"{c['frequency']}", C.money(c["monetary"]),
         C.money(c["value_at_risk"]), html.Span(c["action"], className="small muted")]
        for c in custs
    ]
    return [head, C.table(
        ["Customer", "Risk", "Recency", "Orders", "Spend", "Value at risk", "Action"],
        rows, numeric={2, 3, 4, 5})]


# ══════════════════════════════════════════════════════════════════════════════

def layout():
    seg_opts = _segment_options()
    cust_opts = _customer_options()
    banner = [] if seg_opts else [C.offline_banner()]
    return module_page(
        D.index, D.title, D.summary,
        banner + [
            html.Div(
                [
                    _card_segmentation(),
                    _card_nbo(seg_opts),
                    _card_assistant(cust_opts),
                    _card_churn(seg_opts),
                ],
                className="grid-2",
            )
        ],
    )
