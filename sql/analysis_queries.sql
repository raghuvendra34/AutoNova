-- =====================================================================
-- Omnichannel Analytics: 20 SQL queries (SQLite dialect; works in MySQL 8 / PostgreSQL with minor changes)
-- Each query starts with a "-- Q<n>:" title line used by the runner script.
-- =====================================================================

-- Q1: Overall KPI snapshot
SELECT (SELECT ROUND(SUM(amount)/1e7,2) FROM sales)                          AS sales_crore,
       (SELECT COUNT(*) FROM sales)                                           AS vehicles_and_accessory_orders,
       (SELECT ROUND(100.0*SUM(converted)/COUNT(*),2) FROM web_sessions)      AS web_conversion_pct,
       (SELECT ROUND(AVG(order_value),0) FROM web_sessions WHERE converted=1) AS aov,
       (SELECT ROUND(100.0*(SUM(nps_score>=9)-SUM(nps_score<=6))/COUNT(*),1) FROM feedback) AS nps,
       (SELECT ROUND(100.0*AVG(resolved),1) FROM call_logs)                   AS call_resolution_pct;

-- Q2: Monthly sales trend with month-over-month growth (window: LAG)
WITH m AS (SELECT year_month, SUM(amount) AS sales FROM sales GROUP BY year_month)
SELECT year_month, ROUND(sales/1e6,1) AS sales_mn,
       ROUND(100.0*(sales - LAG(sales) OVER (ORDER BY year_month)) / LAG(sales) OVER (ORDER BY year_month),1) AS mom_pct
FROM m ORDER BY year_month;

-- Q3: Dealer sales rank within each region (window: RANK)
SELECT d.region, d.dealer_name, ROUND(SUM(s.amount)/1e6,1) AS sales_mn,
       RANK() OVER (PARTITION BY d.region ORDER BY SUM(s.amount) DESC) AS region_rank
FROM sales s JOIN dealers d USING (dealer_id)
GROUP BY d.region, d.dealer_name ORDER BY d.region, region_rank;

-- Q4: Dealer sales vs target (achievement %)  - target is monthly, so x24 months
SELECT d.dealer_name, d.region,
       ROUND(SUM(s.amount)/1e6,1)                         AS actual_mn,
       ROUND(d.monthly_target*24/1e6,1)                   AS target_mn,
       ROUND(100.0*SUM(s.amount)/(d.monthly_target*24),1) AS achievement_pct
FROM sales s JOIN dealers d USING (dealer_id)
GROUP BY d.dealer_id ORDER BY achievement_pct DESC;

-- Q5: Product mix share of revenue (window: SUM OVER)
SELECT product, COUNT(*) AS orders, ROUND(SUM(amount)/1e6,1) AS revenue_mn,
       ROUND(100.0*SUM(amount)/SUM(SUM(amount)) OVER (),1) AS revenue_share_pct
FROM sales GROUP BY product ORDER BY revenue_mn DESC;

-- Q6: Festive-quarter (Oct-Dec) lift vs rest of year
SELECT is_festive_q, COUNT(*) AS orders, ROUND(SUM(amount)/1e6,1) AS revenue_mn,
       ROUND(SUM(amount)/COUNT(DISTINCT year_month)/1e6,1) AS avg_monthly_revenue_mn
FROM sales GROUP BY is_festive_q;

-- Q7: Service TAT by dealer, flag dealers above network average (CTE + subquery)
WITH t AS (SELECT dealer_id, ROUND(AVG(tat_days),2) AS avg_tat, ROUND(100.0*AVG(tat_flag='Delayed'),1) AS delayed_pct,
                  ROUND(SUM(revenue)/1e6,2) AS service_rev_mn
           FROM service_jobs GROUP BY dealer_id)
SELECT d.dealer_name, d.region, t.avg_tat, t.delayed_pct, t.service_rev_mn,
       CASE WHEN t.avg_tat > (SELECT AVG(avg_tat) FROM t)*1.25 THEN 'RED FLAG' ELSE 'OK' END AS status
