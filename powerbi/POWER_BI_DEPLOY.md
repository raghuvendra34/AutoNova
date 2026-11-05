# Power BI dashboard — build & publish guide (Mac route)

Power BI Desktop does not run on macOS, so this project is deployed through
**Power BI Service in the browser** (app.powerbi.com). Everything it needs is
already in this folder:

| File | What it is |
|---|---|
| `PowerBI_AutoNova_Data.xlsx` | All 9 model tables as formatted Excel tables + 2 pre-joined flat sheets + a README sheet with the relationship list |
| `data_model.md` | Star-schema diagram and the 9 relationships to create |
| `dax_measures.dax` | 50+ measures (KPI, NPS, ROI, call-centre) for a `_Measures` table |
| `dashboard_build_guide.md` | The 5 report pages, visual by visual |

Regenerate the workbook any time with:

```bash
cd ~/Downloads/omnichannel-analytics/python
python3 build_powerbi_workbook.py
```

(If it complains about openpyxl: `python3 -m pip install openpyxl` once.)

## Publish steps

1. Open **app.powerbi.com** in Brave and sign in with a **work or school
   Microsoft account** (for example a VIT student account, if it includes
   Microsoft 365). A personal Gmail/Outlook account cannot register for
   Power BI — this sign-in is the one step only you can do.
2. **My workspace → New item → Upload a file →** select
   `powerbi/PowerBI_AutoNova_Data.xlsx`. Power BI creates a semantic model
   from the workbook's tables.
3. Open the model → **Open data model** (if your licence shows it) and create
   the 9 relationships from `data_model.md`. Mark `dim_date` as the date
   table. If web modelling is not available on your licence, skip this —
   the `flat_sales_dealer` and `flat_feedback_dealer` sheets already carry
   dealer name/city/region, so most visuals still work.
4. **Create report** and build the 5 pages from `dashboard_build_guide.md`:
   Executive Summary, Digital Performance, Dealer Performance,
   Marketing & NPS, Call Center & VoC. Theme: white background, blue
   `#2563eb` primary, red `#dc2626` for bad, grey for context.
5. Add the measures from `dax_measures.dax` (in Desktop, or in web modelling
   where available). At minimum: Total Sales, Conversion %, AOV, NPS,
   Resolution %, Campaign ROI (x), Target Achievement %.
6. Save the report as **AutoNova Omnichannel Analytics**.

## Sharing — honest limits

- A **free** Power BI licence keeps the report in your own workspace. You can
  open it in interviews and export pages as PDF/images for GitHub and your
  resume.
- A public **Publish to web** link normally needs a Pro / Premium / Fabric
  licence and tenant permission. Do not promise a public Power BI link on a
  free account.
- For a public interactive link, this same project also has a Streamlit
  version (`app.py`, see `DEPLOYMENT.md` at the project root). Portfolio
  pattern used by recruiters: Power BI screenshots/PDF in the README +
  Streamlit live link.

## Honesty note

The data is synthetic, generated for this portfolio project. The dashboard
itself says so. Never present the numbers as real company results.
