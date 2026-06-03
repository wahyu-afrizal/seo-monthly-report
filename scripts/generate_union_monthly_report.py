#!/usr/bin/env python3
import csv
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape


BASE_DIR = Path(__file__).resolve().parent
LP_GSC_CSV = BASE_DIR / "The Union Group - LP GSC March 2026.csv"
QUERY_GSC_CSV = BASE_DIR / "The Union Group - Queries GSC March 2026.csv"
LP_GA4_CSV = BASE_DIR / "The Union Group - LP GA4 March 2026.csv"
OUTPUT_XLSX = BASE_DIR / "The Union Group - SEO Monthly Insight Report - March 2026.xlsx"
OUTPUT_MD = BASE_DIR / "The Union Group - SEO Monthly Insight Report - March 2026.md"


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_path(value):
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        path = urlparse(value).path
    else:
        path = value
    path = path.rstrip("/")
    return path or "/"


def load_csv(path):
    with path.open(newline="") as handle:
        rows = list(csv.reader(handle))
    header = rows[0]
    seen = {}
    normalized_header = []
    for column in header:
        count = seen.get(column, 0)
        normalized_header.append(column if count == 0 else f"{column}_{count}")
        seen[column] = count + 1
    return [dict(zip(normalized_header, row)) for row in rows[1:]]


@dataclass
class LandingPageRow:
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
    query_pct_delta: float


@dataclass
class QueryRow:
    query: str
    clicks: float
    click_delta: float
    impressions: float
    impression_delta: float
    ctr: float
    ctr_delta: float
    avg_position: float
    position_pct_delta: float


@dataclass
class GA4Row:
    path: str
    sessions: float
    session_delta: float
    new_users: float
    new_user_delta: float
    total_users: float
    total_user_delta: float


def load_landing_pages():
    rows = []
    for record in load_csv(LP_GSC_CSV):
        rows.append(
            LandingPageRow(
                path=normalize_path(record["Landing Page"]),
                clicks=to_float(record["URL Clicks"]),
                click_delta=to_float(record["Δ"]),
                impressions=to_float(record["Impressions"]),
                impression_delta=to_float(record["Δ_1"]),
                ctr=to_float(record["URL CTR"]),
                ctr_delta=to_float(record["Δ_2"]),
                avg_position=to_float(record["Avg. Position"]),
                position_pct_delta=to_float(record["% Δ"]),
                query_count=to_float(record["Query"]),
                query_pct_delta=to_float(record["% Δ_1"]),
            )
        )
    return rows


def load_queries():
    rows = []
    for record in load_csv(QUERY_GSC_CSV):
        rows.append(
            QueryRow(
                query=record["Query"],
                clicks=to_float(record["URL Clicks"]),
                click_delta=to_float(record["Δ"]),
                impressions=to_float(record["Impressions"]),
                impression_delta=to_float(record["Δ_1"]),
                ctr=to_float(record["URL CTR"]),
                ctr_delta=to_float(record["Δ_2"]),
                avg_position=to_float(record["Average Position"]),
                position_pct_delta=to_float(record["% Δ"]),
            )
        )
    return rows


def load_ga4():
    rows = []
    for record in load_csv(LP_GA4_CSV):
        rows.append(
            GA4Row(
                path=normalize_path(record["LP & Query String"]),
                sessions=to_float(record["Sessions"]),
                session_delta=to_float(record["Δ"]),
                new_users=to_float(record["New Users"]),
                new_user_delta=to_float(record["Δ_1"]),
                total_users=to_float(record["Total Users"]),
                total_user_delta=to_float(record["Δ_2"]),
            )
        )
    return rows


def pct_change(current, delta):
    previous = current - delta
    if previous == 0:
        return 0.0
    return delta / previous


def safe_div(numerator, denominator):
    if not denominator:
        return 0.0
    return numerator / denominator


def format_pct(value):
    return f"{value * 100:.2f}%"


def format_pp(value):
    return f"{value * 100:.2f} pp"


def format_num(value):
    if math.isclose(value, round(value)):
        return f"{int(round(value)):,}"
    return f"{value:,.2f}"