FROM t JOIN dealers d USING (dealer_id) ORDER BY t.avg_tat DESC;

-- Q8: Service revenue and TAT by job type
SELECT job_type, COUNT(*) AS jobs, ROUND(AVG(revenue),0) AS avg_revenue, ROUND(AVG(tat_days),2) AS avg_tat_days
FROM service_jobs GROUP BY job_type ORDER BY jobs DESC;

-- Q9: Inventory aging - stock sitting 90+ days (latest snapshot only)
SELECT d.dealer_name, d.region, SUM(i.stock_qty) AS units_in_stock,
       SUM(CASE WHEN i.aging_bucket='90+' THEN i.stock_qty ELSE 0 END) AS units_90plus_days,
       ROUND(100.0*SUM(CASE WHEN i.aging_bucket='90+' THEN i.stock_qty ELSE 0 END)/SUM(i.stock_qty),1) AS aged_pct
FROM inventory i JOIN dealers d USING (dealer_id)
WHERE i.snapshot_date = (SELECT MAX(snapshot_date) FROM inventory)
GROUP BY d.dealer_id ORDER BY aged_pct DESC LIMIT 10;

-- Q10: Stock-to-sales ratio per dealer (months of cover, last 12 months)
WITH st AS (SELECT dealer_id, SUM(stock_qty) AS stock FROM inventory
            WHERE snapshot_date=(SELECT MAX(snapshot_date) FROM inventory) AND product<>'Accessories Pack' GROUP BY dealer_id),
     sl AS (SELECT dealer_id, COUNT(*)/12.0 AS monthly_units FROM sales
            WHERE sale_date>='2025-01-01' AND product<>'Accessories Pack' GROUP BY dealer_id)
SELECT d.dealer_name, st.stock, ROUND(sl.monthly_units,1) AS avg_monthly_units_sold,
       ROUND(st.stock/sl.monthly_units,2) AS months_of_cover
FROM st JOIN sl USING (dealer_id) JOIN dealers d USING (dealer_id) ORDER BY months_of_cover DESC LIMIT 10;

-- Q11: Conversion rate and AOV by traffic source
SELECT source, COUNT(*) AS sessions, SUM(converted) AS orders,
       ROUND(100.0*SUM(converted)/COUNT(*),2) AS conversion_pct,
       ROUND(AVG(CASE WHEN converted=1 THEN order_value END),0) AS aov
FROM web_sessions GROUP BY source ORDER BY sessions DESC;

-- Q12: Conversion by platform x device (website / chatbot / connected app)
SELECT platform, device, COUNT(*) AS sessions, ROUND(100.0*AVG(converted),2) AS conversion_pct
FROM web_sessions WHERE device<>'Unknown' GROUP BY platform, device ORDER BY platform, conversion_pct DESC;

-- Q13: Chatbot performance: escalated vs resolved-in-bot sessions
SELECT CASE chatbot_escalated WHEN 1 THEN 'Escalated to human' ELSE 'Handled by bot' END AS outcome,
       COUNT(*) AS sessions, ROUND(100.0*AVG(converted),2) AS conversion_pct, ROUND(AVG(page_views),1) AS avg_page_views
FROM web_sessions WHERE platform='Chatbot' GROUP BY chatbot_escalated;

-- Q14: Campaign ROI and cost per lead by channel
SELECT channel, ROUND(SUM(spend)/1e6,2) AS spend_mn, SUM(leads) AS leads, SUM(conversions) AS conversions,
       ROUND(SUM(spend)/SUM(leads),0) AS cost_per_lead, ROUND(SUM(spend)/SUM(conversions),0) AS cost_per_conversion,
       ROUND(100.0*SUM(conversions)/SUM(leads),2) AS lead_to_conv_pct,
       ROUND((SUM(gross_profit_attributed)-SUM(spend))/SUM(spend),1) AS roi_x
