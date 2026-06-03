#!/usr/bin/env python3
"""
Generic SEO Monthly Report Generator — all retainer clients.

Usage:
    cd /path/to/report/folder   # must contain report_config.json + CSVs
    python3 generate_monthly_report.py

Outputs:
    <output_prefix> - <period>.xlsx       — data workbook (3 tabs)
    <output_prefix> - <period>_analysis.json  — structured data for Claude insight pass
"""

import csv
import json
import math
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape


# ── Config ─────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    p = Path("report_config.json")
    if not p.exists():
        raise FileNotFoundError(
            "report_config.json not found. Run this script from the report folder."
        )
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ── Utilities ──────────────────────────────────────────────────────────────────

def to_float(v) -> float:
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def normalize_path(value: str) -> str:
    if not value:
        return ""
    v = str(value).strip()
    if v.startswith("http://") or v.startswith("https://"):
        v = urlparse(v).path
    return v.rstrip("/") or "/"


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        return []
    header = rows[0]
    seen: dict[str, int] = {}
    norm_header = []
    for col in header:
        count = seen.get(col, 0)
        norm_header.append(col if count == 0 else f"{col}_{count}")
        seen[col] = count + 1
    return [dict(zip(norm_header, row)) for row in rows[1:] if any(row)]


def pct_change(current: float, delta: float) -> float:
    prev = current - delta
    return 0.0 if prev == 0 else delta / prev


def fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def fmt_num(v: float) -> str:
    if math.isclose(v, round(v)):
        return f"{int(round(v)):,}"
    return f"{v:,.1f}"


def slug_keywords(path: str) -> list[str]:
    """Extract meaningful words from URL slug for query matching."""
    slug = path.strip("/").split("/")[-1]
    words = re.split(r"[-_]", slug)
    stopwords = {
        "dan", "di", "ke", "yang", "ini", "itu", "dengan", "untuk", "dari",
        "cara", "how", "to", "the", "a", "and", "or", "in", "of", "apa", "itu",
        "adalah", "cek", "beli", "kartu", "paket",
    }
    return [w.lower() for w in words if len(w) > 2 and w.lower() not in stopwords]


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class LPRow:
    path: str
    clicks: float
    click_delta: float
    impressions: float
    impression_delta: float
    ctr: float
    ctr_delta: float
    avg_position: float
    position_pct_delta: float
    query_count: float


@dataclass
class QueryRow:
    query: str
    clicks: float
    click_delta: float
    impressions: float
    impression_delta: float
    ctr: float
    avg_position: float
    position_pct_delta: float


@dataclass
class GA4Row:
    path: str
    sessions: float
    session_delta: float
    new_users: float
    total_users: float


@dataclass
class ConvRow:
    path: str
    conversions: float
    conversion_delta: float


# ── Data loading ───────────────────────────────────────────────────────────────

def load_landing_pages(cfg: dict) -> list[LPRow]:
    rows = load_csv(Path(cfg["csv"]["gsc_landing_pages"]))
    result = []
    for r in rows:
        path = normalize_path(r.get("Landing Page") or r.get("Landing page") or "")
        if not path or path == "(not set)":
            continue
        result.append(LPRow(
            path=path,
            clicks=to_float(r.get("URL Clicks") or r.get("Clicks") or 0),
            click_delta=to_float(r.get("Δ") or 0),
            impressions=to_float(r.get("Impressions") or 0),
            impression_delta=to_float(r.get("Δ_1") or 0),
            ctr=to_float(r.get("URL CTR") or r.get("CTR") or 0),
            ctr_delta=to_float(r.get("Δ_2") or 0),
            avg_position=to_float(r.get("Avg. Position") or r.get("Average Position") or 0),
            position_pct_delta=to_float(r.get("% Δ") or 0),
            query_count=to_float(r.get("Query") or 0),
        ))
    return result


def load_queries(cfg: dict) -> list[QueryRow]:
    rows = load_csv(Path(cfg["csv"]["gsc_queries"]))
    result = []
    for r in rows:
        q = r.get("Query", "").strip()
        if not q:
            continue
        result.append(QueryRow(
            query=q,
            clicks=to_float(r.get("URL Clicks") or r.get("Clicks") or 0),
            click_delta=to_float(r.get("Δ") or 0),
            impressions=to_float(r.get("Impressions") or 0),
            impression_delta=to_float(r.get("Δ_1") or 0),
            ctr=to_float(r.get("URL CTR") or r.get("CTR") or 0),
            avg_position=to_float(r.get("Average Position") or r.get("Avg. Position") or 0),
            position_pct_delta=to_float(r.get("% Δ") or 0),
        ))
    return result


