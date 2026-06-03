# SEO Monthly Report — Step-by-Step Guide

For Antikode SEO team. Works for all retainer clients: AXIS, XL Satu, MSIG Online, The Union Group.

---

## What This Does

Takes your GA4 and GSC CSV exports and produces:
- **`.xlsx` workbook** — 3 tabs: monthly movers, executive summary, reoptimisation candidates
- **`.md` narrative** — ready-to-use insight copy per page, based on actual query behaviour

Claude handles the analysis and writes the insight copy — you review and paste into the deck.

---

## Installation (one-time setup)

1. Copy the `seo-monthly-report` folder into your Claude skills directory:
```bash
cp -r seo-monthly-report ~/.claude/skills/
```
2. Verify it's there:
```bash
ls ~/.claude/skills/seo-monthly-report/
```
You should see: `SKILL.md`, `README.md`, `scripts/`, `examples/`

That's it — no restart needed. The skill is immediately available in any Claude Code session.

---

## Prerequisites

- Claude Code installed and running
- Python 3.10+ installed
- Your GA4 + GSC CSV exports for the month

---

## Step 1 — Export Your CSVs

You need **3 exports** per client (4 if client has conversion tracking):

| File | Where to export | What it contains |
|------|----------------|-----------------|
| LP GSC | Google Search Console → Search results → Filter by Landing Page | Clicks, impressions, CTR, position per page |
| Queries GSC | Google Search Console → Search results → Filter by Query | Clicks, impressions, CTR, position per query |
| LP GA4 | GA4 → Reports → Landing page | Sessions, new users per page |
| Conversions GA4 *(optional)* | GA4 → Reports → Events → filter by conversion events | Event name, landing page, conversion count |

**GSC export format must include delta columns (Δ).** Export from your Data Studio / Looker Studio report, not raw GSC — raw GSC doesn't include period-over-period deltas.

**Naming convention** (follow exactly so the config works):
```
AXIS - LP GSC May 2026.csv
AXIS - Queries GSC May 2026.csv
AXIS - LP GA4 May 2026.csv
AXIS - Conversions GA4 May 2026.csv   ← only if client has conversion data
```

---

## Step 2 — Place Files in the Report Folder

Drop all CSVs into the client's monthly report folder:
```
client-active/
  axis/
    Report/
      may-2026/
        AXIS - LP GSC May 2026.csv
        AXIS - Queries GSC May 2026.csv
        AXIS - LP GA4 May 2026.csv
        AXIS - Conversions GA4 May 2026.csv
        report_config.json          ← you create this (see Step 3)
```

---

## Step 3 — Create report_config.json

Copy the right example from the `examples/` folder in this directory and rename it to `report_config.json`. Then update `"period"` to the current month.

**Examples available:**
- `examples/report_config.axis.json` → AXIS (with conversions)
- `examples/report_config.xl-satu.json` → XL Satu
- `examples/report_config.msig-online.json` → MSIG Online
- `examples/report_config.union-group.json` → The Union Group (with `/id/` exclusion)

**The only field you need to update each month is `"period"`:**
```json
{
  "client_name": "AXIS",
  "period": "June 2026",     ← update this
  ...
}
```

And update the CSV filenames if they differ from your naming convention.

---

## Step 4 — Run the Report

Open Claude Code, navigate to the report folder, and say:

> *"Generate the monthly report"*

or

> *"Run /seo-monthly-report for AXIS May 2026"*

Claude will:
1. Run the data script → produces `.xlsx` (with placeholders) + `_analysis.json`
2. Read `_analysis.json` and analyse query behaviour per page
3. Write `insights.json` to the report folder
4. Re-run the script — detects `insights.json` and produces a final `.xlsx` with all insights populated
5. Produce the final `.md` narrative

> **Note:** The `insights.json` file stays in the folder after the run — if you need to tweak any insight copy, edit it there and re-run the script manually to regenerate the xlsx.

---

## Step 5 — Review the Output

Check the three output files in your report folder:

### `AXIS - SEO Monthly Insight Report - May 2026.xlsx`
Three tabs:
- **`May 2026`** — top 5 session increase/decrease (+ conversion movers if enabled), each with a 1–2 sentence insight
- **`📋 Summary`** — executive summary + slide narrative, ready to paste into deck
- **`🔧 Reoptimisation`** — auto-generated candidates with opportunity + recommended action

### `AXIS - SEO Monthly Insight Report - May 2026.md`
Same content as the workbook but in markdown — useful for copying into Notion, docs, or Lark.

### `AXIS - SEO Monthly Insight Report - May 2026_analysis.json`
Intermediate file used by Claude. You don't need to open this — it's the raw data that informed the insight copy.

---

## Common Questions

**Q: The script says "report_config.json not found"**
Make sure you're running from inside the report folder (the same folder as your CSVs), not the root of the project.

**Q: A client doesn't have conversion data yet**
Set `"conversions": { "enabled": false }` in the config. The conversion movers section will be skipped automatically.

**Q: The insight for a page feels generic**
The query matching uses URL keywords. If the page slug is very short (e.g., `/produk`) there's less to match on. You can add more context by editing that specific insight manually.

**Q: I need to add a new client**
Copy any example config, update `client_name`, `csv` filenames, `output_prefix`, and any `filters`. That's it — no code changes needed.

**Q: The Union Group has both English and Indonesian pages**
The `exclude_path_prefix: ["/id/"]` filter in TUG's config automatically removes Indonesian pages from all analysis. Only English pages are included in movers and reopt candidates.

**Q: How do I adjust the reoptimisation threshold?**
Change `min_impressions_for_opportunity` in the config. Default is 500. For smaller sites (MSIG Online) use 200; for larger sites (AXIS) 500 is fine.

---

## Folder Structure Reference

```
~/.claude/skills/seo-monthly-report/
  README.md                          ← this file
  SKILL.md                           ← Claude's instructions (don't edit)
  scripts/
    generate_monthly_report.py       ← main script (all clients)
    generate_union_monthly_report.py ← TUG legacy (March 2026 hardcoded)
  examples/
    report_config.axis.json
    report_config.xl-satu.json
    report_config.msig-online.json
    report_config.union-group.json
```

---

## Contact

Questions about this workflow → Jemmima / analytics@antikode.com
