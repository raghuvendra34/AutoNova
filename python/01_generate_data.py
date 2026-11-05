"""
01_generate_data.py
Generates a SYNTHETIC dataset for an automotive + service brand operating
across dealers, web/chatbot/app and a call center.
All data is fictional. Seeded for reproducibility.
Deliberate "hidden patterns" are planted so the analysis has real findings:
  - Paid Social: high traffic, lowest conversion
  - 4 dealers in the East region: high service TAT + low NPS
  - Billing disputes drive most negative call sentiment
  - Chatbot sessions that escalate convert less
Some dirty data (nulls, duplicates, typos, outliers) is injected on purpose
so the cleaning step is genuine.
"""
import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
OUT = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")
DAYS = (END - START).days + 1


# ---------------------------------------------------------------- dealers
regions = {"North": ["Delhi", "Chandigarh", "Lucknow"],
           "South": ["Bangalore", "Chennai", "Hyderabad", "Kochi"],
           "West": ["Mumbai", "Pune", "Ahmedabad"],
           "East": ["Kolkata", "Patna", "Bhubaneswar", "Guwahati"]}
rows, did = [], 1
for reg, cities in regions.items():
    for c in cities:
        for k in range(2):
            rows.append((f"D{did:03d}", f"{c} Motors {k+1}", c, reg,
                         rng.choice(["Aarav", "Meera", "Rohit", "Sana", "Vikram", "Neha", "Karan", "Isha"]),
                         int(rng.integers(18_000_000, 28_000_000))))  # monthly sales target (INR)
            did += 1
dealers = pd.DataFrame(rows, columns=["dealer_id", "dealer_name", "city", "region", "manager", "monthly_target"])
dealer_ids = dealers.dealer_id.tolist()
# weak dealers (planted): 4 in East
weak = dealers[dealers.region == "East"].dealer_id.tolist()[:4]
dealer_strength = {d: (0.7 if d in weak else rng.uniform(0.85, 1.25)) for d in dealer_ids}

# ---------------------------------------------------------------- products
products = {"Hatchback": 650_000, "Sedan": 950_000, "SUV": 1_350_000, "EV": 1_600_000, "Accessories Pack": 45_000}
pnames = list(products)

# ---------------------------------------------------------------- sales
N_SALES = 18_000
w = np.array([dealer_strength[d] for d in dealer_ids]); w /= w.sum()
s_dealer = rng.choice(dealer_ids, N_SALES, p=w)
s_prod = rng.choice(pnames, N_SALES, p=[0.28, 0.2, 0.25, 0.07, 0.20])
s_date = START + pd.to_timedelta(rng.integers(0, DAYS, N_SALES), unit="D")
# festive uplift: move ~25% of sales into Oct-Dec window
mask = rng.random(N_SALES) < 0.25
fest = pd.to_datetime(rng.choice([2024, 2025], N_SALES).astype(str)) + pd.to_timedelta(273 + rng.integers(0, 92, N_SALES), unit="D")
s_date = pd.DatetimeIndex(np.where(mask, fest, s_date))
amount = np.array([products[p] for p in s_prod]) * rng.normal(1.0, 0.07, N_SALES)
sales = pd.DataFrame({"sale_id": [f"S{i:06d}" for i in range(1, N_SALES + 1)], "dealer_id": s_dealer,
                      "product": s_prod, "amount": amount.round(0), "sale_date": s_date,
                      "payment_mode": rng.choice(["Finance", "Cash", "Card", "Exchange"], N_SALES, p=[.45, .25, .15, .15])})

# ---------------------------------------------------------------- service_jobs
N_JOBS = 20_000
sj_dealer = rng.choice(dealer_ids, N_JOBS)
job_type = rng.choice(["Periodic Service", "Repair", "Warranty", "Accident Repair", "Wash & Detail"], N_JOBS, p=[.4, .25, .15, .08, .12])
base_tat = {"Periodic Service": 1.5, "Repair": 3, "Warranty": 3.5, "Accident Repair": 7, "Wash & Detail": 0.5}
tat = np.array([base_tat[j] for j in job_type]) * rng.lognormal(0, 0.3, N_JOBS)
tat = np.where(np.isin(sj_dealer, weak), tat * 1.9, tat)
rev_base = {"Periodic Service": 6500, "Repair": 14000, "Warranty": 0, "Accident Repair": 38000, "Wash & Detail": 1200}
sj_rev = np.array([rev_base[j] for j in job_type]) * rng.normal(1, 0.2, N_JOBS)
service = pd.DataFrame({"job_id": [f"J{i:06d}" for i in range(1, N_JOBS + 1)], "dealer_id": sj_dealer,
                        "job_type": job_type, "revenue": np.clip(sj_rev, 0, None).round(0),
                        "tat_days": tat.round(1), "job_date": START + pd.to_timedelta(rng.integers(0, DAYS, N_JOBS), unit="D")})

