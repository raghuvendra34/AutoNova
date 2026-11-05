"""04_insights_and_charts.py - computes headline insights and saves 6 charts to /charts (also usable as Power BI mock-ups)."""
import sqlite3
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "charts"; CH.mkdir(exist_ok=True)
con = sqlite3.connect(ROOT / "data" / "omnichannel.db")
q = lambda s: pd.read_sql(s, con)
plt.rcParams.update({"figure.figsize": (9, 4.8), "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
BLUE, RED, GREY = "#2563eb", "#dc2626", "#9ca3af"

# 1 monthly sales
d = q("SELECT year_month, SUM(amount)/1e6 AS s FROM sales GROUP BY 1 ORDER BY 1")
plt.plot(d.year_month, d.s, marker="o", color=BLUE); plt.xticks(rotation=90, fontsize=7)
plt.title("Monthly sales (INR mn) - festive spike every Oct-Dec"); plt.ylabel("INR mn"); plt.tight_layout(); plt.savefig(CH / "1_monthly_sales.png", dpi=130); plt.clf()

# 2 conversion by source
d = q("SELECT source, 100.0*AVG(converted) c, COUNT(*) n FROM web_sessions GROUP BY 1 ORDER BY c")
plt.barh(d.source, d.c, color=[RED if s == "Paid Social" else BLUE for s in d.source])
for i, (c, n) in enumerate(zip(d.c, d.n)): plt.text(c + .1, i, f"{c:.1f}%  ({n:,} sessions)", va="center", fontsize=8)
plt.title("Conversion % by traffic source (Paid Social: most traffic, worst conversion)"); plt.xlim(0, 11); plt.tight_layout(); plt.savefig(CH / "2_conversion_by_source.png", dpi=130); plt.clf()

# 3 TAT vs NPS scatter by dealer
d = q("""SELECT d.dealer_name, d.region, AVG(j.tat_days) tat,
         (SELECT 100.0*(SUM(nps_score>=9)-SUM(nps_score<=6))/COUNT(*) FROM feedback f WHERE f.dealer_id=d.dealer_id) nps
         FROM service_jobs j JOIN dealers d USING(dealer_id) GROUP BY d.dealer_id""")
plt.scatter(d.tat, d.nps, c=[RED if t > 4 else BLUE for t in d.tat], s=60)
for _, r in d[d.tat > 4].iterrows(): plt.annotate(r.dealer_name, (r.tat, r.nps), fontsize=7, xytext=(5, 4), textcoords="offset points")
plt.xlabel("Avg service TAT (days)"); plt.ylabel("NPS"); plt.title("Slow service dealers have deeply negative NPS"); plt.tight_layout(); plt.savefig(CH / "3_tat_vs_nps.png", dpi=130); plt.clf()

# 4 campaign cost per conversion vs ROI
d = q("SELECT channel, SUM(spend)/SUM(conversions) cpc, (SUM(gross_profit_attributed)-SUM(spend))/SUM(spend) roi FROM campaigns GROUP BY 1 ORDER BY roi")
plt.barh(d.channel, d.roi, color=[RED if r < 1.5 else BLUE for r in d.roi])
for i, r in enumerate(d.roi): plt.text(r + .3, i, f"{r:.1f}x", va="center")
plt.title("Campaign ROI by channel (gross profit / spend)"); plt.tight_layout(); plt.savefig(CH / "4_campaign_roi.png", dpi=130); plt.clf()

# 5 negative call share by issue
d = q("SELECT issue_type, 100.0*SUM(sentiment='Negative')/(SELECT SUM(sentiment='Negative') FROM call_logs) p FROM call_logs GROUP BY 1 ORDER BY p")
plt.barh(d.issue_type, d.p, color=[RED if i == "Billing Dispute" else GREY for i in d.issue_type])
plt.title("Share of all negative-sentiment calls by issue type (%)"); plt.tight_layout(); plt.savefig(CH / "5_negative_calls_by_issue.png", dpi=130); plt.clf()

# 6 detractor themes
d = q("SELECT theme, COUNT(*) n FROM feedback WHERE nps_category='Detractor' GROUP BY 1 ORDER BY n")
plt.barh(d.theme, d.n, color=BLUE); plt.title("What detractors complain about"); plt.tight_layout(); plt.savefig(CH / "6_detractor_themes.png", dpi=130); plt.clf()

# ---------------- headline numbers for the write-up
print("--- HEADLINES ---")
print(q("""SELECT ROUND(SUM(amount)/1e7,0) sales_cr FROM sales""").to_string(index=False))
print(q("""SELECT ROUND(100.0*AVG(converted),2) conv, ROUND(AVG(CASE WHEN converted=1 THEN order_value END)) aov FROM web_sessions""").to_string(index=False))
print(q("""SELECT ROUND(100.0*(SUM(nps_score>=9)-SUM(nps_score<=6))/COUNT(*),1) nps FROM feedback""").to_string(index=False))
print(q("""SELECT ROUND(100.0*SUM(CASE WHEN d.region='East' THEN 1 ELSE 0 END)/COUNT(*),1) pct_fb_east FROM feedback f JOIN dealers d USING(dealer_id)""").to_string(index=False))
print("Paid social share of sessions:", q("SELECT ROUND(100.0*AVG(source='Paid Social'),1) p FROM web_sessions").p[0])
print("Paid social share of spend:", q("SELECT ROUND(100.0*SUM(CASE WHEN channel='Paid Social' THEN spend END)/SUM(spend),1) p FROM campaigns").p[0])
print("Dealers below 100% target:", q("""SELECT COUNT(*) n FROM (SELECT SUM(s.amount)/(d.monthly_target*24.0) a FROM sales s JOIN dealers d USING(dealer_id) GROUP BY d.dealer_id) WHERE a<1""").n[0])
print("East weak dealers ach:", q("""SELECT d.dealer_name, ROUND(100.0*SUM(s.amount)/(d.monthly_target*24),0) a FROM sales s JOIN dealers d USING(dealer_id) WHERE d.dealer_name IN ('Kolkata Motors 1','Kolkata Motors 2','Patna Motors 1','Patna Motors 2') GROUP BY d.dealer_id""").to_string(index=False))
print("Mobile vs desktop conv:", q("SELECT device, ROUND(100.0*AVG(converted),2) c FROM web_sessions GROUP BY 1").to_string(index=False))
print("Reallocation sim: ", end="")
e = q("SELECT channel, SUM(spend) sp, SUM(conversions) cv FROM campaigns GROUP BY 1").set_index("channel")
cpc = e.sp / e.cv; move = 0.15 * e.loc["Paid Social", "sp"]
gain = move / cpc["Email"] - move / cpc["Paid Social"]
print(f"moving 15% of Paid Social budget (INR {move/1e6:.1f}mn) to Email at current CPA => +{gain:,.0f} extra conversions (assumes constant CPA, i.e. upper bound)")
print("Detractors from billing+service delay %:", q("SELECT ROUND(100.0*SUM(theme IN ('Pricing / Billing','Service Delay'))/COUNT(*),1) p FROM feedback WHERE nps_category='Detractor'").p[0])
print("Bottom quartile agents CSAT/Top:", q("""WITH a AS (SELECT agent_id, AVG(csat) c, AVG(resolved) r FROM call_logs GROUP BY 1) SELECT ROUND(MIN(c),2) lo, ROUND(MAX(c),2) hi, ROUND(100*MIN(r),1) rlo, ROUND(100*MAX(r),1) rhi FROM a""").to_string(index=False))
print("Festive lift:", q("SELECT ROUND(AVG(CASE WHEN is_festive_q=1 THEN m END)/AVG(CASE WHEN is_festive_q=0 THEN m END),2) x FROM (SELECT is_festive_q, year_month, SUM(amount) m FROM sales GROUP BY 1,2)").x[0])