def load_ga4(cfg: dict) -> list[GA4Row]:
    rows = load_csv(Path(cfg["csv"]["ga4_landing_pages"]))
    result = []
    for r in rows:
        path = normalize_path(
            r.get("LP & Query String") or r.get("Landing Page") or r.get("Landing page") or ""
        )
        if not path or path == "(not set)":
            continue
        result.append(GA4Row(
            path=path,
            sessions=to_float(r.get("Sessions") or 0),
            session_delta=to_float(r.get("Δ") or 0),
            new_users=to_float(r.get("New Users") or 0),
            total_users=to_float(r.get("Total Users") or r.get("Total users") or 0),
        ))
    return result


def load_conversions(cfg: dict) -> list[ConvRow]:
    conv_cfg = cfg.get("conversions", {})
    if not conv_cfg.get("enabled"):
        return []

    col_cfg = conv_cfg.get("columns", {})
    lp_col = col_cfg.get("landing_page", "Landing page")
    val_col = col_cfg.get("value", "Conversion")
    delta_col = col_cfg.get("delta", "Δ")

    rows = load_csv(Path(conv_cfg["csv"]))
    agg: dict[str, list] = defaultdict(lambda: [0.0, 0.0])

    for r in rows:
        path = normalize_path(r.get(lp_col, "") or "")
        if not path or path == "(not set)":
            continue
        agg[path][0] += to_float(r.get(val_col) or 0)
        raw_delta = str(r.get(delta_col, "") or "").strip()
        if raw_delta:
            agg[path][1] += to_float(raw_delta)

    return [ConvRow(path=p, conversions=v[0], conversion_delta=v[1]) for p, v in agg.items()]


# ── Analysis helpers ───────────────────────────────────────────────────────────

def build_gsc_lookup(lp_rows: list[LPRow]) -> dict[str, LPRow]:
    lookup: dict[str, LPRow] = {}
    for row in lp_rows:
        ex = lookup.get(row.path)
        if ex is None or (row.clicks, row.impressions) > (ex.clicks, ex.impressions):
            lookup[row.path] = row
    return lookup


def apply_exclusions(rows: list, exclude: list[str]):
    return [r for r in rows if not any(r.path.startswith(p) for p in exclude)]


def top_movers(rows: list, key_fn, n: int = 5) -> tuple[list, list]:
    by_delta = sorted(rows, key=key_fn, reverse=True)
    increases = by_delta[:n]
    decreases = [r for r in reversed(by_delta) if key_fn(r) < 0][:n]
    return increases, decreases


def reopt_candidates(lp_rows: list[LPRow], ga4_lookup: dict, cfg: dict) -> list[dict]:
    threshold = cfg.get("filters", {}).get("min_impressions_for_opportunity", 500)
    candidates = []
    for row in lp_rows:
        if row.impressions < threshold:
            continue
        ga4 = ga4_lookup.get(row.path)

        if row.ctr < 0.02:
            issue = "High impressions, low CTR"
        elif row.click_delta < 0 and row.impression_delta >= 0:
            issue = "Click drop with stable/growing impressions"
        elif row.position_pct_delta > 0.10 and row.clicks > 10:
            issue = "Position decline"
        elif row.click_delta < -10:
            issue = "Significant click decline"
        else:
            continue

        candidates.append({
            "path": row.path,
            "issue_type": issue,
            "impressions": int(row.impressions),
            "impression_delta": int(row.impression_delta),
            "clicks": int(row.clicks),
            "click_delta": int(row.click_delta),
            "ctr": round(row.ctr, 4),
            "avg_position": round(row.avg_position, 1),
            "sessions": int(ga4.sessions) if ga4 else 0,
            "session_delta": int(ga4.session_delta) if ga4 else 0,
        })

    candidates.sort(key=lambda x: x["impressions"], reverse=True)
    return candidates[:10]


