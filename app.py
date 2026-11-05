"""AutoNova Omnichannel Analytics (Streamlit dashboard).

Reads the cleaned CSVs in data/clean/ and computes every number from the
underlying records. Every page opens with a sentence computed from the data,
so the headline always matches the filters in the sidebar.

Run:   streamlit run app.py
Theme: put the config.toml that ships with this file in .streamlit/config.toml
       (the layout is designed for a light theme).

Data note: the dataset is synthetic. Patterns were planted on purpose so the
analysis has something to detect. Findings show method, not business results.
"""

from __future__ import annotations

import html
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# Design tokens
# ----------------------------------------------------------------------------
INK = "#12262B"        # text
PAPER = "#F3F6F5"      # page background
SURFACE = "#FFFFFF"    # sidebar, chart hover
RULE = "#D3DCDA"       # hairlines
GRID = "#E3EAE8"       # chart gridlines
MUTED = "#5E7176"      # secondary text
TEAL = "#17707D"       # normal data
SIGNAL = "#D8431E"     # problems only (used for nothing else)
SOFT = "#9DB0B4"       # comparison series
FONT = "Instrument Sans, -apple-system, Segoe UI, Roboto, sans-serif"
PALETTE = [TEAL, "#6C8EAD", "#B08D2F", "#8B5E83", "#6E9A78", "#8A6F5A"]

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "clean"
DOCS_DIR = BASE_DIR / "docs"

PAGES = ["Overview", "Digital", "Dealers", "Marketing & NPS", "Call center", "Findings & method"]
TABLES = ["dealers", "sales", "web_sessions", "feedback", "call_logs",
          "service_jobs", "campaigns", "inventory", "dim_date"]