# ---------------------------------------------------------------- inventory (monthly snapshots)
snap = pd.date_range(START, END, freq="MS")
inv = []
for d in dealer_ids:
    for m in snap:
        for p in pnames[:4]:
            stock = int(max(0, rng.normal(14 if d not in weak else 24, 5)))
            inv.append((d, p, stock, m, int(np.clip(rng.normal(85 if d in weak else 42, 25), 5, 200)) if stock else 0))
inventory = pd.DataFrame(inv, columns=["dealer_id", "product", "stock_qty", "snapshot_date", "avg_age_days"])

# ---------------------------------------------------------------- campaigns
# channel: (lead->sale rate, cost per lead INR)
chs = {"Paid Social": (0.008, 250), "Google Search": (0.03, 400), "Email": (0.05, 120),
       "Influencer": (0.012, 500), "WhatsApp": (0.045, 150), "Offline/Events": (0.035, 700)}
camp = []
cid = 1
for ch, (conv, cpl) in chs.items():
    for q in pd.period_range("2024Q1", "2025Q4", freq="Q"):
        for k in range(3):
            leads = int(rng.integers(8000, 25000) * (1.8 if ch == "Paid Social" else 1))
            spend = leads * cpl * rng.normal(1, 0.1)
            convs = max(int(leads * conv * rng.normal(1, 0.15)), 1)
            camp.append((f"C{cid:03d}", f"{ch} {q} #{k+1}", ch, str(q), round(spend, 0), leads, convs,
                         round(convs * rng.normal(70_000, 15_000), 0)))  # gross profit per sale ~INR 70k
            cid += 1
campaigns = pd.DataFrame(camp, columns=["campaign_id", "campaign_name", "channel", "quarter", "spend", "leads", "conversions", "gross_profit_attributed"])

# ---------------------------------------------------------------- web / chatbot / app sessions
N_WEB = 60_000
src = rng.choice(list(chs), N_WEB, p=[.30, .25, .10, .08, .12, .15])
src = np.where(rng.random(N_WEB) < 0.15, "Organic", src)
device = rng.choice(["Mobile", "Desktop", "Tablet"], N_WEB, p=[.65, .30, .05])
platform = rng.choice(["Website", "Chatbot", "Connected App"], N_WEB, p=[.6, .25, .15])
conv_p = {"Paid Social": .012, "Google Search": .06, "Email": .09, "Influencer": .03, "WhatsApp": .08,
          "Offline/Events": .05, "Organic": .05}
p = np.array([conv_p[s] for s in src])
p = np.where(device == "Mobile", p * 0.85, p * 1.25)
p = np.where(platform == "Chatbot", p * 0.9, p)
escalated = (platform == "Chatbot") & (rng.random(N_WEB) < 0.3)
p = np.where(escalated, p * 0.4, p)
converted = (rng.random(N_WEB) < p).astype(int)
aov = np.where(converted == 1, rng.lognormal(np.log(52_000), 0.5, N_WEB), np.nan)
web = pd.DataFrame({"session_id": [f"W{i:07d}" for i in range(1, N_WEB + 1)],
                    "session_date": START + pd.to_timedelta(rng.integers(0, DAYS, N_WEB), unit="D"),
                    "platform": platform, "source": src, "device": device,
                    "page_views": rng.poisson(5, N_WEB) + 1, "chatbot_escalated": escalated.astype(int),
                    "converted": converted, "order_value": np.round(aov, 0)})

# ---------------------------------------------------------------- feedback (NPS)
N_FB = 12_000
fb_dealer = rng.choice(dealer_ids, N_FB)
base = np.where(np.isin(fb_dealer, weak), 5.4, 8.1)
score = np.clip(np.round(rng.normal(base, 2.0)), 0, 10).astype(int)
pos = ["Great service and friendly staff", "Smooth delivery experience", "Fair pricing, would recommend",
       "Quick turnaround and clean work", "Very helpful sales executive", "App makes booking easy"]