def query_signals(path: str, queries: list[QueryRow], top_n: int = 5) -> dict:
    """Match queries to a page via URL keyword overlap and extract signal patterns."""
    keywords = slug_keywords(path)
    if not keywords:
        return {"matched_queries": [], "signals": []}

    scored = []
    for q in queries:
        ql = q.query.lower()
        score = sum(1 for kw in keywords if kw in ql)
        if score > 0:
            scored.append((score, q))

    scored.sort(key=lambda x: (-x[0], -x[1].impressions))
    top = [q for _, q in scored[:top_n]]

    signals = []
    for q in top:
        if q.position_pct_delta > 0.05 and q.click_delta < 0:
            hint = "position_drop_causing_click_loss"
        elif q.impression_delta < 0 and q.click_delta < 0:
            hint = "demand_decline"
        elif q.impression_delta > 0 and q.ctr < 0.01:
            hint = "visible_but_not_clicked"
        elif q.click_delta > 0 and q.position_pct_delta < -0.05:
            hint = "ranking_improvement_driving_growth"
        elif q.click_delta > 0 and q.impression_delta > 0:
            hint = "organic_growth"
        else:
            hint = "stable"

        signals.append({
            "query": q.query,
            "clicks": int(q.clicks),
            "click_delta": int(q.click_delta),
            "impressions": int(q.impressions),
            "impression_delta": int(q.impression_delta),
            "ctr": fmt_pct(q.ctr),
            "avg_position": round(q.avg_position, 1),
            "hint": hint,
        })

    return {"matched_queries": [q.query for q in top], "signals": signals}


# ── XLSX writer ────────────────────────────────────────────────────────────────

def cell_xml(value, style_id=0) -> str:
    if value is None:
        return f'<c s="{style_id}"/>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(value) or math.isinf(value):
            value = 0
        return f'<c s="{style_id}"><v>{value}</v></c>'
    return f'<c t="inlineStr" s="{style_id}"><is><t>{escape(str(value))}</t></is></c>'


