# Data model (star schema)

Load the 9 CSVs from `data/clean/`. In **Power Query**, set date columns to *Date* type and mark `dim_date` as the Date table.

```
                     dim_date (date)
                    /  |   |   |   \
        sales  service_jobs  web_sessions  feedback  call_logs      (date columns -> dim_date[date])
          \       |                          |
           \      |                          |
            dealers (dealer_id) ------------ +  <- also joins inventory
                                    
campaigns : standalone (channel/quarter), linked to web_sessions via a small `dim_channel` table (optional)
call_logs : agent_id is a degenerate dimension (no agent table needed)
```

## Relationships (all Many-to-One, single direction, from fact -> dimension)
| From (many) | To (one) |
|---|---|
| sales[dealer_id] | dealers[dealer_id] |
| service_jobs[dealer_id] | dealers[dealer_id] |
| inventory[dealer_id] | dealers[dealer_id] |
| feedback[dealer_id] | dealers[dealer_id] |
| sales[sale_date] | dim_date[date] |
| service_jobs[job_date] | dim_date[date] |
| web_sessions[session_date] | dim_date[date] |
| feedback[feedback_date] | dim_date[date] |
| call_logs[call_date] | dim_date[date] |

Optional: create `dim_channel` (distinct values of source/channel) to cross-filter web_sessions and campaigns together.

## Modelling tips (interview talking points)
- Star schema, not one flat table -> faster, clearer filter context.
- Measures (not calculated columns) for all KPIs.
- `dealers` is the shared dimension that lets one Region slicer filter sales, service, NPS and inventory.
- Hide foreign-key columns from report view; use a `_Measures` table.
