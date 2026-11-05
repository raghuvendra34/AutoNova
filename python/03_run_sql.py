"""03_run_sql.py - executes every query in sql/analysis_queries.sql, saves results to docs/sql_results/ and prints them."""
import re, sqlite3
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
out = ROOT / "docs" / "sql_results"; out.mkdir(parents=True, exist_ok=True)
text = (ROOT / "sql" / "analysis_queries.sql").read_text()
parts = re.split(r"^-- (Q\d+): (.*)$", text, flags=re.M)[1:]
con = sqlite3.connect(ROOT / "data" / "omnichannel.db")
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
for i in range(0, len(parts), 3):
    qid, title, sql = parts[i], parts[i + 1], parts[i + 2].strip()
    df = pd.read_sql(sql, con)
    df.to_csv(out / f"{qid}.csv", index=False)
    print(f"\n=== {qid}: {title} ===\n{df.head(12).to_string(index=False)}")
