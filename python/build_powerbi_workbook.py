"""Build the Power BI data package for the Omnichannel Analytics project.

Reads the cleaned CSVs in data/clean/ and writes one Excel workbook,
powerbi/PowerBI_AutoNova_Data.xlsx, with:
  - a README sheet (model map + relationships + honesty note)
  - one sheet per model table (dim_date, dealers, sales, service_jobs,
    inventory, campaigns, web_sessions, feedback, call_logs)
  - two pre-joined flat sheets (flat_sales_dealer, flat_feedback_dealer)
    so simple reports work even before relationships are created.

Upload the workbook to Power BI Service (Get Data -> Excel) or open it in
Power BI Desktop, then follow powerbi/data_model.md, dax_measures.dax and
dashboard_build_guide.md.

Data note: the dataset is synthetic (generated for this portfolio project).
"""

from pathlib import Path

import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "powerbi" / "PowerBI_AutoNova_Data.xlsx"

DATE_COLS = {
    "dim_date": ["date"],
    "sales": ["sale_date"],
    "service_jobs": ["job_date"],
    "inventory": ["snapshot_date"],
    "web_sessions": ["session_date"],
    "feedback": ["feedback_date"],
    "call_logs": ["call_date"],
}

TABLES = [
    "dim_date",
    "dealers",
    "sales",
    "service_jobs",
    "inventory",
    "campaigns",
    "web_sessions",
    "feedback",
    "call_logs",
]

README_LINES = [
    ("AutoNova Omnichannel Analytics - Power BI data package", True),
    ("", False),
    ("HONESTY NOTE: This dataset is SYNTHETIC. It was generated for a learning /", False),
    ("portfolio project, with patterns deliberately planted so the analysis has", False),
    ("something to detect. Findings demonstrate method, not real business results.", False),
    ("", False),
    ("HOW TO USE", True),
    ("1. Power BI Service (browser, works on Mac): sign in at app.powerbi.com with a", False),
    ("   work or school Microsoft account -> My workspace -> New item -> Upload ->", False),
    ("   this workbook. Then open the semantic model and choose 'Create report'.", False),
    ("2. Power BI Desktop (Windows): Get Data -> Excel -> this workbook.", False),
    ("3. Create the relationships listed below (Model view), mark dim_date as the", False),
    ("   date table, create a _Measures table and paste in dax_measures.dax.", False),
    ("4. Build the 5 report pages from dashboard_build_guide.md.", False),
    ("", False),
    ("RELATIONSHIPS (many -> one, single direction)", True),
    ("sales[dealer_id] -> dealers[dealer_id]", False),
    ("service_jobs[dealer_id] -> dealers[dealer_id]", False),
    ("inventory[dealer_id] -> dealers[dealer_id]", False),
    ("feedback[dealer_id] -> dealers[dealer_id]", False),
    ("sales[sale_date] -> dim_date[date]", False),
    ("service_jobs[job_date] -> dim_date[date]", False),
    ("web_sessions[session_date] -> dim_date[date]", False),
    ("feedback[feedback_date] -> dim_date[date]", False),
    ("call_logs[call_date] -> dim_date[date]", False),
    ("", False),
    ("FLAT SHEETS", True),
    ("flat_sales_dealer and flat_feedback_dealer are pre-joined with dealer name,", False),
    ("city and region, so basic visuals work even before relationships are set up.", False),
]


def load(name):
    df = pd.read_csv(CLEAN / f"{name}.csv")
    for col in DATE_COLS.get(name, []):
        df[col] = pd.to_datetime(df[col])
    return df


def main():
    frames = {name: load(name) for name in TABLES}
    dealers = frames["dealers"]

    flat_sales = frames["sales"].merge(
        dealers[["dealer_id", "dealer_name", "city", "region", "manager"]],
        on="dealer_id",
        how="left",
    )
    flat_feedback = frames["feedback"].merge(
        dealers[["dealer_id", "dealer_name", "city", "region"]],
        on="dealer_id",
        how="left",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
        # README first (placeholder row replaced below)
        pd.DataFrame({"README": []}).to_excel(writer, sheet_name="README", index=False)
        for name in TABLES:
            frames[name].to_excel(writer, sheet_name=name, index=False)
        flat_sales.to_excel(writer, sheet_name="flat_sales_dealer", index=False)
        flat_feedback.to_excel(writer, sheet_name="flat_feedback_dealer", index=False)

        wb = writer.book

        ws = wb["README"]
        ws.sheet_properties.pageSetUpPr = None
        for row, (text, bold) in enumerate(README_LINES, start=1):
            cell = ws.cell(row=row, column=1, value=text)
            if bold:
                cell.font = Font(bold=True, size=12)
        ws.column_dimensions["A"].width = 95

        for name in TABLES + ["flat_sales_dealer", "flat_feedback_dealer"]:
            ws = wb[name]
            n_rows, n_cols = ws.max_row, ws.max_column
            ref = f"A1:{get_column_letter(n_cols)}{n_rows}"
            tab = Table(displayName=f"tbl_{name}", ref=ref)
            tab.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2", showRowStripes=True
            )
            ws.add_table(tab)
            ws.freeze_panes = "A2"
            for col_idx in range(1, n_cols + 1):
                header = str(ws.cell(row=1, column=col_idx).value or "")
                width = min(max(len(header) + 4, 12), 42)
                ws.column_dimensions[get_column_letter(col_idx)].width = width

    print(f"Wrote {OUT}")
    for name in TABLES:
        print(f"  {name}: {len(frames[name]):,} rows")
    print(f"  flat_sales_dealer: {len(flat_sales):,} rows")
    print(f"  flat_feedback_dealer: {len(flat_feedback):,} rows")


if __name__ == "__main__":
    main()
