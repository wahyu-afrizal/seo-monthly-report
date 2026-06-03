---
name: seo-monthly-report
description: Generate SEO monthly insight reports for any retainer client from GA4 and GSC CSV exports. Produces a data workbook (.xlsx) and fills insight copy based on query behaviour analysis. Use when asked to create or update a monthly SEO report for AXIS, XL Satu, MSIG Online, The Union Group, or any other retainer client.
---

# SEO Monthly Report — Generic (All Retainer Clients)

## Overview

Two-phase workflow:
1. **Script phase** — Python script reads CSVs + `report_config.json`, produces `.xlsx` (data tables) and `_analysis.json` (structured data + query signals)
2. **Insight phase** — Claude reads `_analysis.json` and fills all insight copy: page-level insights, summary narrative, reopt recommendations

Output for each period:
- `<prefix> - <period>.xlsx` — 3-tab workbook (month tab, Summary, Reoptimisation)
- `<prefix> - <period>_analysis.json` — intermediate data file (not delivered to client)
- `<prefix> - <period>.md` — narrative summary (Claude produces this at the end)

---

## Setup — report_config.json

Each client's report folder must have a `report_config.json`. Create one if missing.

### Minimal config (no conversions):
```json
{
  "client_name": "XL Satu",
  "period": "May 2026",
  "prepared_by": "Antikode SEO",
  "csv": {
    "gsc_landing_pages": "XL Satu - LP GSC May 2026.csv",
    "gsc_queries": "XL Satu - Queries GSC May 2026.csv",
    "ga4_landing_pages": "XL Satu - LP GA4 May 2026.csv"
  },
  "filters": {
    "exclude_path_prefix": [],
    "min_impressions_for_opportunity": 500
  },
  "output_prefix": "XL Satu - SEO Monthly Insight Report"
}
```

### With conversions:
```json
{
  "client_name": "AXIS",
  "period": "May 2026",
  "prepared_by": "Antikode SEO",
  "csv": {
    "gsc_landing_pages": "AXIS - LP GSC May 2026.csv",
    "gsc_queries": "AXIS - Queries GSC May 2026.csv",
    "ga4_landing_pages": "AXIS - LP GA4 May 2026.csv"
  },
  "conversions": {
    "enabled": true,
    "label": "Conversions",
    "csv": "AXIS - Conversions GA4 May 2026.csv",
    "columns": {
      "event_name": "Event Name",
      "landing_page": "Landing page",
      "value": "Conversion",
      "delta": "Δ"
    }
  },
  "filters": {
    "exclude_path_prefix": [],
    "min_impressions_for_opportunity": 500
  },
  "output_prefix": "AXIS - SEO Monthly Insight Report"
}
```

### TUG (with /id/ exclusion):
```json
{
  "client_name": "The Union Group",
  "period": "May 2026",
  "prepared_by": "Antikode Analytics",
  "csv": {
    "gsc_landing_pages": "The Union Group - LP GSC May 2026.csv",
    "gsc_queries": "The Union Group - Queries GSC May 2026.csv",
    "ga4_landing_pages": "The Union Group - LP GA4 May 2026.csv"
  },
  "filters": {
    "exclude_path_prefix": ["/id/"],
    "min_impressions_for_opportunity": 1000
  },
  "output_prefix": "The Union Group - SEO Monthly Insight Report"
}
```

---

## Phase 0 — Check for report_config.json

Before running the script, check if `report_config.json` exists in the report folder.

**If it exists:** proceed to Phase 1.

**If it does NOT exist:**
1. List all `.csv` files in the folder
2. Infer what you can from filenames (client name, period, which CSVs are LP GSC / Queries GSC / GA4 / Conversions)
3. Ask the user only for what cannot be inferred:
   - Confirm client name and period if uncertain
   - Ask: "Does this client have conversion data?" — if yes, confirm which CSV is the conversion file and what label to use (e.g. "Leads", "Conversions", "Purchases")
   - Ask: "Are there any URL prefixes to exclude?" (e.g. `/id/` for TUG bilingual sites) — default no
4. Create `report_config.json` in the report folder using the example template for that client (or the generic template if unknown client)
5. Confirm the config was created, then proceed to Phase 1

Example question to ask:
> "I don't see a `report_config.json` in this folder. I found these CSV files: [list files]. I'll set this up as **[inferred client]** for **[inferred period]**. Does this client have conversion data? And any URL prefixes to exclude from the analysis?"

