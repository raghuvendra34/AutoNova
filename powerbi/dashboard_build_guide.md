# Power BI dashboard build guide (5 pages)

Theme: white background, blue (#2563eb) primary, red (#dc2626) for "bad", grey for context. Add a navigation bar of page buttons.
Global slicers (sync across pages): **Year, Quarter, Region** (from dealers).

## Page 1 - Executive Summary
- KPI cards: Total Sales, Target Achievement %, Conversion %, AOV, NPS, Resolution %
- Line chart: Total Sales by dim_date[year_month] + Sales LY (dashed)
- Clustered bar: Target Achievement % by Region
- Donut: Revenue Share % by product
- Smart narrative / text box: 3 headline insights
- Conditional format NPS card using [NPS Colour]

## Page 2 - Digital Performance (Website, Chatbot, Connected App)
- Funnel: Sessions -> Orders (Web)
- Bar: Conversion % by source (highlight Paid Social red) with Sessions as tooltip
- Matrix: platform x device -> Conversion %
- Card pair: Chatbot Escalation %, conversion of escalated vs bot-handled (use a calculated column or two measures)
- Line: Conversion % by month; slicer: platform

## Page 3 - Dealer Performance
- Table (conditional-format data bars): Dealer, Total Sales, Target Achievement %, Avg TAT, Delayed Jobs %, NPS, Aged Stock %
- Scatter: X = Avg TAT, Y = NPS, size = Total Sales, legend = Region (shows the East cluster)
- Stacked column: Inventory units by aging_bucket per dealer (latest snapshot)
- Matrix: job_type x Avg TAT
- Drill-through page: Dealer detail (right-click a dealer -> Dealer 360)

## Page 4 - Marketing & NPS
- Bar: Campaign ROI (x) by channel; Table: Cost per Lead, Cost per Conversion
- Scatter: Spend vs Conversions per campaign (look for outliers)
- Line: NPS by month; 100% stacked column: Promoter / Passive / Detractor by month
- Bar: Detractor comments by theme (feedback[theme])
- Decomposition tree: NPS -> Region -> Dealer -> Theme

## Page 5 - Call Center & Voice of Customer
- Cards: Calls, Resolution %, Avg Handle Time, Avg CSAT, Negative Calls %
- Stacked bar: sentiment split by issue_type; bar: Share of All Negative Calls
- Agent scorecard table: Calls, AHT, Resolution %, CSAT, Negative % with red/green conditional formatting
- Line: Negative Calls % by month
- Key influencers visual: what drives `sentiment = Negative` (try issue_type, resolved, aht_bucket)

## Publish checklist
1. Check each page renders on a laptop-size canvas (16:9). 2. Add alt-text. 3. Export PDF + screenshots to /charts.
4. Publish to Power BI Service (free work/school account) or record a 2-3 min Loom walkthrough if you only have Desktop.