def make_reopt_candidates(landing_pages, ga4_lookup):
    candidates = [
        {
            "path": "/news/what-is-hampers",
            "issue_type": "Low CTR content page",
            "why": "Already visible in search with 221 impressions and 47 ranking queries, but still 0 clicks. The topic has search visibility, but the page is not convincing users to visit.",
            "action": "Refresh the article around gifting intent and seasonal moments. Rewrite the headline and intro to answer what hampers are, when people buy them, and what makes a good hamper. Add clearer sections, practical examples, and stronger internal links from rewards, seasonal, and celebration-related pages.",
        },
        {
            "path": "/news/spanish-food",
            "issue_type": "Page 1 content with no clicks",
            "why": "Ranks in page-1 territory with average position 6.06, yet still delivered 0 clicks. This suggests the topic is relevant, but the content framing is not strong enough.",
            "action": "Rework the article to target user curiosity more directly: what Spanish food is, signature dishes to know, and where to experience it in Jakarta. Strengthen the opener, add scannable dish explanations, and connect the content to relevant dining pages so it feels more useful and complete.",
        },
        {
            "path": "/whats-on/events/union-bagel-bar-goes-to-puri",
            "issue_type": "Best-performing event content",
            "why": "This was the strongest content URL in March with organic clicks, impression growth, and session growth. It is a good template for what event content can do when search intent and page copy align.",
            "action": "Turn this into the model for future event pages. Expand the copy with clearer event context, who it is for, why it matters, and what guests can expect. Make the page useful even after launch by adding evergreen details that can still attract search demand.",
        },
        {
            "path": "/whats-on/events/a-live-session-featuring-kanda-brothers-rock-around-the-heartbreak",
            "issue_type": "Visited event page with weak search capture",
            "why": "The page generated visits in GA4 but had no matching landing-page visibility in GSC. Users are reaching it somehow, but it is not yet working as search content.",
            "action": "Strengthen the content angle so it can stand on its own in search. Add a clearer summary of the event, performer context, venue details, and audience appeal. The goal is to make the page understandable even for users who have never heard of the event before.",
        },
        {
            "path": "/news/italian-food-jakarta",
            "issue_type": "Topic article with weak organic footprint",
            "why": "The page has visits in GA4 but no clear GSC landing-page footprint in this export. That usually means the article exists, but it has not yet built enough search relevance.",
            "action": "Deepen the article so it genuinely answers the topic: what defines Italian food, popular dishes, what diners usually look for, and where the Jakarta angle fits. Use more descriptive subheadings and connect the article naturally to Roma Osteria and other relevant brand pages.",
        },
    ]
    lp_lookup = {row.path: row for row in landing_pages}
    enriched = []
    for item in candidates:
        lp = lp_lookup.get(item["path"])
        ga = ga4_lookup.get(item["path"])
        enriched.append(
            {
                **item,
                "clicks": lp.clicks if lp else 0.0,
                "click_delta": lp.click_delta if lp else 0.0,
                "impressions": lp.impressions if lp else 0.0,
                "queries": lp.query_count if lp else 0.0,
                "avg_position": lp.avg_position if lp else 0.0,
                "sessions": ga.sessions if ga else 0.0,
                "session_delta": ga.session_delta if ga else 0.0,
            }
        )
    return enriched


def build_primary_gsc_lookup(landing_pages):
    lookup = {}
    for row in landing_pages:
        existing = lookup.get(row.path)
        if existing is None:
            lookup[row.path] = row
            continue
        existing_score = (existing.clicks, existing.impressions)
        current_score = (row.clicks, row.impressions)
        if current_score > existing_score:
            lookup[row.path] = row
    return lookup