neg = ["Service took too many days", "Delivery was delayed again", "Staff behaviour was rude",
       "Hidden charges in the final price", "App keeps crashing while booking", "Billing was wrong, still unresolved",
       "No update on my vehicle status", "Long waiting time at the showroom"]
neu = ["Average experience overall", "Okay service, nothing special", "Product fine, process slow"]
comment = [rng.choice(pos) if s >= 9 else rng.choice(neg) if s <= 6 else rng.choice(neu) for s in score]
fb = pd.DataFrame({"feedback_id": [f"F{i:06d}" for i in range(1, N_FB + 1)], "customer_id": [f"CU{rng.integers(1, 9000):05d}" for _ in range(N_FB)],
                   "dealer_id": fb_dealer, "nps_score": score, "comment": comment,
                   "feedback_date": START + pd.to_timedelta(rng.integers(0, DAYS, N_FB), unit="D")})

# ---------------------------------------------------------------- call logs
N_CALL = 25_000
agents = [f"A{i:03d}" for i in range(1, 41)]
a_skill = {a: rng.normal(0, 1) for a in agents}
issue = rng.choice(["Billing Dispute", "Delivery Delay", "Service Complaint", "Product Query", "App/Technical", "Booking/Appointment"],
                   N_CALL, p=[.20, .18, .17, .15, .15, .15])
agent = rng.choice(agents, N_CALL)
dur = rng.gamma(4, 1.8, N_CALL) * np.where(issue == "Billing Dispute", 1.6, 1.0)
resolved_p = np.array([{"Billing Dispute": .52, "Delivery Delay": .62, "Service Complaint": .66, "Product Query": .9, "App/Technical": .72, "Booking/Appointment": .93}[i] for i in issue])
resolved_p = resolved_p + np.array([a_skill[a] for a in agent]) * 0.06
resolved = (rng.random(N_CALL) < np.clip(resolved_p, .05, .98)).astype(int)
sent_score = np.where(issue == "Billing Dispute", -0.45, np.where(issue == "Delivery Delay", -0.2, 0.15)) \
             + np.where(resolved == 1, 0.35, -0.3) + np.array([a_skill[a] for a in agent]) * 0.1 + rng.normal(0, 0.25, N_CALL)
sentiment = np.where(sent_score > 0.15, "Positive", np.where(sent_score < -0.15, "Negative", "Neutral"))
calls = pd.DataFrame({"call_id": [f"CL{i:06d}" for i in range(1, N_CALL + 1)], "agent_id": agent, "issue_type": issue,
                      "call_date": START + pd.to_timedelta(rng.integers(0, DAYS, N_CALL), unit="D"),
                      "duration_min": dur.round(1), "resolved": resolved, "sentiment": sentiment,
                      "csat": np.clip(np.round(3 + sent_score * 2.2 + rng.normal(0, .5, N_CALL)), 1, 5).astype(int)})

# ---------------------------------------------------------------- inject dirt (cleaning is genuine)
def dirty(df, null_cols, dup_frac=0.005, null_frac=0.01):
    df = df.copy()
    for c in null_cols:
        idx = rng.choice(df.index, int(len(df) * null_frac), replace=False)
        df.loc[idx, c] = np.nan
    dups = df.sample(frac=dup_frac, random_state=1)
    return pd.concat([df, dups], ignore_index=True)

sales = dirty(sales, ["payment_mode"])
sales.loc[rng.choice(sales.index, 15, replace=False), "amount"] *= 50          # outliers
service = dirty(service, ["tat_days"])
web = dirty(web, ["device"], dup_frac=0.003)
fb = dirty(fb, ["comment"])
calls = dirty(calls, ["sentiment"], dup_frac=0.004)
calls["issue_type"] = calls["issue_type"].where(rng.random(len(calls)) > 0.01, calls["issue_type"].str.lower())  # case typos
for df, col in [(sales, "sale_date"), (service, "job_date"), (web, "session_date"), (fb, "feedback_date"), (calls, "call_date")]:
    df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
inventory["snapshot_date"] = inventory["snapshot_date"].dt.strftime("%Y-%m-%d")

tables = dict(dealers=dealers, sales=sales, service_jobs=service, inventory=inventory, campaigns=campaigns,
              web_sessions=web, feedback=fb, call_logs=calls)
for n, df in tables.items():
    df.to_csv(OUT / f"{n}.csv", index=False)
    print(f"{n:14s} {len(df):>7,} rows")
