"""
UI helpers for ODA Consortium Intelligence Streamlit app.
Keep this file in the same directory as app.py.
"""
from __future__ import annotations

import html
from typing import Any, Iterable

import pandas as pd


def _e(x: Any) -> str:
    """HTML-escape a value for safe rendering."""
    if x is None:
        return ""
    return html.escape(str(x), quote=True)


def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def inject() -> str:
    """Global CSS injection."""
    return """
<style>
:root{
  --bg:#f8fafc;
  --card:#ffffff;
  --text:#0f172a;
  --muted:#64748b;
  --line:#e2e8f0;
  --primary:#2563eb;
  --primary-soft:#eff6ff;
  --green:#10b981;
  --amber:#f59e0b;
  --violet:#8b5cf6;
  --red:#ef4444;
  --slate:#334155;
}
.block-container{padding-top:1.3rem; padding-bottom:2rem; max-width:1280px;}
section[data-testid="stSidebar"]{background:#0f172a;}
section[data-testid="stSidebar"] *{color:#e5e7eb !important;}
section[data-testid="stSidebar"] hr{border-color:rgba(255,255,255,.12);}
.brand{font-size:21px; font-weight:800; line-height:1.15; letter-spacing:-.02em; color:#fff;}
.mark{display:inline-block; width:12px; height:12px; border-radius:4px; background:#3b82f6; margin-right:8px; vertical-align:1px;}
.eyebrow{font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:.08em; color:#64748b; margin-bottom:8px;}
.card{background:var(--card); border:1px solid var(--line); border-radius:18px; padding:18px; box-shadow:0 1px 2px rgba(15,23,42,.04);}
.hero{background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 55%,#2563eb 100%); color:#fff; border-radius:24px; padding:30px 34px; margin-bottom:18px; box-shadow:0 12px 30px rgba(37,99,235,.22);}
.hero .label{font-size:12px; font-weight:800; letter-spacing:.1em; text-transform:uppercase; opacity:.8;}
.hero h1{font-size:34px; line-height:1.15; margin:8px 0 10px; letter-spacing:-.03em; color:#fff;}
.hero p{font-size:15px; opacity:.88; max-width:850px; margin:0;}
.meta{display:flex; flex-wrap:wrap; gap:8px; margin-top:18px;}
.meta span{background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.16); padding:7px 10px; border-radius:999px; font-size:12px;}
.kpi-grid{display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:14px 0 18px;}
.kpi{background:#fff; border:1px solid var(--line); border-radius:18px; padding:16px;}
.kpi .name{font-size:12px; color:var(--muted); font-weight:700;}
.kpi .value{font-size:25px; font-weight:850; color:var(--text); margin-top:4px; letter-spacing:-.02em;}
.kpi .sub{font-size:12px; color:var(--muted); margin-top:2px;}
.section{margin:12px 0 12px;}
.section h2{font-size:24px; letter-spacing:-.025em; margin:0 0 4px; color:#0f172a;}
.section .over{font-size:12px; font-weight:850; text-transform:uppercase; letter-spacing:.08em; color:var(--primary); margin-bottom:4px;}
.section p{font-size:14px; color:var(--muted); margin:0;}
.pill{display:inline-block; border-radius:999px; padding:4px 8px; font-size:11px; font-weight:750; margin:2px 3px 2px 0; border:1px solid transparent; vertical-align:middle;}
.pill-real{background:#ecfdf5; color:#047857; border-color:#a7f3d0;}
.pill-mock{background:#fff7ed; color:#c2410c; border-color:#fed7aa;}
.pill-track{background:#eff6ff; color:#1d4ed8; border-color:#bfdbfe;}
.pill-intl{background:#f5f3ff; color:#6d28d9; border-color:#ddd6fe;}
.statline{display:flex; justify-content:space-between; align-items:center; gap:12px; font-size:12px; padding:8px 0; border-bottom:1px solid rgba(255,255,255,.09);}
.statline span{color:#cbd5e1 !important;}
.statline b{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; color:#fff !important;}
.match{display:flex; gap:12px; padding:13px 0; border-bottom:1px solid var(--line);}
.match:last-child{border-bottom:0; padding-bottom:0;}
.rank{flex:0 0 34px; width:34px; height:34px; border-radius:12px; background:var(--primary-soft); color:var(--primary); display:flex; align-items:center; justify-content:center; font-weight:850; font-size:12px;}
.body{flex:1; min-width:0;}
.org{font-size:15px; color:var(--text); font-weight:850; margin-bottom:3px;}
.ev{font-size:12px; color:var(--muted); line-height:1.45;}
.score{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; font-size:12px; font-weight:800; color:#0f172a;}
.pcard-grid{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px;}
.pcard{background:#fff; border:1px solid var(--line); border-radius:18px; padding:16px; min-height:166px;}
.pname{font-weight:850; font-size:16px; color:#0f172a; line-height:1.35; margin-bottom:8px;}
.prole{font-size:13px; color:#475569; line-height:1.5; margin:10px 0;}
.pcomp{font-size:12px; color:#64748b; line-height:1.45;}
.bar{background:#e2e8f0; height:10px; border-radius:999px; overflow:hidden;}
.bar i{display:block; height:100%; background:#2563eb; border-radius:999px;}
.sector-row{display:grid; grid-template-columns:170px 1fr 48px; align-items:center; gap:10px; margin:9px 0;}
.sector-name{font-size:12px; color:#334155; font-weight:750; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.sector-val{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; font-size:12px; color:#475569; text-align:right;}
.partner-grid{display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px;}
.partner-card{background:#fff; border:1px solid var(--line); border-radius:18px; padding:15px; min-height:138px;}
.partner-card .ptype{font-size:11px; color:#64748b; font-weight:800; text-transform:uppercase; letter-spacing:.04em;}
.partner-card .pname2{font-size:15px; color:#0f172a; font-weight:850; margin:5px 0;}
.partner-card .role{font-size:12px; color:#475569; line-height:1.45;}
.rec{display:grid; grid-template-columns:1fr 1.1fr 1fr; gap:12px; align-items:stretch; margin-bottom:12px;}
.rec .box{background:#fff; border:1px solid var(--line); border-radius:18px; padding:15px;}
.rec-title{font-weight:850; color:#0f172a; font-size:15px; margin-bottom:6px;}
.gauge{font-size:54px; font-weight:900; color:#2563eb; letter-spacing:-.06em;}
.gauge small{font-size:18px; color:#64748b; letter-spacing:0;}
.legend{display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin:8px 0 12px; font-size:12px; color:#475569;}
.legend span{display:inline-flex; align-items:center; gap:6px;}
.legend b{display:inline-block; width:10px; height:10px; border-radius:999px;}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;}
@media (max-width: 900px){.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.pcard-grid{grid-template-columns:1fr;}.partner-grid{grid-template-columns:1fr 1fr;}.rec{grid-template-columns:1fr;}}
</style>
"""