---

## Phase 1 — Run Script

```bash
cd /path/to/client/report/folder
python3 ~/.claude/skills/seo-monthly-report/scripts/generate_monthly_report.py
```

Script will:
- Load all CSVs
- Calculate top 5 session increases/decreases
- Calculate top 5 conversion increases/decreases (if enabled) — all events aggregated per page
- Auto-generate reopt candidates from: high impressions + low CTR, click drops, position declines
- Extract query signals per page via keyword matching on URL slug
- Write `.xlsx` with placeholder insight cells
- Write `_analysis.json` with full structured data

---

## Phase 2 — Fill Insights (Claude) + Produce Final XLSX

After the script runs:
1. Read `_analysis.json`
2. Write `insights.json` to the **same folder** (format below) — this is what the script picks up to populate the xlsx
3. Re-run the script — it detects `insights.json` and produces a final xlsx with all insight cells populated
4. Produce the `.md` narrative

### insights.json format:
```json
{
  "session_increases": ["insight for page 1", "insight for page 2", ...],
  "session_decreases": ["insight for page 1", ...],
  "conversion_increases": ["insight for page 1", ...],
  "conversion_decreases": ["insight for page 1", ...],
  "reopt": [
    { "path": "/url", "opportunity": "...", "action": "..." },
    ...
  ],
  "summary": {
    "growth_driver": "...",
    "decline_risk": "...",
    "key_opportunity": "...",
    "content_opportunity": "...",
    "recommendation_focus": "...",
    "slide_narrative": "..."
  }
}
```

Arrays must match the order of pages in the analysis JSON. All copy should be in **English**.

### For each page in session_movers and conversion_movers:

Look at `query_signals` for that page:
- `hint: "position_drop_causing_click_loss"` → page dropped in rankings for these queries, lost clicks as result
- `hint: "demand_decline"` → search interest for related queries is shrinking
- `hint: "visible_but_not_clicked"` → page appears in search but not convincing users — possible title/meta issue
- `hint: "ranking_improvement_driving_growth"` → page climbed in rankings, driving more clicks
- `hint: "organic_growth"` → more searches and more clicks — healthy demand growth
- `hint: "stable"` → no strong query signal, describe based on available metrics

Also use `site_query_trends.top_declining` and `top_growing` for context when individual page signals are weak.

Write each insight in **1–2 sentences**, non-technical, easy for client stakeholders to understand.

### For reopt candidates:

Each candidate has `issue_type` + `query_signals`. Write:
- **Opportunity**: why this page is underperforming (based on data + query behaviour)
- **Recommended Action**: content-led fix (better headline/intro, stronger sections, clearer intent match, internal linking). Do not default to technical recommendations unless issue_type is explicitly technical.

### For Summary tab:

Fill:
- **Biggest Growth Driver**: top session increase page + what query behaviour explains it
- **Biggest Decline Risk**: top session decrease page + root cause from query signals
- **Key Opportunity**: highest-impression low-CTR page from reopt candidates
- **Content Opportunity**: a page with growing impressions but underperforming CTR or position
- **Recommendation Focus**: one-sentence priority action for next month
- **Slide Narrative**: 3–4 sentences covering totals trend + key growth driver + key risk + one action. Suitable for a deck slide, non-technical.

### Produce final .md:

After filling insights, produce a `<prefix> - <period>.md` with:
- Executive summary paragraph
- Top 5 session increases (with insight per page)
- Top 5 session decreases (with insight per page)
- Top 5 conversion increases/decreases (if enabled, with insight per page)
- Reopt candidates table (URL, issue, opportunity, action)
- Slide narrative

---

## Workbook Tab Structure

| Tab | Contents |
|-----|----------|
| `<period>` e.g. `May 2026` | Top 5 session increase/decrease + top 5 conversion increase/decrease (if enabled) |
| `📋 Summary` | Executive summary + slide narrative |
| `🔧 Reoptimisation` | Auto-generated candidates with opportunity + action |

---

## Notes

- Conversion CSV format: `Event Name`, `Landing page`, `Conversion`, `Δ` — all events aggregated per page
- GSC query CSV is site-wide (not per-LP). Query signals use URL keyword matching — not perfect but surfaces relevant patterns
- `generate_union_monthly_report.py` still works for TUG legacy runs (hardcoded March 2026 format)
- Reopt recommendations are **content-led by default** unless the user explicitly asks for technical audit