st.set_page_config(page_title="AutoNova Analytics", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&display=swap');
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"],
button, input, select, textarea { font-family: 'Instrument Sans', -apple-system, 'Segoe UI', Roboto, sans-serif; }
.stApp { background: __PAPER__; color: __INK__; }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, .stDeployButton { visibility: hidden; }
.block-container { max-width: 1180px; padding-top: 1.4rem; padding-bottom: 4rem; }
[data-testid="stSidebar"] { background: __SURFACE__; border-right: 1px solid __RULE__; }
.stApp p, .stApp li, .stApp label, .stApp span { color: inherit; }
[data-testid="stAppDeployButton"], .stAppDeployButton { display: none; }

/* Keep every widget readable on the light page, even when the browser or Streamlit theme is dark */
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"], [data-testid="stSidebar"] label,
[data-testid="stSidebar"] h3, [data-testid="stExpander"] summary, [data-testid="stExpander"] details { color: __INK__; }
[data-testid="stCaptionContainer"], [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: __MUTED__; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { background: __SURFACE__; border: 1px solid __RULE__; }
[data-testid="stSidebar"] [data-baseweb="select"] *, [data-baseweb="popover"] * { color: __INK__; }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] ul, [data-baseweb="menu"] { background: __SURFACE__; }
[data-baseweb="tag"] { background: __TEAL__; }
[data-baseweb="tag"] * { color: #FFFFFF; }
.stButton > button { background: __SURFACE__; color: __INK__; border: 1px solid __RULE__; }
.stButton > button:hover { border-color: __TEAL__; color: __TEAL__; }
[data-testid="stExpander"] { background: __SURFACE__; border: 1px solid __RULE__; border-radius: 6px; }

.mast { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
        flex-wrap: wrap; border-bottom: 1px solid __RULE__; padding-bottom: .7rem; margin-bottom: .6rem; }
.mast .brand { font-weight: 700; font-size: 1.1rem; letter-spacing: -.01em; }
.mast .brand span { font-weight: 500; color: __MUTED__; margin-left: .6rem; }
.mast .note { font-size: .8rem; color: __MUTED__; max-width: 48ch; text-align: right; }

div[role="radiogroup"] { gap: .1rem 1.6rem; flex-wrap: wrap; border-bottom: 1px solid __RULE__; }
div[role="radiogroup"] > label { padding: .55rem 0 .45rem; margin: 0; cursor: pointer;
        border-bottom: 3px solid transparent; }
div[role="radiogroup"] > label > div:first-of-type { display: none; }
div[role="radiogroup"] > label p { font-size: .95rem; font-weight: 500; color: __MUTED__; }
div[role="radiogroup"] > label:has(input:checked) { border-bottom-color: __TEAL__; }
div[role="radiogroup"] > label:has(input:checked) p { color: __INK__; font-weight: 650; }
div[role="radiogroup"] > label:focus-within { outline: 2px solid __TEAL__; outline-offset: 2px; }

.scope { font-size: .85rem; color: __MUTED__; margin: .7rem 0 0; }
.lede { margin: .5rem 0 1.3rem; }
.lede h1 { font-size: 2.05rem; line-height: 1.18; font-weight: 650; letter-spacing: -.02em;
           max-width: 27em; margin: 0 0 .55rem; padding: 0; color: __INK__; }
.lede p { color: __MUTED__; max-width: 62ch; margin: 0; font-size: 1rem; line-height: 1.5; }

.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
        border-top: 2px solid __INK__; margin: .4rem 0 .6rem; }
.kpi { padding: .85rem .9rem .8rem 0; }
.kpi + .kpi { border-left: 1px solid __RULE__; padding-left: 1rem; }
.kpi-l { font-size: .85rem; color: __MUTED__; }
.kpi-v { font-size: 1.95rem; font-weight: 650; letter-spacing: -.02em; line-height: 1.25;
         font-variant-numeric: tabular-nums; }
.kpi-n { font-size: .8rem; color: __MUTED__; }
.kpi.bad .kpi-v { color: __SIGNAL__; }

.sec { margin: 1.9rem 0 .3rem; }
.sec h3 { font-size: 1.08rem; font-weight: 650; margin: 0; padding: 0; color: __INK__; }
.sec p { color: __MUTED__; font-size: .9rem; margin: .15rem 0 0; max-width: 72ch; }

.finding { border-left: 3px solid __TEAL__; padding: .15rem 0 .15rem 1rem; margin: 0 0 1.5rem; }
.finding.bad { border-left-color: __SIGNAL__; }
.finding h4 { margin: 0 0 .3rem; font-size: 1.08rem; padding: 0; color: __INK__; }
.finding p { margin: .15rem 0; max-width: 74ch; line-height: 1.5; }
.finding .act { color: __INK__; font-weight: 500; }
.finding .src { font-size: .82rem; color: __MUTED__; }

.fine { font-size: .82rem; color: __MUTED__; max-width: 80ch; }
</style>
"""
for _k, _v in {"__PAPER__": PAPER, "__INK__": INK, "__SURFACE__": SURFACE, "__RULE__": RULE,
               "__MUTED__": MUTED, "__TEAL__": TEAL, "__SIGNAL__": SIGNAL}.items():
    CSS = CSS.replace(_k, _v)
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Streamlit version compatibility (width="stretch" vs use_container_width)
# ----------------------------------------------------------------------------
def _stretch_kwargs(fn) -> dict:
    try:
        p = inspect.signature(fn).parameters.get("width")
        if p is not None and p.default == "stretch":
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


PLOT_KW = _stretch_kwargs(st.plotly_chart)
FRAME_KW = _stretch_kwargs(st.dataframe)
PLOT_CONFIG = {"displayModeBar": False}


# ----------------------------------------------------------------------------
# Data loading and preparation
# ----------------------------------------------------------------------------
def _add_period(df: pd.DataFrame) -> pd.DataFrame:
    ym = df["year_month"].astype(str)
    df["year_num"] = ym.str[:4].astype(int)
    m = ym.str[5:7].astype(int)
    df["quarter_num"] = (m - 1) // 3 + 1
    df["month_start"] = pd.to_datetime(ym + "-01")
    return df


@st.cache_data(show_spinner="Loading data")
def load_tables():
    missing = [t for t in TABLES if not (DATA_DIR / f"{t}.csv").exists()]
    if missing:
        return None, missing
    T = {t: pd.read_csv(DATA_DIR / f"{t}.csv") for t in TABLES}

    dealers = T["dealers"]
    region = dealers.set_index("dealer_id")["region"]
    name = dealers.set_index("dealer_id")["dealer_name"]

    sales = _add_period(T["sales"].copy())
    sales["region"] = sales["dealer_id"].map(region)
    sales["dealer_name"] = sales["dealer_id"].map(name)

    service = _add_period(T["service_jobs"].copy())
    service["is_delayed"] = (service["tat_flag"] == "Delayed").astype(int)
    service["region"] = service["dealer_id"].map(region)
    service["dealer_name"] = service["dealer_id"].map(name)

    feedback = _add_period(T["feedback"].copy())
    feedback["region"] = feedback["dealer_id"].map(region)
    feedback["dealer_name"] = feedback["dealer_id"].map(name)

    web = _add_period(T["web_sessions"].copy())
    calls = _add_period(T["call_logs"].copy())
    calls["is_negative"] = (calls["sentiment"] == "Negative").astype(int)

    camp = T["campaigns"].copy()
    camp["year_num"] = camp["quarter"].astype(str).str[:4].astype(int)
    camp["quarter_num"] = camp["quarter"].astype(str).str.extract(r"Q([1-4])")[0].astype(int)

    inv = T["inventory"].copy()
    inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"])
    inv["year_num"] = inv["snapshot_date"].dt.year
    inv["quarter_num"] = inv["snapshot_date"].dt.quarter
    inv["region"] = inv["dealer_id"].map(region)

    dd = T["dim_date"][["year_month", "year", "month_num"]].drop_duplicates().copy()
    dd["year_num"] = dd["year"].astype(int)
    dd["quarter_num"] = (dd["month_num"] - 1) // 3 + 1

    return {"dealers": dealers, "sales": sales, "service": service, "feedback": feedback,
            "web": web, "calls": calls, "campaigns": camp, "inventory": inv, "months": dd}, []


def in_period(df: pd.DataFrame, year, quarters) -> pd.DataFrame:
    mask = df["quarter_num"].isin(quarters)
    if year != "All":
        mask &= df["year_num"] == int(year)
    return df[mask]


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def pct(v, d=1):
    return "n/a" if pd.isna(v) else f"{v:.{d}f}%"


def cr(v):
    return "n/a" if pd.isna(v) else f"₹{v / 1e7:,.1f} cr"


def inr(v):
    return "n/a" if pd.isna(v) else f"₹{v:,.0f}"


def times(v):
    return "n/a" if pd.isna(v) else (f"{v:.0f}×" if abs(v) >= 10 else f"{v:.1f}×")


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def join_names(names, limit=4):
    names = list(names)
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:limit - 1]) + f" and {len(names) - limit + 1} more" if len(names) > limit \
        else ", ".join(names[:-1]) + " and " + names[-1]


def nps_value(df: pd.DataFrame) -> float:
    if df.empty:
        return np.nan
    return 100.0 * ((df["nps_score"] >= 9).mean() - (df["nps_score"] <= 6).mean())


def nps_by(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """NPS and response count per group, vectorised (no groupby.apply)."""
    if df.empty:
        return pd.DataFrame(columns=["responses", "nps"])
    t = pd.DataFrame({"k": df[by].values,
                      "p": (df["nps_score"] >= 9).astype(float).values,
                      "d": (df["nps_score"] <= 6).astype(float).values})
    g = t.groupby("k").agg(responses=("p", "size"), p=("p", "mean"), d=("d", "mean"))
    g["nps"] = 100.0 * (g["p"] - g["d"])
    g.index.name = by
    return g[["responses", "nps"]]


def festive_lift(sales_df: pd.DataFrame) -> float:
    m = sales_df.groupby("month_start")["amount"].sum()
    if m.empty:
        return np.nan
    fest = m[m.index.month >= 10]
    rest = m[m.index.month < 10]
    if fest.empty or rest.empty or rest.mean() == 0:
        return np.nan
    return fest.mean() / rest.mean()


def dealer_summary(dealers_scope, sales_f, service_f, feedback_f, inventory_f, months) -> pd.DataFrame:
    base = dealers_scope[["dealer_id", "dealer_name", "region", "monthly_target"]].set_index("dealer_id")
    s = sales_f.groupby("dealer_id").agg(actual_sales=("amount", "sum"), orders=("sale_id", "size"))
    sv = service_f.groupby("dealer_id").agg(avg_tat=("tat_days", "mean"),
                                            delayed_pct=("is_delayed", "mean"),
                                            service_jobs=("job_id", "size"))
    sv["delayed_pct"] = sv["delayed_pct"] * 100
    fb = nps_by(feedback_f, "dealer_id")
    if inventory_f.empty:
        inv = pd.DataFrame(columns=["stock_units", "aged_pct"])
    else:
        last = inventory_f[inventory_f["snapshot_date"] == inventory_f["snapshot_date"].max()]
        stock = last.groupby("dealer_id")["stock_qty"].sum()
        aged = last[last["aging_bucket"] == "90+"].groupby("dealer_id")["stock_qty"].sum()
        inv = pd.DataFrame({"stock_units": stock, "aged_units": aged}).fillna(0)
        inv["aged_pct"] = 100.0 * inv["aged_units"] / inv["stock_units"].replace(0, np.nan)
        inv = inv[["stock_units", "aged_pct"]]
    out = base.join([s, sv, fb, inv], how="left")
    out["actual_sales"] = out["actual_sales"].fillna(0)
    out["target_sales"] = out["monthly_target"] * months
    out["achievement_pct"] = 100.0 * out["actual_sales"] / out["target_sales"].replace(0, np.nan)
    return out.reset_index()


def slow_mask(ds: pd.DataFrame) -> pd.Series:
    """Same rule as SQL Q7: average TAT more than 25% above the dealer average."""
    if ds["avg_tat"].dropna().empty:
        return pd.Series(False, index=ds.index)
    return ds["avg_tat"] > 1.25 * ds["avg_tat"].mean()


def conv_by(df: pd.DataFrame, col: str) -> pd.DataFrame:
    g = df.groupby(col).agg(sessions=("session_id", "size"), orders=("converted", "sum")).reset_index()
    g["conv"] = 100.0 * g["orders"] / g["sessions"]
    g["share"] = 100.0 * g["sessions"] / g["sessions"].sum()
    return g


def channel_table(camp: pd.DataFrame) -> pd.DataFrame:
    g = camp.groupby("channel").agg(spend=("spend", "sum"), leads=("leads", "sum"),
                                    conversions=("conversions", "sum"),
                                    gross_profit=("gross_profit_attributed", "sum")).reset_index()
    g["cost_per_lead"] = g["spend"] / g["leads"]
    g["cost_per_conversion"] = g["spend"] / g["conversions"]
    g["lead_to_sale_pct"] = 100.0 * g["conversions"] / g["leads"]
    g["roi"] = (g["gross_profit"] - g["spend"]) / g["spend"]
    return g


def issue_table(calls: pd.DataFrame) -> pd.DataFrame:
    g = calls.groupby("issue_type").agg(calls=("call_id", "size"), aht=("duration_min", "mean"),
                                        resolution=("resolved", "mean"),
                                        negative=("is_negative", "mean"),
                                        neg_calls=("is_negative", "sum")).reset_index()
    g["resolution"] *= 100
    g["negative"] *= 100
    g["call_share"] = 100.0 * g["calls"] / g["calls"].sum()
    g["neg_share"] = 100.0 * g["neg_calls"] / max(g["neg_calls"].sum(), 1)
    return g


def agent_table(calls: pd.DataFrame) -> pd.DataFrame:
    g = calls.groupby("agent_id").agg(calls=("call_id", "size"), aht=("duration_min", "mean"),
                                      resolution=("resolved", "mean"), csat=("csat", "mean"),
                                      negative=("is_negative", "mean")).reset_index()
    g["resolution"] *= 100
    g["negative"] *= 100
    return g


# ----------------------------------------------------------------------------
# Rendering helpers
# ----------------------------------------------------------------------------
def e(text) -> str:
    return html.escape(str(text))


def masthead():
    st.markdown(
        '<div class="mast"><div class="brand">AutoNova<span>Omnichannel analytics</span></div>'
        '<div class="note">Synthetic data. Patterns were planted for practice, so the findings show '
        'method, not real business results.</div></div>', unsafe_allow_html=True)


def lede(headline: str, sub: str = ""):
    p = f"<p>{e(sub)}</p>" if sub else ""
    st.markdown(f'<div class="lede"><h1>{e(headline)}</h1>{p}</div>', unsafe_allow_html=True)


def section(title: str, note: str = ""):
    n = f"<p>{e(note)}</p>" if note else ""
    st.markdown(f'<div class="sec"><h3>{e(title)}</h3>{n}</div>', unsafe_allow_html=True)


def kpi_strip(items):
    """items: (label, value, note, tone) where tone is '' or 'bad'."""
    cells = "".join(
        f'<div class="kpi {tone}"><div class="kpi-l">{e(label)}</div>'
        f'<div class="kpi-v">{e(value)}</div><div class="kpi-n">{e(note)}</div></div>'
        for label, value, note, tone in items)
    st.markdown(f'<div class="kpis">{cells}</div>', unsafe_allow_html=True)


def fine(text: str):
    st.markdown(f'<p class="fine">{e(text)}</p>', unsafe_allow_html=True)


def style(fig, height=330, legend=False, grid="y"):
    fig.update_layout(
        height=height, margin=dict(l=4, r=18, t=10, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=INK), showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=12)),
        hoverlabel=dict(bgcolor=SURFACE, font=dict(family=FONT, size=13, color=INK)), bargap=0.35)
    axis = dict(zeroline=False, linecolor=RULE, automargin=True,
                tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    fig.update_xaxes(showgrid=(grid == "x"), gridcolor=GRID, **axis)
    fig.update_yaxes(showgrid=(grid == "y"), gridcolor=GRID, **axis)
    return fig


def show(fig, height=330, legend=False, grid="y"):
    st.plotly_chart(style(fig, height, legend, grid), theme=None, config=PLOT_CONFIG, **PLOT_KW)


def hbar(df, x, y, text, flag=None, ref=None, x_title=None, height=None, fmt="%{text}"):
    """Horizontal bars, red where flag is True. df should be sorted ascending by x."""
    d = df.reset_index(drop=True)
    flags = d[flag].tolist() if flag is not None else [False] * len(d)
    fig = go.Figure(go.Bar(
        x=d[x], y=d[y], orientation="h", text=d[text], textposition="outside", cliponaxis=False,
        marker=dict(color=[SIGNAL if f else TEAL for f in flags], line=dict(width=0)),
        hovertemplate="%{y}: " + fmt + "<extra></extra>"))
    fig.update_yaxes(categoryorder="array", categoryarray=d[y].tolist())
    if x_title:
        fig.update_xaxes(title_text=x_title)
    if ref is not None:
        fig.add_vline(x=ref, line_width=1, line_dash="dot", line_color=INK)
    show(fig, height or max(190, 44 * len(d) + 50), grid="x")


def shade_festive(fig, months: pd.Series):
    lo, hi = months.min(), months.max()
    for yr in sorted({m.year for m in months}):
        start, end = pd.Timestamp(yr, 10, 1), pd.Timestamp(yr + 1, 1, 1)
        if start > hi:
            continue
        end = min(end, hi + pd.offsets.MonthBegin(1))
        fig.add_vrect(x0=start, x1=end, fillcolor=RULE, opacity=0.4, line_width=0, layer="below")
    fig.update_xaxes(range=[lo - pd.Timedelta(days=15), hi + pd.Timedelta(days=15)], tickformat="%b %Y")


def line_chart(x, y, name, color=TEAL, ytitle=None, festive=None, zero=False, height=300, fmt=",.1f"):
    fig = go.Figure(go.Scatter(x=x, y=y, mode="lines+markers", name=name,
                               line=dict(color=color, width=2.2), marker=dict(size=5),
                               hovertemplate="%{x|%b %Y}: %{y:" + fmt + "}<extra></extra>"))
    if festive is not None and len(festive):
        shade_festive(fig, festive)
    else:
        fig.update_xaxes(tickformat="%b %Y")
    if zero:
        fig.add_hline(y=0, line_width=1, line_color=INK)
    if ytitle:
        fig.update_yaxes(title_text=ytitle)
    show(fig, height)


def frame(df, config=None, height=None):
    kw = dict(hide_index=True, **FRAME_KW)
    if config:
        kw["column_config"] = config
    if height:
        kw["height"] = height
    st.dataframe(df, **kw)


def colcfg():
    """Column formatting; returns None on Streamlit versions without column_config."""
    return getattr(st, "column_config", None)


# ----------------------------------------------------------------------------
# Load data
# ----------------------------------------------------------------------------
masthead()
loaded, missing = load_tables()
if loaded is None:
    st.error(f"Missing data files in data/clean: {', '.join(m + '.csv' for m in missing)}. "
             "Run the pipeline first: cd python, then python 01_generate_data.py and python 02_clean_and_enrich.py.")
    st.stop()

dealers = loaded["dealers"]
SALES, SERVICE, FEEDBACK = loaded["sales"], loaded["service"], loaded["feedback"]
WEB, CALLS, CAMP, INV, MONTHS = loaded["web"], loaded["calls"], loaded["campaigns"], loaded["inventory"], loaded["months"]

# ----------------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------------
YEAR_OPTIONS = ["All"] + sorted(MONTHS["year_num"].unique().tolist())
REGIONS = ["All"] + sorted(dealers["region"].unique().tolist())


def reset_filters():
    st.session_state["f_year"] = "All"
    st.session_state["f_quarters"] = [1, 2, 3, 4]
    st.session_state["f_region"] = "All"


with st.sidebar:
    st.markdown("### Filters")
    year = st.selectbox("Year", YEAR_OPTIONS, key="f_year",
                        format_func=lambda x: "All years" if x == "All" else str(x))
    quarters = st.multiselect("Quarter", [1, 2, 3, 4], default=[1, 2, 3, 4], key="f_quarters",
                              format_func=lambda q: f"Q{q}")
    region = st.selectbox("Region", REGIONS, key="f_region",
                          format_func=lambda x: "All regions" if x == "All" else x)
    st.button("Reset filters", on_click=reset_filters)
    st.caption("Region applies to sales, service, inventory and NPS. Web sessions, campaigns and "
               "calls are not tied to a dealer, so they ignore it.")

if not quarters:
    st.warning("Choose at least one quarter in the sidebar to see results.")
    st.stop()

page = st.radio("Page", PAGES, horizontal=True, label_visibility="collapsed", key="page")

year_label = "all years" if year == "All" else str(year)
q_label = "all quarters" if len(quarters) == 4 else ", ".join(f"Q{q}" for q in sorted(quarters))
r_label = "all regions" if region == "All" else f"the {region} region"
st.markdown(f'<p class="scope">Showing {year_label}, {q_label}, {r_label}.</p>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Filtered frames
# ----------------------------------------------------------------------------
sales_f = in_period(SALES, year, quarters)
service_f = in_period(SERVICE, year, quarters)
feedback_f = in_period(FEEDBACK, year, quarters)
inventory_f = in_period(INV, year, quarters)
web_f = in_period(WEB, year, quarters)
calls_f = in_period(CALLS, year, quarters)
camp_f = in_period(CAMP, year, quarters)

dealers_scope = dealers
if region != "All":
    dealers_scope = dealers[dealers["region"] == region]
    sales_f = sales_f[sales_f["region"] == region]
    service_f = service_f[service_f["region"] == region]
    feedback_f = feedback_f[feedback_f["region"] == region]
    inventory_f = inventory_f[inventory_f["region"] == region]

period_months = max(len(in_period(MONTHS, year, quarters)), 1)

if sales_f.empty or web_f.empty or calls_f.empty:
    st.warning("No records match these filters. Widen the year, quarter or region.")
    st.stop()

ds = dealer_summary(dealers_scope, sales_f, service_f, feedback_f, inventory_f, period_months)


# ============================================================================
# PAGE: Overview
# ============================================================================
def page_overview():
    total_sales = sales_f["amount"].sum()
    target_total = dealers_scope["monthly_target"].sum() * period_months
    ach = 100.0 * total_sales / target_total if target_total else np.nan
    conv = 100.0 * web_f["converted"].mean()
    aov = web_f.loc[web_f["converted"] == 1, "order_value"].mean()
    nps = nps_value(feedback_f)
    res = 100.0 * calls_f["resolved"].mean()
    below = int((ds["achievement_pct"] < 100).sum())
    lift = festive_lift(sales_f)

    head = f"{below} of {plural(len(ds), 'dealer')} {'is' if below == 1 else 'are'} behind sales target"
    head += f", and festive months sell {lift:.1f}× a normal month." if pd.notna(lift) else "."
    lede(head, f"Sales of {cr(total_sales)} reached {pct(ach, 0)} of target. Web conversion is "
               f"{pct(conv, 2)} and NPS is {nps:.1f}.")

    prom = 100.0 * (feedback_f["nps_score"] >= 9).mean()
    det = 100.0 * (feedback_f["nps_score"] <= 6).mean()
    kpi_strip([
        ("Sales", cr(total_sales), f"{len(sales_f):,} orders", ""),
        ("Target achievement", pct(ach), f"target {cr(target_total)}", "bad" if ach < 100 else ""),
        ("Web conversion", pct(conv, 2), f"{len(web_f):,} sessions", ""),
        ("Average order value", inr(aov), "buying sessions only", ""),
        ("NPS", f"{nps:.1f}", f"{prom:.0f}% promoters, {det:.0f}% detractors", "bad" if nps < 0 else ""),
        ("Calls resolved", pct(res), f"{len(calls_f):,} calls", ""),
    ])

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        section("Monthly sales", "Grey bands mark October to December.")
        m = sales_f.groupby("month_start")["amount"].sum().reset_index()
        line_chart(m["month_start"], m["amount"] / 1e6, "Sales", ytitle="₹ million",
                   festive=m["month_start"], fmt=",.0f", height=320)
    with c2:
        section("Revenue by product", "Share of sales value.")
        p = sales_f.groupby("product")["amount"].sum().sort_values().reset_index()
        p["share"] = 100.0 * p["amount"] / p["amount"].sum()
        p["label"] = p["share"].map(lambda v: f"{v:.0f}%")
        hbar(p, "amount", "product", "label", height=320, fmt="%{text} of sales")

    section("Target achievement by region", "Dotted line is 100% of target. Red means behind target.")
    rs = sales_f.groupby("region")["amount"].sum()
    rt = dealers_scope.groupby("region")["monthly_target"].sum() * period_months
    r = pd.DataFrame({"sales": rs, "target": rt}).dropna().reset_index()
    r["ach"] = 100.0 * r["sales"] / r["target"]
    r = r.sort_values("ach")
    r["label"] = r["ach"].map(lambda v: f"{v:.0f}%")
    r["behind"] = r["ach"] < 100
    hbar(r, "ach", "region", "label", flag="behind", ref=100, height=max(180, 56 * len(r) + 40))
    fine("A region can look healthy while a few dealers inside it are not. The Dealers page separates the two.")


# ============================================================================
# PAGE: Digital
# ============================================================================
def page_digital():
    st.caption("Web sessions, chatbot and the connected app are not tied to a dealer, so the region filter does not apply here.") if region != "All" else None
    n = len(web_f)
    overall = 100.0 * web_f["converted"].mean()
    src = conv_by(web_f, "source")
    big = src[src["share"] >= 10]
    dev = conv_by(web_f[web_f["device"].isin(["Mobile", "Desktop"])], "device").set_index("device")
    mob = dev["conv"].get("Mobile", np.nan)
    desk = dev["conv"].get("Desktop", np.nan)

    if not big.empty and big["conv"].min() < 0.6 * overall:
        w = big.loc[big["conv"].idxmin()]
        head = f"{w['source']} brings {w['share']:.0f}% of web sessions but converts at {w['conv']:.1f}%, against {overall:.1f}% overall."
    else:
        head = f"Web conversion is {overall:.1f}% across {n:,} sessions, with no large source far below the average."
    lede(head, f"Mobile converts at {pct(mob)} against {pct(desk)} on desktop. The checks below test whether that gap "
               "is real or just a result of which channels send mobile traffic.")

    bot = web_f[web_f["platform"] == "Chatbot"]
    esc = 100.0 * bot["chatbot_escalated"].mean() if len(bot) else np.nan
    mob_share = 100.0 * (web_f["device"] == "Mobile").mean()
    aov = web_f.loc[web_f["converted"] == 1, "order_value"].mean()
    kpi_strip([
        ("Sessions", f"{n:,}", "website, chatbot and app", ""),
        ("Orders", f"{int(web_f['converted'].sum()):,}", "converted sessions", ""),
        ("Conversion", pct(overall, 2), "orders per session", ""),
        ("Average order value", inr(aov), "buying sessions only", ""),
        ("Chatbot escalations", pct(esc), "chatbot sessions passed to a human", ""),
        ("Mobile share", pct(mob_share), "of all sessions", ""),
    ])

    c1, c2 = st.columns(2, gap="large")
    with c1:
        section("Conversion by traffic source", "Red marks sources converting at less than 60% of the overall rate. Dotted line is the overall rate.")
        s = src.sort_values("conv").copy()
        s["label"] = s.apply(lambda r: f"{r['conv']:.1f}%  ({r['share']:.0f}% of traffic)", axis=1)
        s["weak"] = s["conv"] < 0.6 * overall
        hbar(s, "conv", "source", "label", flag="weak", ref=overall, height=330)
    with c2:
        section("Does mobile trail desktop inside each source?",
                "If mobile is lower within most sources, the gap is real and not a traffic-mix effect.")
        d = web_f[web_f["device"].isin(["Mobile", "Desktop"])]
        piv = d.groupby(["source", "device"])["converted"].mean().mul(100).unstack("device").dropna()
        if {"Mobile", "Desktop"} <= set(piv.columns) and len(piv):
            piv = piv.sort_values("Desktop")
            fig = go.Figure()
            fig.add_bar(y=piv.index, x=piv["Desktop"], name="Desktop", orientation="h", marker_color=SOFT,
                        hovertemplate="%{y}, desktop: %{x:.1f}%<extra></extra>")
            fig.add_bar(y=piv.index, x=piv["Mobile"], name="Mobile", orientation="h", marker_color=TEAL,
                        hovertemplate="%{y}, mobile: %{x:.1f}%<extra></extra>")
            fig.update_layout(barmode="group", bargap=0.3)
            fig.update_xaxes(title_text="Conversion %")
            show(fig, 330, legend=True, grid="x")
            lower = int((piv["Mobile"] < piv["Desktop"]).sum())
            fine(f"Mobile converts below desktop in {lower} of {len(piv)} sources.")
        else:
            fine("Not enough device data in this selection.")

    c3, c4 = st.columns(2, gap="large")
    with c3:
        section("Platform and device", "Conversion % for each combination (unknown devices left out).")
        k = web_f[web_f["device"] != "Unknown"]
        mat = k.groupby(["platform", "device"])["converted"].mean().mul(100).unstack("device")
        if not mat.empty:
            fig = go.Figure(go.Heatmap(z=mat.values, x=list(mat.columns), y=list(mat.index),
                                       text=np.round(mat.values, 1), texttemplate="%{text}%",
                                       colorscale=[[0, "#E6F0F1"], [1, TEAL]], showscale=False,
                                       hovertemplate="%{y}, %{x}: %{z:.1f}%<extra></extra>"))
            show(fig, 260)
    with c4:
        section("Chatbot outcomes", "Escalated sessions may be harder cases from the start, so this shows association, not cause.")
        if len(bot):
            o = bot.assign(outcome=np.where(bot["chatbot_escalated"] == 1, "Escalated to a human", "Handled by the bot"))
            g = o.groupby("outcome")["converted"].agg(["mean", "size"]).reset_index()
            g["conv"] = g["mean"] * 100
            g = g.sort_values("conv")
            g["label"] = g.apply(lambda r: f"{r['conv']:.1f}%  ({int(r['size']):,} sessions)", axis=1)
            g["weak"] = g["outcome"].str.startswith("Escalated")
            hbar(g, "conv", "outcome", "label", flag="weak", height=210)

    section("Conversion by month")
    mc = web_f.groupby("month_start")["converted"].mean().mul(100).reset_index()
    line_chart(mc["month_start"], mc["converted"], "Conversion", ytitle="Conversion %", height=280, fmt=".2f")


# ============================================================================
# PAGE: Dealers
# ============================================================================
def page_dealers():
    slow = slow_mask(ds)
    if slow.any():
        a, b = ds[slow], ds[~slow]
        regs = a["region"].unique()
        where = f", all in {regs[0]}" if len(regs) == 1 else ""
        head = (f"{plural(int(slow.sum()), 'dealer')} run service slower than the network{where}: "
                f"{a['avg_tat'].mean():.1f} days on average against {b['avg_tat'].mean():.1f}.")
        sub = (f"Their NPS is {a['nps'].mean():.0f} against {b['nps'].mean():.0f} for the rest, and they reach "
               f"{a['achievement_pct'].min():.0f}% to {a['achievement_pct'].max():.0f}% of sales target.")
    else:
        head = "No dealer stands out on service speed in this selection."
        sub = (f"Target achievement ranges from {ds['achievement_pct'].min():.0f}% to "
               f"{ds['achievement_pct'].max():.0f}% across {plural(len(ds), 'dealer')}.")
    lede(head, sub)

    section("Dealer scorecard", "Sorted from lowest target achievement. Slow means average service turnaround more than 25% above the dealer average.")
    show_df = ds.sort_values("achievement_pct")[[
        "dealer_name", "region", "actual_sales", "target_sales", "achievement_pct",
        "avg_tat", "delayed_pct", "nps", "aged_pct"]].copy()
    cc = colcfg()
    cfg = None
    if cc is not None:
        try:
            cfg = {
                "dealer_name": cc.TextColumn("Dealer"),
                "region": cc.TextColumn("Region"),
                "actual_sales": cc.NumberColumn("Sales (₹)", format="%.0f"),
                "target_sales": cc.NumberColumn("Target (₹)", format="%.0f"),
                "achievement_pct": cc.ProgressColumn("Target achieved", min_value=0, max_value=150, format="%.0f%%"),
                "avg_tat": cc.NumberColumn("Service days", format="%.1f"),
                "delayed_pct": cc.NumberColumn("Late jobs %", format="%.0f"),
                "nps": cc.NumberColumn("NPS", format="%.0f"),
                "aged_pct": cc.NumberColumn("Stock 90+ days %", format="%.0f"),
            }
        except Exception:
            cfg = None
    frame(show_df, cfg, height=420)
    st.download_button("Download scorecard (CSV)", ds.round(2).to_csv(index=False).encode("utf-8"),
                       file_name="dealer_scorecard.csv", mime="text/csv")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        section("Service speed against NPS", "Each dot is a dealer; size shows sales. Red dots are the slow dealers.")
        pts = ds.dropna(subset=["avg_tat", "nps"]).copy()
        pts["slow"] = slow_mask(pts) if len(pts) else False
        size = 9 + 22 * (pts["actual_sales"] / max(pts["actual_sales"].max(), 1))
        fig = go.Figure()
        for flag, color, name in [(False, TEAL, "Other dealers"), (True, SIGNAL, "Slow dealers")]:
            sel = pts["slow"] == flag
            if sel.any():
                fig.add_trace(go.Scatter(
                    x=pts.loc[sel, "avg_tat"], y=pts.loc[sel, "nps"], mode="markers", name=name,
                    marker=dict(color=color, size=size[sel], opacity=0.85, line=dict(width=0)),
                    customdata=pts.loc[sel, "dealer_name"],
                    hovertemplate="%{customdata}<br>Service %{x:.1f} days, NPS %{y:.0f}<extra></extra>"))
        fig.update_xaxes(title_text="Average service days")
        fig.update_yaxes(title_text="NPS")
        show(fig, 340, legend=True)
    with c2:
        section("Lowest target achievement", "Ten dealers furthest behind. Dotted line is 100%.")
        b = ds.sort_values("achievement_pct").head(10).sort_values("achievement_pct", ascending=False).copy()
        b["label"] = b["achievement_pct"].map(lambda v: f"{v:.0f}%")
        b["behind"] = b["achievement_pct"] < 100
        hbar(b, "achievement_pct", "dealer_name", "label", flag="behind", ref=100, height=340)

    section("Dealer detail", "Pick one dealer to see it next to the network.")
    names = ds["dealer_name"].tolist()
    pick = st.selectbox("Dealer", names, key="dealer_pick", label_visibility="collapsed")
    row = ds[ds["dealer_name"] == pick].iloc[0]
    net_tat = ds["avg_tat"].mean()
    kpi_strip([
        ("Sales", cr(row["actual_sales"]), f"target {cr(row['target_sales'])}", "bad" if row["achievement_pct"] < 100 else ""),
        ("Target achieved", pct(row["achievement_pct"], 0), "of period target", "bad" if row["achievement_pct"] < 100 else ""),
        ("Service days", "n/a" if pd.isna(row["avg_tat"]) else f"{row['avg_tat']:.1f}", f"dealer average {net_tat:.1f}",
         "bad" if pd.notna(row["avg_tat"]) and row["avg_tat"] > 1.25 * net_tat else ""),
        ("NPS", "n/a" if pd.isna(row["nps"]) else f"{row['nps']:.0f}", f"{int(row['responses']) if pd.notna(row['responses']) else 0} responses",
         "bad" if pd.notna(row["nps"]) and row["nps"] < 0 else ""),
        ("Stock aged 90+ days", pct(row["aged_pct"], 0), f"{int(row['stock_units']) if pd.notna(row['stock_units']) else 0} units in stock", ""),
    ])
    d1, d2 = st.columns(2, gap="large")
    with d1:
        section("Monthly sales against target")
        ms = sales_f[sales_f["dealer_name"] == pick].groupby("month_start")["amount"].sum().reset_index()
        fig = go.Figure(go.Scatter(x=ms["month_start"], y=ms["amount"] / 1e6, mode="lines+markers", name="Sales",
                                   line=dict(color=TEAL, width=2.2), marker=dict(size=5),
                                   hovertemplate="%{x|%b %Y}: ₹%{y:.1f} mn<extra></extra>"))
        fig.add_hline(y=row["monthly_target"] / 1e6, line_dash="dot", line_color=INK, line_width=1,
                      annotation_text="Monthly target", annotation_position="top left")
        fig.update_yaxes(title_text="₹ million")
        fig.update_xaxes(tickformat="%b %Y")
        show(fig, 300)
    with d2:
        section("What this dealer's detractors say")
        det = feedback_f[(feedback_f["dealer_name"] == pick) & (feedback_f["nps_category"] == "Detractor")]
        det = det[det["theme"] != "No comment"]
        if len(det):
            t = det.groupby("theme").size().sort_values().reset_index(name="n")
            t["label"] = (100.0 * t["n"] / t["n"].sum()).map(lambda v: f"{v:.0f}%")
            hbar(t, "n", "theme", "label", height=max(200, 44 * len(t) + 50), fmt="%{x} comments")
        else:
            fine("No detractor comments for this dealer in the selected period.")


# ============================================================================
# PAGE: Marketing & NPS
# ============================================================================
def page_marketing():
    st.caption("Campaigns are not tied to a dealer, so the region filter does not apply to the channel results.") if region != "All" else None
    ch = channel_table(camp_f)
    nps = nps_value(feedback_f)
    best, worst = ch.loc[ch["roi"].idxmax()], ch.loc[ch["roi"].idxmin()]
    lede(f"{worst['channel']} returns {times(worst['roi'])} on spend, while {best['channel']} returns {times(best['roi'])}.",
         "ROI is attributed gross profit minus spend, divided by spend. Owned channels such as email reach a limited "
         "audience, so their ratios will not hold if budgets are scaled up.")

    spend, leads, convs = ch["spend"].sum(), ch["leads"].sum(), ch["conversions"].sum()
    blended = (ch["gross_profit"].sum() - spend) / spend
    kpi_strip([
        ("Campaign spend", cr(spend), f"{len(camp_f)} campaigns", ""),
        ("Leads", f"{int(leads):,}", f"{pct(100.0 * convs / leads)} become sales", ""),
        ("Cost per sale", inr(spend / convs), "spend per conversion", ""),
        ("Blended ROI", times(blended), "all channels together", ""),
        ("NPS", f"{nps:.1f}", f"{len(feedback_f):,} survey responses", "bad" if nps < 0 else ""),
    ])

    c1, c2 = st.columns(2, gap="large")
    with c1:
        section("Return on spend by channel", "Red marks channels returning less than 1.5× their spend.")
        t = ch.sort_values("roi").copy()
        t["label"] = t["roi"].map(times)
        t["weak"] = t["roi"] < 1.5
        hbar(t, "roi", "channel", "label", flag="weak", height=330)
    with c2:
        section("Spend and sales by campaign", "Each dot is one campaign.")
        fig = go.Figure()
        for i, (name, g) in enumerate(camp_f.groupby("channel")):
            fig.add_trace(go.Scatter(x=g["spend"] / 1e6, y=g["conversions"], mode="markers", name=name,
                                     marker=dict(color=PALETTE[i % len(PALETTE)], size=8, opacity=0.8),
                                     customdata=g["campaign_name"],
                                     hovertemplate="%{customdata}<br>₹%{x:.1f} mn, %{y} sales<extra></extra>"))
        fig.update_xaxes(title_text="Spend (₹ million)")
        fig.update_yaxes(title_text="Sales")
        show(fig, 330, legend=True)

    section("Channel detail")
    tbl = ch.sort_values("roi", ascending=False)[["channel", "spend", "leads", "conversions", "cost_per_lead",
                                                   "cost_per_conversion", "lead_to_sale_pct", "roi"]]
    cc = colcfg()
    cfg = None
    if cc is not None:
        try:
            cfg = {"channel": cc.TextColumn("Channel"), "spend": cc.NumberColumn("Spend (₹)", format="%.0f"),
                   "leads": cc.NumberColumn("Leads", format="%d"), "conversions": cc.NumberColumn("Sales", format="%d"),
                   "cost_per_lead": cc.NumberColumn("Cost per lead (₹)", format="%.0f"),
                   "cost_per_conversion": cc.NumberColumn("Cost per sale (₹)", format="%.0f"),
                   "lead_to_sale_pct": cc.NumberColumn("Lead to sale %", format="%.1f"),
                   "roi": cc.NumberColumn("ROI (×)", format="%.1f")}
        except Exception:
            cfg = None
    frame(tbl, cfg)

    section("NPS by month", "Promoters score 9 or 10, detractors 0 to 6. NPS is promoters minus detractors, in percentage points.")
    nm = nps_by(feedback_f, "month_start").reset_index()
    line_chart(nm["month_start"], nm["nps"], "NPS", ytitle="NPS", zero=True, height=280, fmt=".1f")

    c3, c4 = st.columns(2, gap="large")
    with c3:
        section("Promoters, passives and detractors")
        mix = feedback_f.groupby(["month_start", "nps_category"]).size().unstack(fill_value=0)
        mix = mix.div(mix.sum(axis=1), axis=0) * 100
        fig = go.Figure()
        for cat, col in [("Promoter", TEAL), ("Passive", SOFT), ("Detractor", SIGNAL)]:
            if cat in mix.columns:
                fig.add_bar(x=mix.index, y=mix[cat], name=cat, marker_color=col,
                            hovertemplate="%{x|%b %Y}: %{y:.0f}%<extra>" + cat + "</extra>")
        fig.update_layout(barmode="stack", bargap=0.15)
        fig.update_yaxes(title_text="% of responses")
        fig.update_xaxes(tickformat="%b %Y")
        show(fig, 300, legend=True)
    with c4:
        section("What detractors complain about", "Themes come from keyword matching on comments, so shares are approximate.")
        dt = feedback_f[(feedback_f["nps_category"] == "Detractor") & (feedback_f["theme"] != "No comment")]
        if len(dt):
            th = dt.groupby("theme").size().sort_values().reset_index(name="n")
            th["label"] = (100.0 * th["n"] / th["n"].sum()).map(lambda v: f"{v:.0f}%")
            hbar(th, "n", "theme", "label", height=300, fmt="%{x} comments")


# ============================================================================
# PAGE: Call center
# ============================================================================
def page_calls():
    st.caption("Calls are not tied to a dealer, so the region filter does not apply here.") if region != "All" else None
    it = issue_table(calls_f)
    top = it.loc[it["neg_share"].idxmax()]
    lede(f"{top['issue_type']} calls are {top['call_share']:.0f}% of volume but {top['neg_share']:.0f}% of all negative calls.",
         f"{top['negative']:.0f}% of these calls end negative and only {top['resolution']:.0f}% are resolved, "
         f"with an average handling time of {top['aht']:.1f} minutes.")

    kpi_strip([
        ("Calls", f"{len(calls_f):,}", "in this selection", ""),
        ("Resolved", pct(100.0 * calls_f["resolved"].mean()), "calls marked resolved", ""),
        ("Average handling time", f"{calls_f['duration_min'].mean():.1f} min", "per call", ""),
        ("Customer satisfaction", f"{calls_f['csat'].mean():.2f}", "average, scale 1 to 5", ""),
        ("Negative calls", pct(100.0 * calls_f["is_negative"].mean()), "sentiment negative", ""),
    ])

    c1, c2 = st.columns(2, gap="large")
    with c1:
        section("Share of all negative calls", "Red marks the issue behind the most negative calls.")
        t = it.sort_values("neg_share").copy()
        t["label"] = t["neg_share"].map(lambda v: f"{v:.0f}%")
        t["worst"] = t["issue_type"] == top["issue_type"]
        hbar(t, "neg_share", "issue_type", "label", flag="worst", height=330, fmt="%{x:.0f}% of negative calls")
    with c2:
        section("How each issue ends", "Sentiment split for every call type.")
        sg = calls_f.groupby(["issue_type", "sentiment"]).size().unstack(fill_value=0)
        sg = sg.div(sg.sum(axis=1), axis=0) * 100
        order = it.sort_values("negative")["issue_type"].tolist()
        fig = go.Figure()
        for cat, col in [("Positive", TEAL), ("Neutral", SOFT), ("Negative", SIGNAL)]:
            if cat in sg.columns:
                fig.add_bar(y=sg.reindex(order).index, x=sg.reindex(order)[cat], name=cat, orientation="h",
                            marker_color=col, hovertemplate="%{y}: %{x:.0f}%<extra>" + cat + "</extra>")
        fig.update_layout(barmode="stack", bargap=0.3)
        fig.update_xaxes(title_text="% of calls", range=[0, 100])
        show(fig, 330, legend=True, grid="x")

    section("Agent results", "Each dot is an agent. Red dots are the lowest quarter by satisfaction.")
    ag = agent_table(calls_f)
    cutoff = ag["csat"].quantile(0.25)
    ag["low"] = ag["csat"] <= cutoff
    fig = go.Figure()
    for flag, color, name in [(False, TEAL, "Other agents"), (True, SIGNAL, "Lowest quarter")]:
        s = ag[ag["low"] == flag]
        if len(s):
            fig.add_trace(go.Scatter(x=s["resolution"], y=s["csat"], mode="markers", name=name,
                                     marker=dict(color=color, size=10, opacity=0.85),
                                     customdata=s["agent_id"],
                                     hovertemplate="Agent %{customdata}<br>Resolved %{x:.0f}%, satisfaction %{y:.2f}<extra></extra>"))
    fig.update_xaxes(title_text="Calls resolved %")
    fig.update_yaxes(title_text="Average satisfaction")
    show(fig, 340, legend=True)
    fine(f"Agent resolution ranges from {ag['resolution'].min():.0f}% to {ag['resolution'].max():.0f}% and satisfaction "
         f"from {ag['csat'].min():.2f} to {ag['csat'].max():.2f}. Differences this wide point to coaching and support, not only effort.")

    section("Agents who need coaching first", "Ten lowest by satisfaction.")
    low = ag.sort_values("csat").head(10)[["agent_id", "calls", "resolution", "csat", "negative", "aht"]]
    cc = colcfg()
    cfg = None
    if cc is not None:
        try:
            cfg = {"agent_id": cc.TextColumn("Agent"), "calls": cc.NumberColumn("Calls", format="%d"),
                   "resolution": cc.NumberColumn("Resolved %", format="%.0f"),
                   "csat": cc.NumberColumn("Satisfaction", format="%.2f"),
                   "negative": cc.NumberColumn("Negative %", format="%.0f"),
                   "aht": cc.NumberColumn("Handling min", format="%.1f")}
        except Exception:
            cfg = None
    frame(low, cfg)

    section("Negative calls by month")
    mn = calls_f.groupby("month_start")["is_negative"].mean().mul(100).reset_index()
    line_chart(mn["month_start"], mn["is_negative"], "Negative calls", color=SIGNAL, ytitle="Negative %", height=280)


# ============================================================================
# PAGE: Findings & method (always the full period, ignores filters)
# ============================================================================
def compute_findings():
    out = []
    months_all = len(MONTHS)
    dsa = dealer_summary(dealers, SALES, SERVICE, FEEDBACK, INV, months_all)
    sm = slow_mask(dsa)
    if sm.any():
        a, b = dsa[sm], dsa[~sm]
        out.append(dict(tone="bad", title=f"{plural(int(sm.sum()), 'dealer')} drive the NPS problem",
            body=f"{join_names(a['dealer_name'])} average {a['avg_tat'].mean():.1f} days of service turnaround against "
                 f"{b['avg_tat'].mean():.1f} elsewhere. Their NPS is {a['nps'].mean():.0f} against {b['nps'].mean():.0f} for "
                 f"the other {len(b)} dealers, and they reach {a['achievement_pct'].min():.0f}% to {a['achievement_pct'].max():.0f}% of sales target.",
            action="Audit service capacity at these dealers before changing sales incentives.", src="SQL Q7, Q16, Q17"))

    overall = 100.0 * WEB["converted"].mean()
    srcs = conv_by(WEB, "source")
    big = srcs[srcs["share"] >= 10]
    if not big.empty:
        w = big.loc[big["conv"].idxmin()]
        ct = channel_table(CAMP)
        r = ct.loc[ct["channel"] == w["source"], "roi"]
        roi_txt = f" Its campaigns return {times(r.iloc[0])} on spend." if len(r) else ""
        out.append(dict(tone="bad", title=f"{w['source']} is a large channel that rarely converts",
            body=f"It supplies {w['share']:.0f}% of web sessions but converts at {w['conv']:.1f}% against {overall:.1f}% overall.{roi_txt}",
            action="Retarget or cut the weakest creative, and shift budget gradually to channels with proven conversion, testing as you go.",
            src="SQL Q11, Q14"))

    dv = WEB[WEB["device"].isin(["Mobile", "Desktop"])]
    piv = dv.groupby(["source", "device"])["converted"].mean().unstack().dropna()
    dv_conv = conv_by(dv, "device").set_index("device")["conv"]
    if len(piv) and {"Mobile", "Desktop"} <= set(dv_conv.index):
        lower = int((piv["Mobile"] < piv["Desktop"]).sum())
        real = lower >= max(1, int(0.7 * len(piv)))
        out.append(dict(tone="bad" if real else "ok",
            title="Mobile converts worse, even inside the same channel" if real else "The mobile gap is mostly a traffic-mix effect",
            body=f"Mobile converts at {dv_conv['Mobile']:.1f}% against {dv_conv['Desktop']:.1f}% on desktop, and is lower in {lower} of {len(piv)} sources. "
                 + ("Because the gap holds within sources, channel mix does not explain it." if real else "Mobile visitors skew toward weaker sources."),
            action="Audit the mobile booking and checkout flow." if real else "Compare channels before blaming the mobile site.", src="SQL Q12"))

    bot = WEB[WEB["platform"] == "Chatbot"]
    if len(bot) and bot["chatbot_escalated"].nunique() == 2:
        g = bot.groupby("chatbot_escalated")["converted"].mean() * 100
        out.append(dict(tone="bad", title="Chatbot escalations lose sales",
            body=f"Sessions passed to a human convert at {g[1]:.1f}% against {g[0]:.1f}% when the bot handles them. "
                 "Escalated sessions may be harder cases from the start, so this is an association, not proof of cause.",
            action="Fix the most common escalation reasons and add a warm hand-off.", src="SQL Q13"))

    it = issue_table(CALLS)
    top = it.loc[it["neg_share"].idxmax()]
    det = FEEDBACK[(FEEDBACK["nps_category"] == "Detractor") & (FEEDBACK["theme"] != "No comment")]
    th = det.groupby("theme").size().sort_values(ascending=False)
    th_txt = ""
    if len(th) >= 2:
        th_txt = (f" In surveys, {th.index[0]} and {th.index[1]} make up {100.0 * th.iloc[:2].sum() / th.sum():.0f}% "
                  "of detractor comments (keyword-based, so approximate).")
    out.append(dict(tone="bad", title=f"{top['issue_type']} is the biggest source of unhappy calls",
        body=f"It is {top['call_share']:.0f}% of call volume but {top['neg_share']:.0f}% of negative calls; {top['negative']:.0f}% end negative and "
             f"{top['resolution']:.0f}% are resolved.{th_txt}",
        action="Create a specialist queue for this issue and make the related customer paperwork clearer.", src="SQL Q18, Q19"))

    ag = agent_table(CALLS)
    out.append(dict(tone="ok", title="Agent results vary widely",
        body=f"Across {len(ag)} agents, resolution runs from {ag['resolution'].min():.0f}% to {ag['resolution'].max():.0f}% and satisfaction from "
             f"{ag['csat'].min():.2f} to {ag['csat'].max():.2f}. These are the single lowest and highest agents, not quartile bounds.",
        action="Coach the lowest-satisfaction quarter on the top issue type above.", src="SQL Q20"))

    lift = festive_lift(SALES)
    if pd.notna(lift):
        out.append(dict(tone="ok", title="October to December is the peak",
            body=f"Average monthly sales in those months are {lift:.1f}× the average of the other months.",
            action="Plan stock, staffing and campaign budget for the peak.", src="SQL Q2, Q6"))
    return out


def page_findings():
    lede("What the data says, and how far to trust it.",
         "These findings use the full period and ignore the sidebar filters, so they match the SQL queries in the project.")
    for f in compute_findings():
        cls = "finding bad" if f["tone"] == "bad" else "finding"
        st.markdown(f'<div class="{cls}"><h4>{e(f["title"])}</h4><p>{e(f["body"])}</p>'
                    f'<p class="act">{e(f["action"])}</p><p class="src">Query: {e(f["src"])}</p></div>',
                    unsafe_allow_html=True)

    section("How this was built")
    with st.expander("Data and method"):
        st.markdown(
            "The data is **synthetic**. A Python script generated 28 dealers in four regions, sales, service jobs, inventory, "
            "campaigns, web, chatbot and app sessions, survey feedback and call logs. Seasonality was added, and a few patterns "
            "were planted on purpose (slow service at four dealers, a weak paid channel, billing-heavy complaints). "
            "Duplicates, blanks, mistyped amounts and inconsistent text were also injected, then cleaned and logged.\n\n"
            "NPS is the share of promoters (9 to 10) minus the share of detractors (0 to 6). Theme and sentiment tags on survey "
            "comments come from keyword rules, so they are approximate.")
    with st.expander("Data cleaning log"):
        p = DOCS_DIR / "data_quality_log.csv"
        if p.exists():
            frame(pd.read_csv(p))
        else:
            fine("Run python/02_clean_and_enrich.py to create docs/data_quality_log.csv.")
    with st.expander("Tables and row counts"):
        rows = [("dealers", len(dealers), "One row per dealer, with region and monthly target"),
                ("sales", len(SALES), "One row per order"),
                ("service_jobs", len(SERVICE), "One row per service job"),
                ("inventory", len(INV), "Dealer, product and month-end stock snapshot"),
                ("campaigns", len(CAMP), "One row per marketing campaign"),
                ("web_sessions", len(WEB), "One row per website, chatbot or app session"),
                ("feedback", len(FEEDBACK), "One row per NPS survey response"),
                ("call_logs", len(CALLS), "One row per call center call")]
        frame(pd.DataFrame(rows, columns=["Table", "Rows", "What a row is"]))
    with st.expander("Limits of this analysis"):
        st.markdown(
            "- Planted patterns are easy to find. Real data is messier, so treat results as a demonstration of method.\n"
            "- Keyword tagging of comments is crude and will miss sarcasm and mixed feedback.\n"
            "- Correlation is not cause. A slow dealer with low NPS may have other problems.\n"
            "- Budget moves suggested by channel ROI assume the cost per sale holds as spend grows, which it usually does not.")


# ----------------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------------
{"Overview": page_overview, "Digital": page_digital, "Dealers": page_dealers,
 "Marketing & NPS": page_marketing, "Call center": page_calls,
 "Findings & method": page_findings}[page]()

st.markdown('<p class="fine" style="margin-top:3rem">Built with Python, Pandas, Plotly and Streamlit from the cleaned tables '
            'behind the project\'s 20 SQL queries. All data is synthetic.</p>', unsafe_allow_html=True)