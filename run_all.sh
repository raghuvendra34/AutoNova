#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/python"
python3 01_generate_data.py
python3 02_clean_and_enrich.py
python3 03_run_sql.py > ../docs/sql_results/_all_results.txt
python3 04_insights_and_charts.py
echo "Done. Clean CSVs in data/clean, DB in data/omnichannel.db, charts in charts/"
