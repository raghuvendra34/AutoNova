"""
02_clean_and_enrich.py
Cleans raw CSVs, engineers features, tags sentiment/themes in feedback,
writes clean CSVs (for Power BI) and loads everything into SQLite (for SQL).
Also writes a data-quality log documenting every fix.
"""
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)
log = []


def note(table, issue, action, n):
    log.append({"table": table, "issue": issue, "action": action, "rows_affected": int(n)})


def load(name, dates=()):
    return pd.read_csv(RAW / f"{name}.csv", parse_dates=list(dates))


# ------------------------------------------------------------- dealers / campaigns / inventory
dealers = load("dealers")
campaigns = load("campaigns")
campaigns["cost_per_lead"] = (campaigns.spend / campaigns.leads).round(2)
campaigns["lead_to_conv_pct"] = (100 * campaigns.conversions / campaigns.leads).round(2)
campaigns["roi_x"] = ((campaigns.gross_profit_attributed - campaigns.spend) / campaigns.spend).round(2)
inventory = load("inventory", ["snapshot_date"])
inventory["aging_bucket"] = pd.cut(inventory.avg_age_days, [-1, 30, 60, 90, 999], labels=["0-30", "31-60", "61-90", "90+"])

# ------------------------------------------------------------- sales
sales = load("sales", ["sale_date"])
n = sales.duplicated("sale_id").sum(); sales = sales.drop_duplicates("sale_id"); note("sales", "duplicate sale_id", "dropped", n)
n = sales.payment_mode.isna().sum(); sales["payment_mode"] = sales.payment_mode.fillna("Unknown"); note("sales", "null payment_mode", "filled 'Unknown'", n)
# outliers: amount > 3x the product median -> data-entry error; replace with product median
med = sales.groupby("product").amount.transform("median")
out = sales.amount > 3 * med
note("sales", "amount > 3x product median (entry error)", "replaced with product median", out.sum())
sales.loc[out, "amount"] = med[out]
sales["year"], sales["month"] = sales.sale_date.dt.year, sales.sale_date.dt.month
sales["year_month"] = sales.sale_date.dt.to_period("M").astype(str)
sales["day_of_week"] = sales.sale_date.dt.day_name()
sales["is_festive_q"] = sales.month.isin([10, 11, 12]).astype(int)

# ------------------------------------------------------------- service
svc = load("service_jobs", ["job_date"])
n = svc.duplicated("job_id").sum(); svc = svc.drop_duplicates("job_id"); note("service_jobs", "duplicate job_id", "dropped", n)
n = svc.tat_days.isna().sum()
svc["tat_days"] = svc.tat_days.fillna(svc.groupby("job_type").tat_days.transform("median"))
note("service_jobs", "null tat_days", "filled with job_type median", n)
svc["tat_flag"] = np.where(svc.tat_days > svc.groupby("job_type").tat_days.transform(lambda x: x.quantile(.9)), "Delayed", "On time")
svc["year_month"] = svc.job_date.dt.to_period("M").astype(str)

# ------------------------------------------------------------- web
web = load("web_sessions", ["session_date"])
n = web.duplicated("session_id").sum(); web = web.drop_duplicates("session_id"); note("web_sessions", "duplicate session_id", "dropped", n)
n = web.device.isna().sum(); web["device"] = web.device.fillna("Unknown"); note("web_sessions", "null device", "filled 'Unknown'", n)
web["aov_bucket"] = pd.cut(web.order_value, [0, 25_000, 50_000, 100_000, 1e9], labels=["<25k", "25-50k", "50-100k", "100k+"])
web["year_month"] = web.session_date.dt.to_period("M").astype(str)

# ------------------------------------------------------------- feedback: NPS category + sentiment + themes
fb = load("feedback", ["feedback_date"])
n = fb.duplicated("feedback_id").sum(); fb = fb.drop_duplicates("feedback_id"); note("feedback", "duplicate feedback_id", "dropped", n)
n = fb.comment.isna().sum(); fb["comment"] = fb.comment.fillna(""); note("feedback", "null comment", "set empty; excluded from theme analysis", n)
fb["nps_category"] = np.select([fb.nps_score >= 9, fb.nps_score <= 6], ["Promoter", "Detractor"], "Passive")