def build_sheet_xml(rows: list) -> str:
    row_xml = []
    for idx, row in enumerate(rows, start=1):
        style = 1 if idx == 1 else 0
        cells = "".join(cell_xml(v, style_id=style) for v in row)
        row_xml.append(f'<row r="{idx}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


def write_workbook(sheets: list[tuple[str, list]], output_path: Path):
    wb_xml = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        "<sheets>",
    ]
    wb_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    ct = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for idx, (name, _) in enumerate(sheets, start=1):
        wb_xml.append(f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>')
        wb_rels.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
        ct.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    wb_xml.extend(["</sheets>", "</workbook>"])
    wb_rels.append(
        '<Relationship Id="rIdStyles" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    wb_rels.append("</Relationships>")
    ct.append("</Types>")

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>\n</Relationships>'
    )
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFD9EAF7"/>'
        '<bgColor indexed="64"/></patternFill></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="1" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "\n".join(ct))
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", "\n".join(wb_xml))
        zf.writestr("xl/_rels/workbook.xml.rels", "\n".join(wb_rels))
        zf.writestr("xl/styles.xml", styles_xml)
        for idx, (_, rows) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", build_sheet_xml(rows))


# ── Sheet builders ─────────────────────────────────────────────────────────────

def build_month_sheet(cfg, session_inc, session_dec, conv_inc, conv_dec, insights: dict) -> list:
    period = cfg["period"]
    conv_cfg = cfg.get("conversions", {})
    conv_enabled = conv_cfg.get("enabled", False)
    conv_label = conv_cfg.get("label", "Conversions")
    ph = "—"

    si = insights.get("session_increases", [])
    sd = insights.get("session_decreases", [])
    ci = insights.get("conversion_increases", [])
    cd = insights.get("conversion_decreases", [])

    rows = [
        [f"Top 5 Increase in Sessions — {period}", "", "", ""],
        ["No", "Page", "Δ Sessions", "Insight"],
    ]
    for i, r in enumerate(session_inc, 1):
        rows.append([i, r.path, int(r.session_delta), si[i-1] if i-1 < len(si) else ph])

    rows += [[], [f"Top 5 Decrease in Sessions — {period}", "", "", ""], ["No", "Page", "Δ Sessions", "Insight"]]
    for i, r in enumerate(session_dec, 1):
        rows.append([i, r.path, int(r.session_delta), sd[i-1] if i-1 < len(sd) else ph])

    if conv_enabled:
        rows += [
            [],
            [f"Top 5 Increase in {conv_label} — {period}", "", "", ""],
            ["No", "Page", f"Δ {conv_label}", "Insight"],
        ]
        for i, r in enumerate(conv_inc, 1):
            rows.append([i, r.path, int(r.conversion_delta), ci[i-1] if i-1 < len(ci) else ph])

        rows += [
            [],
            [f"Top 5 Decrease in {conv_label} — {period}", "", "", ""],
            ["No", "Page", f"Δ {conv_label}", "Insight"],
        ]
        for i, r in enumerate(conv_dec, 1):
            rows.append([i, r.path, int(r.conversion_delta), cd[i-1] if i-1 < len(cd) else ph])

    return rows


def build_summary_sheet(cfg, insights: dict) -> list:
    client = cfg["client_name"]
    period = cfg["period"]
    prepared_by = cfg.get("prepared_by", "Antikode SEO")
    s = insights.get("summary", {})
    ph = "—"
    return [
        [f"{client} · SEO Monthly Report · {period}"],
        [f"Client: {client}  |  Prepared by: {prepared_by}  |  Period: {period}"],
        [],
        ["📌  Executive Summary"],
        ["Biggest Growth Driver", s.get("growth_driver", ph), ""],
        ["Biggest Decline Risk", s.get("decline_risk", ph), ""],
        ["Key Opportunity", s.get("key_opportunity", ph), ""],
        ["Content Opportunity", s.get("content_opportunity", ph), ""],
        ["Recommendation Focus", s.get("recommendation_focus", ph), ""],
        [],
        ["🎙  Slide Narrative"],
        [s.get("slide_narrative", ph)],
    ]


def build_reopt_sheet(cfg, candidates: list, insights: dict) -> list:
    period = cfg["period"]
    ph = "—"
    reopt_insights = insights.get("reopt", [])
    reopt_lookup = {r.get("path", ""): r for r in reopt_insights}

    rows = [
        [f"🔧  Reoptimisation Candidates — {period}"],
        ["URL", "Issue Type", "Impressions", "Δ Impr", "Clicks", "Δ Clicks", "CTR", "Avg Pos", "Opportunity", "Recommended Action"],
    ]
    for c in candidates:
        ri = reopt_lookup.get(c["path"], {})
        rows.append([
            c["path"],
            c["issue_type"],
            c["impressions"],
            c["impression_delta"],
            c["clicks"],
            c["click_delta"],
            fmt_pct(c["ctr"]),
            c["avg_position"],
            ri.get("opportunity", ph),
            ri.get("action", ph),
        ])
    return rows


# ── Analysis JSON ──────────────────────────────────────────────────────────────

def build_analysis_json(
    cfg, session_inc, session_dec, conv_inc, conv_dec,
    candidates, queries, gsc_lookup, ga4_lookup, lp_rows, conv_rows
) -> dict:
    conv_enabled = cfg.get("conversions", {}).get("enabled", False)
    conv_label = cfg.get("conversions", {}).get("label", "Conversions")

    total_sessions = sum(r.sessions for r in ga4_lookup.values())
    total_session_delta = sum(r.session_delta for r in ga4_lookup.values())
    total_clicks = sum(r.clicks for r in lp_rows)
    total_click_delta = sum(r.click_delta for r in lp_rows)
    total_impressions = sum(r.impressions for r in lp_rows)
    total_impression_delta = sum(r.impression_delta for r in lp_rows)

    conv_lookup = {r.path: r for r in conv_rows}

    def enrich(path, session_delta=None, conv_delta=None) -> dict:
        gsc = gsc_lookup.get(path)
        ga4 = ga4_lookup.get(path)
        conv = conv_lookup.get(path)
        return {
            "path": path,
            "session_delta": session_delta,
            "conversion_delta": conv_delta,
            "gsc": {
                "clicks": int(gsc.clicks) if gsc else None,
                "click_delta": int(gsc.click_delta) if gsc else None,
                "impressions": int(gsc.impressions) if gsc else None,
                "ctr": fmt_pct(gsc.ctr) if gsc else None,
                "avg_position": round(gsc.avg_position, 1) if gsc else None,
            },
            "ga4": {
                "sessions": int(ga4.sessions) if ga4 else None,
                "session_delta": int(ga4.session_delta) if ga4 else None,
            },
            "conversions": {
                "total": int(conv.conversions) if conv else None,
                "delta": int(conv.conversion_delta) if conv else None,
            } if conv_enabled else None,
            "query_signals": query_signals(path, queries),
        }

    return {
        "meta": {
            "client": cfg["client_name"],
            "period": cfg["period"],
            "prepared_by": cfg.get("prepared_by", "Antikode SEO"),
            "conversion_label": conv_label if conv_enabled else None,
            "conversion_enabled": conv_enabled,
        },
        "totals": {
            "sessions": int(total_sessions),
            "session_delta": int(total_session_delta),
            "session_pct_change": fmt_pct(pct_change(total_sessions, total_session_delta)),
            "clicks": int(total_clicks),
            "click_delta": int(total_click_delta),
            "click_pct_change": fmt_pct(pct_change(total_clicks, total_click_delta)),
            "impressions": int(total_impressions),
            "impression_delta": int(total_impression_delta),
        },
        "session_movers": {
            "increases": [enrich(r.path, session_delta=int(r.session_delta)) for r in session_inc],
            "decreases": [enrich(r.path, session_delta=int(r.session_delta)) for r in session_dec],
        },
        "conversion_movers": {
            "enabled": conv_enabled,
            "label": conv_label,
            "increases": [enrich(r.path, conv_delta=int(r.conversion_delta)) for r in conv_inc] if conv_enabled else [],
            "decreases": [enrich(r.path, conv_delta=int(r.conversion_delta)) for r in conv_dec] if conv_enabled else [],
        },
        "reopt_candidates": [
            {**c, "query_signals": query_signals(c["path"], queries)}
            for c in candidates
        ],
        "site_query_trends": {
            "top_declining": sorted(
                [{"query": q.query, "click_delta": int(q.click_delta), "impression_delta": int(q.impression_delta), "avg_position": round(q.avg_position, 1)}
                 for q in queries if q.click_delta < -5],
                key=lambda x: x["click_delta"]
            )[:10],
            "top_growing": sorted(
                [{"query": q.query, "click_delta": int(q.click_delta), "impression_delta": int(q.impression_delta), "avg_position": round(q.avg_position, 1)}
                 for q in queries if q.click_delta > 5],
                key=lambda x: x["click_delta"],
                reverse=True
            )[:10],
        },
    }


# ── Insights loader ────────────────────────────────────────────────────────────

def load_insights() -> dict:
    """Load insights.json if present — Claude writes this after reading analysis JSON."""
    p = Path("insights.json")
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    cfg = load_config()
    period = cfg["period"]
    output_prefix = cfg.get("output_prefix", f"{cfg['client_name']} - SEO Monthly Insight Report")
    exclude = cfg.get("filters", {}).get("exclude_path_prefix", [])

    print(f"Loading data for {cfg['client_name']} — {period}...")

    lp_rows = load_landing_pages(cfg)
    queries = load_queries(cfg)
    ga4_rows = load_ga4(cfg)
    conv_rows = load_conversions(cfg)

    # Apply exclusion filter
    lp_rows = apply_exclusions(lp_rows, exclude)
    ga4_rows = apply_exclusions(ga4_rows, exclude)
    conv_rows = apply_exclusions(conv_rows, exclude)

    # Build lookups
    gsc_lookup = build_gsc_lookup(lp_rows)
    ga4_lookup = {r.path: r for r in ga4_rows}

    # Top movers
    session_inc, session_dec = top_movers(ga4_rows, lambda r: r.session_delta)
    conv_inc, conv_dec = top_movers(conv_rows, lambda r: r.conversion_delta) if conv_rows else ([], [])

    # Reopt candidates
    candidates = reopt_candidates(lp_rows, ga4_lookup, cfg)

    # Load insights if available
    insights = load_insights()
    if insights:
        print("✓ insights.json found — populating xlsx with insight copy")

    # Build sheets
    month_sheet = build_month_sheet(cfg, session_inc, session_dec, conv_inc, conv_dec, insights)
    summary_sheet = build_summary_sheet(cfg, insights)
    reopt_sheet = build_reopt_sheet(cfg, candidates, insights)

    # Build analysis JSON
    analysis = build_analysis_json(
        cfg, session_inc, session_dec, conv_inc, conv_dec,
        candidates, queries, gsc_lookup, ga4_lookup, lp_rows, conv_rows
    )

    # Write outputs
    output_xlsx = Path(f"{output_prefix} - {period}.xlsx")
    output_json = Path(f"{output_prefix} - {period}_analysis.json")

    write_workbook(
        [(period, month_sheet), ("📋 Summary", summary_sheet), ("🔧 Reoptimisation", reopt_sheet)],
        output_xlsx,
    )
    output_json.write_text(json.dumps(analysis, indent=2, ensure_ascii=False))

    conv_note = f" + {len(conv_rows)} conversion rows" if conv_rows else ""
    print(f"✓ Loaded: {len(lp_rows)} LP rows, {len(ga4_rows)} GA4 rows{conv_note}, {len(queries)} queries")
    print(f"✓ {output_xlsx.name}")
    print(f"✓ {output_json.name}")
    if insights:
        print(f"\n✓ Insights applied from insights.json — xlsx is fully populated.")
    else:
        print(f"\nNext: Claude reads {output_json.name}, writes insights.json, then re-runs this script to populate the xlsx.")


if __name__ == "__main__":
    main()