FROM campaigns GROUP BY channel ORDER BY cost_per_conversion;

-- Q15: Quarterly best vs worst campaign per channel (ROW_NUMBER)
WITH r AS (SELECT campaign_name, channel, roi_x,
                  ROW_NUMBER() OVER (PARTITION BY channel ORDER BY roi_x DESC) AS rn_best,
                  ROW_NUMBER() OVER (PARTITION BY channel ORDER BY roi_x ASC)  AS rn_worst
           FROM campaigns)
SELECT channel, campaign_name, roi_x, CASE WHEN rn_best=1 THEN 'Best' ELSE 'Worst' END AS label
FROM r WHERE rn_best=1 OR rn_worst=1 ORDER BY channel, label;

-- Q16: NPS by dealer with promoter/detractor split
SELECT d.dealer_name, d.region, COUNT(*) AS responses,
       ROUND(100.0*SUM(f.nps_category='Promoter')/COUNT(*),1) AS promoter_pct,
       ROUND(100.0*SUM(f.nps_category='Detractor')/COUNT(*),1) AS detractor_pct,
       ROUND(100.0*(SUM(f.nps_category='Promoter')-SUM(f.nps_category='Detractor'))/COUNT(*),1) AS nps
FROM feedback f JOIN dealers d USING (dealer_id)
GROUP BY d.dealer_id ORDER BY nps;

-- Q17: Do slow-service dealers have lower NPS? (join of two CTEs)
WITH t AS (SELECT dealer_id, AVG(tat_days) AS avg_tat FROM service_jobs GROUP BY dealer_id),
     n AS (SELECT dealer_id, 100.0*(SUM(nps_score>=9)-SUM(nps_score<=6))/COUNT(*) AS nps FROM feedback GROUP BY dealer_id)
SELECT CASE WHEN t.avg_tat > (SELECT AVG(avg_tat)*1.25 FROM t) THEN 'High TAT dealers' ELSE 'Other dealers' END AS dealer_group,
       COUNT(*) AS dealers, ROUND(AVG(t.avg_tat),2) AS avg_tat_days, ROUND(AVG(n.nps),1) AS avg_nps
FROM t JOIN n USING (dealer_id) GROUP BY dealer_group;

-- Q18: Detractor themes from feedback comments
SELECT theme, COUNT(*) AS detractor_comments,
       ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),1) AS share_pct
FROM feedback WHERE nps_category='Detractor' GROUP BY theme ORDER BY detractor_comments DESC;

-- Q19: Call centre - issue type: volume, handle time, resolution, negative sentiment
SELECT issue_type, COUNT(*) AS calls, ROUND(AVG(duration_min),1) AS avg_handle_min,
       ROUND(100.0*AVG(resolved),1) AS resolution_pct,
       ROUND(100.0*AVG(sentiment='Negative'),1) AS negative_pct,
       ROUND(100.0*SUM(sentiment='Negative')/SUM(SUM(sentiment='Negative')) OVER (),1) AS share_of_all_negative_pct
FROM call_logs GROUP BY issue_type ORDER BY negative_pct DESC;

-- Q20: Agent scorecard with quartile ranking (NTILE) - bottom-quartile agents flagged
WITH a AS (SELECT agent_id, COUNT(*) AS calls, ROUND(AVG(duration_min),1) AS aht_min,
                  ROUND(100.0*AVG(resolved),1) AS resolution_pct, ROUND(AVG(csat),2) AS csat,
                  ROUND(100.0*AVG(sentiment='Negative'),1) AS negative_pct
           FROM call_logs GROUP BY agent_id)
SELECT agent_id, calls, aht_min, resolution_pct, csat, negative_pct,
       NTILE(4) OVER (ORDER BY csat DESC) AS csat_quartile,
       CASE WHEN NTILE(4) OVER (ORDER BY csat DESC)=4 THEN 'Coaching needed' ELSE '' END AS action
FROM a ORDER BY csat LIMIT 10;