def session_insight(page, gsc_row):
    delta = int(page.session_delta)
    if delta >= 0:
        if page.path == "/brands/union":
            return (
                "This page became the main growth driver in March. More people were actively looking for Union, "
                "and this page captured that demand well."
            )
        if page.path == "/brands/union/union-pakuwon-mall":
            return (
                "Interest in the Pakuwon Mall location increased a lot in March. This page is attracting more people "
                "who are specifically searching for that outlet."
            )
        if page.path == "/":
            return (
                "The homepage brought in more visits, which usually means overall brand awareness is getting stronger. "
                "It also suggests users are now landing on the main website more consistently."
            )
        if "union-mall-kelapa-gading-3" in page.path:
            return (
                "The Mall Kelapa Gading page saw a strong lift, showing more people are discovering this specific location. "
                "There is still room to turn that visibility into even more visits."
            )
        if "union-tunjungan-plaza" in page.path:
            return (
                "The Tunjungan Plaza page performed well because the content is matching what users want. "
                "This is one of the clearest signs that location-specific demand is growing."
            )
        if "corknscrew-cc" in page.path:
            return (
                "More users are finding the Cork & Screw Country Club page through search. "
                "It is growing, but it still has room to perform better."
            )
        return (
            "This page gained more visits from search in March, which is a positive sign that visibility and interest improved."
        )

    if page.path == "/uniondeliverymenu.pdf":
        return (
            "This PDF lost visits, likely because users are moving to the main website pages instead of opening menu files directly. "
            "That is not necessarily a bad thing if traffic is shifting to better landing pages."
        )
    if page.path == "/brands/lentrecte-by-bouchon":
        return (
            "This page looks like a weak or inconsistent version of the main brand page. "
            "The drop suggests users may be landing on the wrong version or not finding the preferred page."
        )
    if "l-entrecote-by-bouchon/l-entrecote-by-bouchon-senopati" in page.path:
        return (
            "This page is losing visits and may be competing with another similar version of the same location page. "
            "That can split visibility and weaken performance."
        )
    if page.path == "/faq":
        return (
            "The FAQ page was visited less often in March. This may mean the page is less useful or less visible to users than before."
        )
    if page.path == "/contact":
        return (
            "The contact page dipped slightly, which may reflect a change in user journey rather than a major search issue. "
            "Users may be finding what they need on other pages before reaching contact."
        )
    return (
        "This page lost visits from search in March. It should be reviewed to confirm whether the drop is expected or needs action."
    )


def cell_xml(value, style_id=0):
    if value is None:
        return f'<c s="{style_id}"/>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(value) or math.isinf(value):
            value = 0
        return f'<c s="{style_id}"><v>{value}</v></c>'
    return (
        f'<c t="inlineStr" s="{style_id}"><is><t>{escape(str(value))}'
        f"</t></is></c>"
    )


def build_sheet_xml(rows):
    row_xml = []
    for index, row in enumerate(rows, start=1):
        style = 1 if index == 1 else 0
        cells = "".join(cell_xml(value, style_id=style) for value in row)
        row_xml.append(f'<row r="{index}">{cells}</row>')
    sheet_data = "".join(row_xml)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetViews><sheetView workbookViewId=\"0\"/></sheetViews>"
        "<sheetFormatPr defaultRowHeight=\"15\"/>"
        f"<sheetData>{sheet_data}</sheetData>"
        "</worksheet>"
    )