def hero(bid: dict[str, Any]) -> str:
    title = bid.get("사업명") or bid.get("title_ko") or bid.get("name") or "ODA Project"
    title_en = bid.get("사업명_영문") or bid.get("title_en") or ""
    country = bid.get("수원국") or bid.get("country") or ""
    budget = bid.get("예산_백만원") or bid.get("budget_million_krw") or ""
    period = bid.get("기간") or bid.get("period") or ""
    buyer = bid.get("발주") or bid.get("buyer") or ""
    budget_txt = f"{int(float(budget)):,}백만원" if str(budget).strip() not in ("", "nan") else "Budget N/A"
    return f"""
<div class="hero">
  <div class="label">ODA Consortium Intelligence</div>
  <h1>{_e(title)}</h1>
  <p>{_e(title_en)}</p>
  <div class="meta">
    <span>Country: {_e(country)}</span>
    <span>Budget: {_e(budget_txt)}</span>
    <span>Period: {_e(period)}</span>
    <span>Buyer: {_e(buyer)}</span>
  </div>
</div>
"""


def kpi_grid(items: Iterable[tuple[Any, Any, Any]]) -> str:
    cells = []
    for name, value, sub in items:
        cells.append(
            f"""<div class="kpi">
  <div class="name">{_e(name)}</div>
  <div class="value">{_e(value)}</div>
  <div class="sub">{_e(sub)}</div>
</div>"""
        )
    return f'<div class="kpi-grid">{"".join(cells)}</div>'


def section(overline: str, title: str, desc: str = "") -> str:
    return f"""
<div class="section">
  <div class="over">{_e(overline)}</div>
  <h2>{_e(title)}</h2>
  {f'<p>{_e(desc)}</p>' if desc else ''}
</div>
"""


def _get(row: Any, *keys: str, default: Any = "") -> Any:
    if isinstance(row, dict):
        for k in keys:
            if k in row and row[k] not in (None, ""):
                return row[k]
        return default
    for k in keys:
        try:
            v = row.get(k, None)
            if v not in (None, ""):
                return v
        except Exception:
            pass
    return default


