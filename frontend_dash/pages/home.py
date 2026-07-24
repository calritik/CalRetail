"""
AI Portfolio Overview — the whole capability map from the Calsoft deck
(slides 4-8) on one screen, with each domain linking through to its console.
"""
from __future__ import annotations

import dash
from dash import dcc, html

from frontend_dash.components import cards as C
from frontend_dash.components.cards import NAV_ICONS
from frontend_dash.components.layout import module_page
from frontend_dash.services.api import backend_is_up
from frontend_dash.services.capabilities import DOMAINS, totals
from frontend_dash.theme import chart_theme as T
from frontend_dash.theme import colors

dash.register_page(__name__, path="/", name="AI Portfolio")

_DOMAIN_ICON = {"cx": "cx", "merch": "merch", "ops": "ops", "support": "support"}


def _wave_chart():
    """
    A real Plotly chart, not static CSS bars — so it carries an actual hover
    tooltip like every other chart in the console, rather than a dead end.
    """
    t = totals()
    scheduled = t["wave1"] + t["wave2"] + t["wave3"]
    rows = [
        ("Wave 1", t["wave1"], colors.OK, "Highest data readiness — ships first"),
        ("Wave 2", t["wave2"], colors.WARN, "Ships once Wave 1 is live"),
        ("Wave 3", t["wave3"], colors.ACCENT, "Longer build, highest long-run payoff"),
        ("Unscheduled", t["capabilities"] - scheduled, colors.CARD_LINE, "No wave assigned yet"),
    ]
    labels, counts, bar_colors, descs = zip(*rows)

    fig = T.figure(height=210, margin=dict(l=8, r=8, t=6, b=6))
    fig.add_bar(
        x=counts, y=labels, orientation="h",
        marker=dict(color=bar_colors, cornerradius=8),
        text=[str(n) for n in counts], textposition="outside", cliponaxis=False,
        customdata=descs,
        hovertemplate="<b>%{y}</b> · %{x} capabilities<br>%{customdata}<extra></extra>",
    )
    fig.update_layout(
        hovermode="closest",
        bargap=.4,
        yaxis=dict(autorange="reversed"),
        xaxis=dict(showgrid=True, gridcolor=colors.LIGHT["grid"],
                   range=[0, max(counts) * 1.35], dtick=5),
    )
    return fig


def _domain_card(d):
    live = sum(c.source == "api" for c in d.capabilities)
    caps = [
        html.Div(
            [
                html.Span(className="pdot", style={
                    "width": "6px", "height": "6px", "borderRadius": "999px", "flex": "none",
                    "background": "var(--brand)",
                }),
                html.Span(c.title, className="grow", style={"fontSize": "12.5px"}),
                html.Span(f"W{c.wave}", className=f"wave w{c.wave}") if c.wave else None,
            ],
            className="row center",
            style={"gap": "9px", "padding": "6px 0"},
        )
        for c in d.capabilities
    ]
    title = html.Span(
        [html.Span(NAV_ICONS.get(_DOMAIN_ICON[d.key]), className="nav-ic",
                   style={"marginRight": "10px"}),
         d.title],
        className="row center",
    )
    return dcc.Link(
        C.card(
            title,
            [
                html.Div(d.tagline, className="card-sub"),
                html.Div(caps),
                html.Div(
                    [C.pill(f"{live}/{len(d.capabilities)} live", "low"), C.pill(d.index, "info")],
                    className="row-wrap", style={"marginTop": "12px"},
                ),
            ],
            caption=d.summary,
        ),
        href=d.path,
        style={"textDecoration": "none", "color": "inherit", "display": "block"},
    )


def layout():
    t = totals()
    up = backend_is_up()
    banner = [] if up else [C.offline_banner()]

    backend_value = [
        html.Span(className="status-dot" + ("" if up else " down"),
                  style={"marginRight": "7px"}),
        "Online" if up else "Offline",
    ]

    return module_page(
        "AI Portfolio",
        "Retail AI Capability Console",
        f"{t['capabilities']} AI capabilities across {t['domains']} domains — from "
        "hyper-personalised discovery through to intelligent customer support, "
        "built on live retail data.",
        banner + [
            html.Div(
                [
                    C.card(
                        "Portfolio at a glance",
                        C.kpi_grid([
                            C.kpi("Domains", t["domains"]),
                            C.kpi("Capabilities", t["capabilities"]),
                            C.kpi("Live on API", f"{t['live']}/{t['capabilities']}",
                                  "all served from real data"),
                            C.kpi("Backend", backend_value, "FastAPI :8000"),
                        ]),
                        caption="Every capability on slides 4-7 of the Calsoft Retail AI deck, "
                                "mapped to what the platform serves today.",
                    ),
                    C.card(
                        "Deployment waves",
                        C.graph(_wave_chart(), 210),
                        caption="Wave 1 ships first — highest data readiness and fastest time to value.",
                        info="Waves are taken straight from the deck's per-capability "
                             "<b>Speed</b> marker. Unscheduled capabilities carry no wave label.",
                    ),
                ],
                className="grid-2",
            ),
            html.Div([_domain_card(d) for d in DOMAINS], className="grid-2",
                     style={"marginTop": "18px"}),
        ],
    )
