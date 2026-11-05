# Data dictionary (all data is SYNTHETIC; 2024-01-01 to 2025-12-31)

| Table | Rows (clean) | Grain | Key columns |
|---|---|---|---|
| dealers | 28 | 1 per dealer | dealer_id, dealer_name, city, region, manager, monthly_target (INR) |
| sales | 18,000 | 1 per order | sale_id, dealer_id, product, amount (INR), sale_date, payment_mode, year_month, is_festive_q |
| service_jobs | 20,000 | 1 per job card | job_id, dealer_id, job_type, revenue, tat_days, job_date, tat_flag |
| inventory | 2,688 | dealer x product x month-end snapshot | stock_qty, avg_age_days, aging_bucket |
| campaigns | 144 | 1 per campaign | channel, quarter, spend, leads, conversions, gross_profit_attributed, cost_per_lead, roi_x |
| web_sessions | 60,000 | 1 per session | platform (Website / Chatbot / Connected App), source, device, page_views, chatbot_escalated, converted, order_value |
| feedback | 12,000 | 1 per survey response | nps_score (0-10), nps_category, comment, theme, comment_sentiment |
| call_logs | 25,000 | 1 per call | agent_id (40 agents), issue_type, duration_min, resolved, sentiment, csat (1-5) |
| dim_date | 731 | 1 per day | year, quarter, month_name, year_month, day_name |

## NPS definition
Promoter 9-10, Passive 7-8, Detractor 0-6. NPS = %Promoters - %Detractors (range -100 to +100).

## Data-quality issues injected and fixed (see data_quality_log.csv)
Duplicate IDs (sales, jobs, sessions, feedback, calls), null payment_mode / TAT / device / comment / sentiment,
15 sales amounts entered ~50x too high, and inconsistent text case in call issue_type.