def match_list(df: Any, max_items: int = 8) -> str:
    """Render domestic matching results from either pandas DataFrame or list[dict]."""
    if df is None:
        return '<div class="card"><div class="ev">No matching partners found.</div></div>'

    if isinstance(df, pd.DataFrame):
        rows = df.to_dict("records")
    elif isinstance(df, list):
        rows = df
    else:
        try:
            rows = list(df)
        except Exception:
            rows = []

    if not rows:
        return '<div class="card"><div class="ev">No matching partners found.</div></div>'

    html_rows = []
    for i, r in enumerate(rows[:max_items], start=1):
        org = _get(r, "기관", "partner_name", "canonical_name_ko", "name_ko", "org", default="Unknown partner")
        score = _get(r, "점수", "score", "match_score", default="")
        source = _get(r, "출처", "source", "source_name", default="")
        reason = _get(r, "근거", "evidence", "evidence_summary", "reason", default="")
        role = _get(r, "suggested_role", "role", default="")
        score_txt = f"Score {_num(score):.1f}" if str(score).strip() not in ("", "nan") else ""
        meta = " · ".join([x for x in [source, role, score_txt] if x])
        html_rows.append(
            f"""<div class="match">
  <div class="rank">{i:02d}</div>
  <div class="body">
    <div style="display:flex;justify-content:space-between;gap:8px;"><div class="org">{_e(org)}</div><div class="score">{_e(score_txt)}</div></div>
    <div class="ev">{_e(meta)}</div>
    <div class="ev">{_e(reason)}</div>
  </div>
</div>"""
        )
    return f'<div class="card">{"".join(html_rows)}</div>'


def sector_bars(sectors: Any, max_items: int = 10) -> str:
    if sectors is None or len(sectors) == 0:
        return '<div class="card"><div class="ev">No sector footprint available.</div></div>'
    try:
        items = list(sectors.head(max_items).items())
        max_val = max([int(v) for _, v in items] or [1])
    except Exception:
        return '<div class="card"><div class="ev">No sector footprint available.</div></div>'

    rows = []
    for name, val in items:
        width = int((_num(val) / max_val) * 100) if max_val else 0
        rows.append(
            f"""<div class="sector-row">
  <div class="sector-name" title="{_e(name)}">{_e(name)}</div>
  <div class="bar"><i style="width:{width}%"></i></div>
  <div class="sector-val">{_e(val)}</div>
</div>"""
        )
    return f'<div class="card">{"".join(rows)}</div>'


def partner_cards(partners: list[dict[str, Any]]) -> str:
    if not partners:
        return '<div class="card"><div class="ev">No field partners available.</div></div>'
    cells = []
    for p in partners:
        comps = ", ".join(p.get("components", []) or [])
        ptype = p.get("type", "")
        name = p.get("name", "")
        role = p.get("role", "")
        cells.append(
            f"""<div class="partner-card">
  <div class="ptype">{_e(ptype)}</div>
  <div class="pname2">{_e(name)}</div>
  <div class="role">{_e(role)}</div>
  <div style="margin-top:8px;"><span class="pill pill-track">{_e(comps)}</span></div>
</div>"""
        )
    return f'<div class="partner-grid">{"".join(cells)}</div>'


def rec_row(component: dict[str, Any], domestic: Any, field: Any) -> str:
    cname = component.get("name", "")
    csector = component.get("sector", "")
    cdesc = component.get("desc", component.get("description", ""))

    if isinstance(domestic, dict):
        dname = domestic.get("기관") or domestic.get("partner_name") or domestic.get("canonical_name_ko") or "No domestic match"
        dscore = domestic.get("점수") or domestic.get("score") or domestic.get("match_score") or ""
        dreason = domestic.get("근거") or domestic.get("evidence_summary") or domestic.get("evidence") or ""
        dsrc = domestic.get("출처") or domestic.get("source") or ""
        dmeta = " · ".join([x for x in [dsrc, f"score {_num(dscore):.1f}" if str(dscore).strip() else ""] if x])
    elif domestic:
        dname, dmeta, dreason = str(domestic), "", ""
    else:
        dname, dmeta, dreason = "No domestic match", "", "Evidence insufficient"

    if isinstance(field, list):
        ftxt = "".join(f'<span class="pill pill-intl">{_e(x)}</span>' for x in field) or "No field partner"
    elif field:
        ftxt = _e(field)
    else:
        ftxt = "No field partner"

    return f"""
<div class="rec">
  <div class="box">
    <div class="eyebrow">Component</div>
    <div class="rec-title">{_e(cname)}</div>
    <span class="pill pill-track">{_e(csector)}</span>
    <div class="ev" style="margin-top:8px;">{_e(cdesc)}</div>
  </div>
  <div class="box">
    <div class="eyebrow">Domestic recommendation</div>
    <div class="rec-title">{_e(dname)}</div>
    <div class="ev">{_e(dmeta)}</div>
    <div class="ev" style="margin-top:6px;">{_e(dreason)}</div>
  </div>
  <div class="box">
    <div class="eyebrow">Field / multilateral linkage</div>
    <div>{ftxt}</div>
  </div>
</div>
"""