def write_workbook(sheets, output_path):
    workbook_xml = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        "<sheets>",
    ]
    workbook_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for idx, (name, _rows) in enumerate(sheets, start=1):
        workbook_xml.append(
            f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>'
        )
        workbook_rels.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    workbook_xml.extend(["</sheets>", "</workbook>"])
    workbook_rels.append(
        '<Relationship Id="rIdStyles" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_rels.append("</Relationships>")
    content_types.append("</Types>")

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFD9EAF7"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="1">
    <border><left/><right/><top/><bottom/><diagonal/></border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="1" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
  </cellXfs>
  <cellStyles count="1">
    <cellStyle name="Normal" xfId="0" builtinId="0"/>
  </cellStyles>
</styleSheet>"""

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", "\n".join(content_types))
        workbook.writestr("_rels/.rels", root_rels)
        workbook.writestr("xl/workbook.xml", "\n".join(workbook_xml))
        workbook.writestr("xl/_rels/workbook.xml.rels", "\n".join(workbook_rels))
        workbook.writestr("xl/styles.xml", styles_xml)
        for idx, (_name, rows) in enumerate(sheets, start=1):
            workbook.writestr(f"xl/worksheets/sheet{idx}.xml", build_sheet_xml(rows))


def main():
    landing_pages = load_landing_pages()
    ga4_rows = load_ga4()
    queries = load_queries()

    gsc_lookup = build_primary_gsc_lookup(landing_pages)
    ga4_lookup = {row.path: row for row in ga4_rows}
    en_landing_pages = [row for row in landing_pages if not row.path.startswith("/id")]
    en_ga4_rows = [row for row in ga4_rows if not row.path.startswith("/id") and row.path != "(not set)"]
    top_increase = sorted(en_ga4_rows, key=lambda row: row.session_delta, reverse=True)[:5]
    top_decrease = [row for row in sorted(en_ga4_rows, key=lambda row: row.session_delta) if row.session_delta < 0][:5]
    reopt_candidates = make_reopt_candidates(en_landing_pages, ga4_lookup)

    sheet_rows = [
        ["Top 5 Increase in Session", "", "", ""],
        ["No", "Pages", "Δ Sessions", "Insight"],
    ]
    for index, row in enumerate(top_increase, start=1):
        gsc_row = gsc_lookup.get(row.path)
        sheet_rows.append(
            [
                index,
                row.path,
                int(row.session_delta),
                session_insight(row, gsc_row),
            ]
        )

    sheet_rows.extend(
        [
            ["", "", "", ""],
            ["Top 5 Decrease in Session", "", "", ""],
            ["No", "Pages", "Δ Sessions", "Insight"],
        ]
    )

    for index, row in enumerate(top_decrease, start=1):
        gsc_row = gsc_lookup.get(row.path)
        sheet_rows.append(
            [
                index,
                row.path,
                int(row.session_delta),
                session_insight(row, gsc_row),
            ]
        )

    total_sessions = sum(row.sessions for row in en_ga4_rows)
    total_session_delta = sum(row.session_delta for row in en_ga4_rows)
    total_clicks = sum(row.clicks for row in en_landing_pages)
    total_click_delta = sum(row.click_delta for row in en_landing_pages)
    total_impressions = sum(row.impressions for row in en_landing_pages)
    total_impression_delta = sum(row.impression_delta for row in en_landing_pages)

    key_opportunity_page = sorted(
        [row for row in en_landing_pages if row.impressions >= 1000 and row.ctr < 0.02],
        key=lambda row: row.impressions,
        reverse=True,
    )[0]

    top_session_growth_summary = ", ".join(
        f"`{row.path}` ({'+' if row.session_delta >= 0 else ''}{int(row.session_delta)})"
        for row in top_increase
    )
    top_session_decline_summary = ", ".join(
        f"`{row.path}` ({int(row.session_delta)})"
        for row in top_decrease
    )

    summary_rows = [
        ["The Union Group · SEO Monthly Report · March 2026"],
        ["Client: The Union Group  |  Prepared by: Antikode Analytics  |  Period: March 2026"],
        [],
        ["📌  Executive Summary"],
        [
            "Biggest Growth Driver",
            f"The Union brand hub and nearby location pages drove the strongest lift in March. `/brands/union` added +{format_num(top_increase[0].session_delta)} sessions, supported by strong gains from Pakuwon Mall, Mall Kelapa Gading 3, and Tunjungan Plaza.",
            "🟢 Positive",
        ],
        [
            "Biggest Decline Risk",
            "A few declining URLs look more like outdated or overlapping page issues than true demand loss. The clearest examples are the menu PDF and the L'Entrecote slug variants, where traffic may be split across weaker URL versions.",
            "🔴 Critical",
        ],
        [
            "Key Opportunity",
            f"`{key_opportunity_page.path}` already earned {format_num(key_opportunity_page.impressions)} impressions in March but only {format_pct(key_opportunity_page.ctr)} CTR. The page is being seen often, but users are not convinced to click yet.",
            "🟡 Action",
        ],
        [
            "Content Opportunity",
            "The site's content layer is still relatively thin. Several article and event pages already show either early search visibility or on-site visits, which means stronger content work could turn them into meaningful traffic drivers.",
            "🟡 Action",
        ],
        [
            "Recommendation Focus",
            "The best next move is content-led reoptimisation: stronger article framing, clearer intros, more useful subheadings, and tighter links from relevant brand and location pages.",
            "🟣 Content",
        ],
        [],
        ["🎙  Slide Narrative"],
        [
            f"March 2026 was a strong month for The Union Group's English pages. Organic sessions reached {format_num(total_sessions)} and clicks reached {format_num(total_clicks)}, with growth led by the Union brand hub and several Union location pages. This shows that brand and location demand is rising. At the same time, content depth is still lagging behind search opportunity. Brand pages are visible, but some are not converting impressions into visits efficiently, while article and event pages need stronger content framing to become reliable traffic drivers. The clearest April opportunity is to improve a focused set of pages through content refreshes rather than broad technical changes."
        ],
    ]

    reopt_rows = [
        ["🔧  Reoptimisation Candidates — March 2026"],
        ["URL", "Issue Type", "Opportunity", "Recommended Action"],
    ]
    for row in reopt_candidates:
        reopt_rows.append(
            [
                row["path"],
                row["issue_type"],
                row["why"],
                row["action"],
            ]
        )
    reopt_rows.extend(
        [
            [],
            ["ℹ  Note: Recommendations are content-led and focused on English pages only while Indonesian pages are paused."],
        ]
    )

    write_workbook(
        [
            ("March 2026", sheet_rows),
            ("📋 Summary", summary_rows),
            ("🔧 Reoptimisation", reopt_rows),
        ],
        OUTPUT_XLSX,
    )

    md_lines = [
        "# The Union Group SEO Monthly Insight Report",
        "",
        "Period: March 2026",
        "",
        "Scope note: the session mover breakdown below focuses on English pages only. `/id/` URLs were excluded from the action layer as requested.",
        "",
        "## Executive Summary",
        "",
        f"- Organic sessions across English landing pages reached **{format_num(total_sessions)}**, up **{format_num(total_session_delta)}** month over month ({format_pct(pct_change(total_sessions, total_session_delta))}).",
        f"- Organic clicks across English landing pages reached **{format_num(total_clicks)}**, up **{format_num(total_click_delta)}** month over month ({format_pct(pct_change(total_clicks, total_click_delta))}).",
        f"- Biggest session increases were {top_session_growth_summary}.",
        f"- Biggest session decreases were {top_session_decline_summary}.",
        "",
        "## Top 5 Increase in Session",
        "",
    ]
    for index, row in enumerate(top_increase, start=1):
        gsc_row = gsc_lookup.get(row.path)
        click_text = (
            f", GSC clicks {'+' if gsc_row.click_delta >= 0 else ''}{format_num(gsc_row.click_delta)}"
            if gsc_row
            else ""
        )
        md_lines.append(
            f"{index}. `{row.path}`: {'+' if row.session_delta >= 0 else ''}{int(row.session_delta)} sessions{click_text}. {session_insight(row, gsc_row)}"
        )

    md_lines.extend(["", "## Top 5 Decrease in Session", ""])
    for index, row in enumerate(top_decrease, start=1):
        gsc_row = gsc_lookup.get(row.path)
        click_text = (
            f", GSC clicks {'+' if gsc_row.click_delta >= 0 else ''}{format_num(gsc_row.click_delta)}"
            if gsc_row
            else ""
        )
        md_lines.append(
            f"{index}. `{row.path}`: {int(row.session_delta)} sessions{click_text}. {session_insight(row, gsc_row)}"
        )

    md_lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Session ranking is based on the March 2026 GA4 landing-page export.",
            "- Insight commentary uses the March 2026 GSC landing-page export as supporting context where available.",
            "- Some declining URLs are legacy or file-based assets, so the drop may reflect healthy migration or content consolidation rather than a new SEO issue.",
            "",
            "## Summary",
            "",
            f"- Biggest growth driver: Union brand and location pages, led by `/brands/union` with +{int(top_increase[0].session_delta)} sessions.",
            "- Biggest decline risk: outdated or overlapping URLs, especially the menu PDF path and the L'Entrecote variants.",
            f"- Key opportunity: `{key_opportunity_page.path}` has high visibility ({format_num(key_opportunity_page.impressions)} impressions) but low click-through ({format_pct(key_opportunity_page.ctr)} CTR).",
            "- Content opportunity: article and event pages already show early traction, but need stronger framing and depth to grow organically.",
            f"- March totals: {format_num(total_sessions)} sessions, {format_num(total_session_delta)} session growth, {format_num(total_clicks)} clicks, {format_num(total_click_delta)} click growth, and {format_num(total_impressions)} impressions (+{format_num(total_impression_delta)}).",
            "",
            "## Reoptimisation Candidates",
            "",
        ]
    )

    for row in reopt_candidates:
        md_lines.extend(
            [
                f"### {row['path']}",
                f"- Issue type: {row['issue_type']}",
                f"- Opportunity: {row['why']}",
                f"- Recommended action: {row['action']}",
                "",
            ]
        )

    OUTPUT_MD.write_text("\n".join(md_lines))


if __name__ == "__main__":
    main()