THEMES = {  # keyword-based theme tagging (rule-based NLP)
    "Service Delay": ["too many days", "no update", "turnaround", "status"],
    "Delivery Delay": ["delivery was delayed", "delayed again"],
    "Staff Behaviour": ["rude", "behaviour", "helpful", "friendly", "executive"],
    "Pricing / Billing": ["hidden charges", "billing", "pricing", "price"],
    "App / Digital": ["app "],
    "Waiting Time": ["waiting"],
}
NEG_WORDS = ["delay", "rude", "hidden", "crash", "wrong", "unresolved", "long", "no update", "too many"]
POS_WORDS = ["great", "smooth", "fair", "quick", "helpful", "easy", "friendly", "recommend"]


def theme(text):
    t = (text + " ").lower()
    for k, kws in THEMES.items():
        if any(w in t for w in kws):
            return k
    return "General / Other" if t.strip() else "No comment"


def polarity(text):
    t = text.lower()
    s = sum(w in t for w in POS_WORDS) - sum(w in t for w in NEG_WORDS)
    return "Positive" if s > 0 else "Negative" if s < 0 else "Neutral"


fb["theme"] = fb.comment.map(theme)
fb["comment_sentiment"] = fb.comment.map(polarity)
fb["year_month"] = fb.feedback_date.dt.to_period("M").astype(str)

# ------------------------------------------------------------- calls
calls = load("call_logs", ["call_date"])
n = calls.duplicated("call_id").sum(); calls = calls.drop_duplicates("call_id"); note("call_logs", "duplicate call_id", "dropped", n)
n = (calls.issue_type != calls.issue_type.str.title()).sum()
calls["issue_type"] = calls.issue_type.str.title().str.replace("App/Technical", "App/Technical").str.replace("Booking/Appointment", "Booking/Appointment")
note("call_logs", "inconsistent text case in issue_type", "standardised to Title Case", n)
n = calls.sentiment.isna().sum()
calls["sentiment"] = calls.sentiment.fillna("Neutral"); note("call_logs", "null sentiment", "filled 'Neutral'", n)
calls["aht_bucket"] = pd.cut(calls.duration_min, [0, 5, 10, 15, 999], labels=["<5", "5-10", "10-15", "15+"])
calls["year_month"] = calls.call_date.dt.to_period("M").astype(str)

# ------------------------------------------------------------- write outputs
tables = dict(dealers=dealers, sales=sales, service_jobs=svc, inventory=inventory, campaigns=campaigns,
              web_sessions=web, feedback=fb, call_logs=calls)

# date dimension for Power BI star schema
dim = pd.DataFrame({"date": pd.date_range("2024-01-01", "2025-12-31")})
dim["year"], dim["month_num"] = dim.date.dt.year, dim.date.dt.month
dim["month_name"], dim["year_month"] = dim.date.dt.strftime("%b"), dim.date.dt.to_period("M").astype(str)
dim["quarter"] = "Q" + dim.date.dt.quarter.astype(str)
dim["day_name"] = dim.date.dt.day_name()
tables["dim_date"] = dim

con = sqlite3.connect(ROOT / "data" / "omnichannel.db")
for name, df in tables.items():
    df = df.copy()
    for c in df.select_dtypes("datetime").columns:
        df[c] = df[c].dt.strftime("%Y-%m-%d")
    for c in df.select_dtypes("category").columns:
        df[c] = df[c].astype(str)
    df.to_csv(CLEAN / f"{name}.csv", index=False)
    df.to_sql(name, con, if_exists="replace", index=False)
    print(f"{name:14s} {len(df):>7,} rows -> clean csv + sqlite")
con.close()
pd.DataFrame(log).to_csv(ROOT / "docs" / "data_quality_log.csv", index=False)
print("\nData-quality log:\n", pd.DataFrame(log).to_string(index=False))
