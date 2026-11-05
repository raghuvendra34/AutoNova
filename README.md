# Omnichannel Sales, Customer Experience & Call Center Analytics

**Tools:** SQL (SQLite, portable to MySQL/PostgreSQL) | Python (Pandas, NumPy, Matplotlib) | Power BI (DAX, star schema)

An end-to-end analytics project for a fictional automotive and service brand ("AutoNova") with 28 dealers in 4 regions,
a website, a chatbot, a connected app, marketing campaigns and a call centre. It answers four business questions:

1. Which dealers and regions are underperforming on sales, service and inventory?
2. Which channels and campaigns really convert, and at what cost?
3. Why is NPS low and what are detractors complaining about?
4. Which call types and agents hurt customer sentiment?

> **Honesty note:** the data is synthetic. Patterns were deliberately planted in the generator
> (`01_generate_data.py`) so the analysis has something to detect. The findings show the *method* and the kind of
> insight an analyst would produce; they are not real business results. Say this in interviews; it builds credibility.

## Project structure
```
python/   01_generate_data.py  02_clean_and_enrich.py  03_run_sql.py  04_insights_and_charts.py
sql/      analysis_queries.sql        (20 queries: joins, CTEs, window functions)
data/     raw/  clean/  omnichannel.db
powerbi/  dax_measures.dax  data_model.md  dashboard_build_guide.md
charts/   6 PNG charts            docs/  data_dictionary.md  data_quality_log.csv  sql_results/
run_all.sh                         (runs the whole pipeline in ~1 minute)
```

## How to run
```bash
pip install -r requirements.txt
./run_all.sh            # generate -> clean -> SQL -> charts
```
Then follow `powerbi/data_model.md` and `powerbi/dashboard_build_guide.md` to build the 5-page dashboard from `data/clean/*.csv`.

## Method
| Step | What was done |
|---|---|
| 1. Data | 8 tables, ~138k rows. Seeded generator with realistic seasonality, dirty records and planted patterns. |
| 2. Cleaning (Pandas/NumPy) | Removed 530 duplicate rows, filled 1,350 nulls with documented rules, fixed 15 outliers (>3x product median), standardised text. Every fix is logged. |
| 3. Feature engineering | Year-month, day-of-week, festive flag, AOV / aging / handle-time buckets, NPS category, TAT delay flag, campaign CPL / ROI, date dimension. |
| 4. Text analytics | Rule-based keyword tagging of feedback into 6 themes and positive/negative polarity. |
| 5. SQL | 20 queries: `LAG`, `RANK`, `ROW_NUMBER`, `NTILE`, window `SUM() OVER`, CTEs, conditional aggregation. |
| 6. Power BI | Star schema, 50+ DAX measures, 5 pages, drill-through, conditional formatting, key-influencers visual. |

## Key findings (from the SQL results in `docs/sql_results/`)
**Overall:** INR 1,500 crore sales over 24 months, web conversion 4.37%, AOV INR 58.4k, NPS +7.8, call resolution ~70%.

1. **Four East-region dealers drive the NPS problem.** Kolkata 1 & 2 and Patna 1 & 2 average **4.97 days** service TAT vs 2.62 elsewhere
   (about 50% of their jobs run late vs 1-3% elsewhere). Their NPS is **-64** vs **+20** for the other 24 dealers. They also reach only 55-72% of sales target,
   hold 5.6-6.7 months of stock cover (network norm ~3), and have the highest aged stock. *Action: service-capacity audit and a TAT recovery plan before touching sales incentives.*
2. **Paid Social is the biggest traffic source but the weakest converter.** It brings 25.5% of sessions at **1.0% conversion** (network 4.37%; Email 8.0%, WhatsApp 7.0%)
   and returns only **1.1x** ROI vs 4.0x for Google Search and 31x for Email. *Action: cut or retarget Paid Social creative and shift budget toward Google Search / WhatsApp, testing gradually since owned channels saturate.*
3. **Mobile underconverts.** Mobile converts 3.8% vs 5.5% on desktop even though mobile is 65% of traffic. *Action: audit the mobile checkout and booking flow.*
4. **Chatbot escalations lose sales.** Escalated sessions convert at **1.6%** vs **4.4%** for bot-handled ones. *Action: improve bot intents for the top escalation reasons and add a warm hand-off.*
5. **Billing is the #1 sentiment killer.** Billing disputes are 20% of call volume but **48% of all negative calls** (68% of billing calls end negative, only 51% resolved, 11.5 min handle time).
   Billing/pricing is also the top detractor theme in surveys (26%). Together with service delay it explains **~50% of detractor comments**. *Action: fix invoice clarity and create a billing specialist queue.*
6. **Agent variance is large.** Agent CSAT ranges 2.5 to 3.9 and resolution 53% to 82%; the bottom-quartile agents (Q20) should get coaching on billing calls.
7. **Seasonality.** Oct-Dec months run **2.3x** the average of other months; plan inventory, staffing and campaign budget accordingly.

## Resume bullets
- Built an end-to-end analytics project (SQL, Python, Power BI) on 138k records covering dealer sales, service, inventory, digital funnels, marketing, NPS and call-centre VoC.
- Wrote 20 SQL queries using joins, CTEs and window functions (LAG, RANK, NTILE) to analyse sales vs target, conversion, AOV, campaign ROI and NPS.
- Cleaned and transformed data with Pandas/NumPy (deduplication, null handling, outlier correction, feature engineering) with a documented data-quality log.
- Tagged customer feedback into 6 themes via rule-based text analytics, showing that billing and service delay account for ~50% of detractor comments.
- Designed a 5-page Power BI dashboard (star schema, 50+ DAX measures, drill-through, key-influencers) that isolates underperforming dealers, low-converting channels and negative call drivers.

## Interview prep: questions this project lets you answer
- *How do you calculate NPS in SQL and DAX?* (Q16, `NPS` measure)
- *Difference between RANK, DENSE_RANK and ROW_NUMBER?* (Q3, Q15)
- *Why a star schema?* (`data_model.md`)  *Calculated column vs measure?*
- *How did you handle outliers and nulls, and why that method?* (`data_quality_log.csv`)
- *What are the limits of your analysis?* Synthetic data; keyword sentiment is crude; correlation is not causation; the reallocation advice assumes channel CPA holds as budget shifts.

## Possible extensions
RFM customer segmentation; churn or lead-scoring model; replace keyword tagging with a VADER/transformer sentiment model;
add a Python-driven monthly report; a small SOC-style log-analysis add-on if you also target the SOC Analyst role.
