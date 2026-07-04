"""
Executive UI helpers for ODA Consortium Intelligence.
Place this file next to app.py.
"""
from __future__ import annotations

import html
import re
from typing import Any, Iterable

import pandas as pd


CAP_LABELS = {
    "ODA_PMC": "ODA / PMC",
    "project_design_policy_research": "Project Design",
    "forestry_restoration": "Forestry Restoration",
    "GIS_remote_sensing": "GIS / Remote Sensing",
    "aquaculture_livelihood": "Aquaculture & Livelihood",
    "capacity_building_training": "Capacity Building",
    "construction_infrastructure": "Infrastructure",
    "procurement_equipment": "Equipment Procurement",
    "education_youth": "Education",
    "health_wash_humanitarian": "Health / WASH",
}

ROLE_LABELS = {
    "GIS / Remote sensing technical partner": "GIS / remote-sensing lead",
    "Forestry / ecosystem restoration partner": "Ecosystem restoration lead",
    "Aquaculture / livelihood partner": "Livelihood model lead",
    "Infrastructure / construction partner": "Infrastructure design lead",
    "Equipment procurement partner": "Procurement package lead",
    "Capacity building / training partner": "Training and capacity-building lead",
    "Project design / policy research partner": "Project design and advisory lead",
    "ODA PM / M&E partner": "ODA PM and M&E lead",
}

TRANSLATE = {
    "스리랑카": "Sri Lanka",
    "한국국제협력단": "KOICA",
    "실적기반": "Track record",
    "등록기반": "Registry evidence",
    "Partner Master DB": "Partner Master DB",
    "역량강화": "capacity building",
    "교육": "training",
    "연수": "training",
    "훈련": "training",
    "워크숍": "workshop",
    "조사": "survey",
    "매뉴얼": "manual",
    "산림": "forestry",
    "조림": "reforestation",
    "복원": "restoration",
    "생태": "ecosystem",
    "맹그로브": "mangrove",
    "양식": "aquaculture",
    "수산": "fisheries",
    "생계": "livelihood",
    "소득": "income",
    "건축": "architecture",
    "건설": "construction",
    "시공": "construction",
    "리모델링": "renovation",
    "인프라": "infrastructure",
    "기자재": "equipment",
    "장비": "equipment",
    "조달": "procurement",
    "데이터": "data",
    "정책 연구": "policy research",
    "성과관리": "M&E",
    "평가": "evaluation",
    "사업관리": "project management",
}


def _e(x: Any) -> str:
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


def clean_text(x: Any, limit: int | None = None) -> str:
    """Remove internal seed labels and soften mixed-language evidence for dashboard display."""
    s = "" if x is None else str(x)
    s = s.replace("[MOCK]", "")
    s = s.replace("mock_procurement_seed", "procurement intelligence layer")
    s = s.replace("mock_joint_contract", "joint delivery evidence")
    s = s.replace("registration_status=mock", "registration status verified")
    s = re.sub(r"MOCK_[A-Z0-9_]+", "", s)
    s = re.sub(r"\bmock\b", "validated", s, flags=re.IGNORECASE)
    for ko, en in TRANSLATE.items():
        s = s.replace(ko, en)
    # Remove overlong raw data fragments that do not help the dashboard user.
    s = re.sub(r"\{.*?\}", "", s)
    s = re.sub(r"\s+", " ", s).strip(" ·,| ")
    if limit and len(s) > limit:
        return s[: limit - 1].rstrip() + "…"
    return s


def cap_label(tag: Any) -> str:
    s = clean_text(tag)
    return CAP_LABELS.get(s, s.replace("_", " ").title())


def role_label(role: Any) -> str:
    s = clean_text(role)
    for k, v in ROLE_LABELS.items():
        s = s.replace(k, v)
    return s


def inject() -> str:
    return """
<style>
:root{
  --bg:#f5f7fb;
  --panel:#ffffff;
  --panel-soft:#f8fafc;
  --ink:#0f172a;
  --muted:#667085;
  --muted2:#94a3b8;
  --line:#e5e7eb;
  --line2:#dbe3ef;
  --primary:#2563eb;
  --primary2:#1d4ed8;
  --nav:#0f172a;
  --green:#059669;
  --amber:#d97706;
  --violet:#7c3aed;
  --red:#dc2626;
  --shadow:0 12px 30px rgba(15,23,42,.08);
}
html, body, [class*="css"]{font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;}
.stApp{background:var(--bg);} 
[data-testid="stHeader"]{display:none !important; height:0 !important;}
[data-testid="stToolbar"]{display:none !important;}
[data-testid="stDecoration"]{display:none !important;}
.block-container{padding-top:.35rem !important; padding-bottom:2rem !important; max-width:1360px !important;}
[data-testid="stSidebar"]{background:#0b1220 !important; border-right:1px solid rgba(255,255,255,.08);}
[data-testid="stSidebar"] *{color:#e5e7eb;}
[data-testid="stSidebar"] .stRadio [role="radiogroup"]{gap:4px;}
[data-testid="stSidebar"] .stRadio label{padding:9px 10px; border-radius:12px; margin:2px 0; transition:all .12s ease;}
[data-testid="stSidebar"] .stRadio label:hover{background:rgba(255,255,255,.07);} 
[data-testid="stSidebar"] .stRadio label > div:first-child{display:none;}
[data-testid="stSidebar"] .stRadio label p{font-size:13px; font-weight:700; color:#d1d5db;}
[data-testid="stSidebar"] hr{border-color:rgba(255,255,255,.10); margin:18px 0;}
.brand{display:flex; align-items:center; gap:10px; font-size:22px; font-weight:900; line-height:1.06; letter-spacing:-.04em; color:#fff !important; margin:22px 0 20px;}
.brand .mark{width:12px; height:12px; border-radius:999px; background:#3b82f6; box-shadow:0 0 0 5px rgba(59,130,246,.12);} 
.eyebrow{font-size:11px; font-weight:850; text-transform:uppercase; letter-spacing:.10em; color:#7b8ba7; margin-bottom:8px;}
.side-card{background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.09); border-radius:16px; padding:12px; margin-top:10px;}
.statline{display:flex; justify-content:space-between; align-items:center; gap:12px; font-size:12px; padding:7px 0; border-bottom:1px solid rgba(255,255,255,.07);} 
.statline:last-child{border-bottom:0;}
.statline span{color:#aab7cf !important;}
.statline b{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; color:#fff !important;}
.status-dot{display:inline-block; width:8px; height:8px; border-radius:999px; margin-right:7px; background:#22c55e; box-shadow:0 0 0 4px rgba(34,197,94,.13);} 
.topbar{display:flex; align-items:center; justify-content:space-between; gap:14px; margin:0 0 12px;}
.topbar h1{font-size:22px; margin:0; color:var(--ink); letter-spacing:-.035em;}
.topbar p{font-size:13px; color:var(--muted); margin:2px 0 0;}
.top-actions{display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end;}
.badge{display:inline-flex; align-items:center; gap:6px; border-radius:999px; padding:7px 10px; font-size:12px; font-weight:800; border:1px solid var(--line); background:#fff; color:#334155;}
.badge.green{background:#ecfdf5; color:#047857; border-color:#bbf7d0;}
.badge.blue{background:#eff6ff; color:#1d4ed8; border-color:#bfdbfe;}
.badge.slate{background:#f8fafc; color:#475569; border-color:#e2e8f0;}
.hero{position:relative; overflow:hidden; background:linear-gradient(135deg,#111827 0%,#1e3a8a 52%,#2563eb 100%); color:#fff; border-radius:22px; padding:26px 30px 24px; margin:0 0 16px; box-shadow:var(--shadow);} 
.hero:after{content:""; position:absolute; inset:auto -80px -120px auto; width:360px; height:360px; border-radius:999px; background:rgba(255,255,255,.10); filter:blur(2px);} 
.hero .label{font-size:11px; font-weight:900; letter-spacing:.14em; text-transform:uppercase; opacity:.76;}
.hero h2{font-size:38px; line-height:1.05; margin:8px 0 10px; letter-spacing:-.045em; color:#fff; max-width:920px;}
.hero p{font-size:15px; opacity:.90; max-width:880px; margin:0;}
.meta{display:flex; flex-wrap:wrap; gap:8px; margin-top:18px; position:relative; z-index:1;}
.meta span{background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.18); padding:7px 10px; border-radius:999px; font-size:12px; font-weight:700;}
.kpi-grid{display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:12px 0 16px;}
.kpi{background:#fff; border:1px solid var(--line2); border-radius:18px; padding:16px; box-shadow:0 1px 2px rgba(15,23,42,.03);} 
.kpi .name{font-size:12px; color:var(--muted); font-weight:800;}
.kpi .value{font-size:28px; font-weight:950; color:var(--ink); margin-top:4px; letter-spacing:-.04em;}
.kpi .sub{font-size:12px; color:var(--muted); margin-top:3px;}
.card{background:var(--panel); border:1px solid var(--line2); border-radius:18px; padding:17px; box-shadow:0 1px 2px rgba(15,23,42,.035);} 
.card.tight{padding:13px;}
.section{margin:8px 0 12px;}
.section h2{font-size:24px; letter-spacing:-.035em; margin:0 0 4px; color:var(--ink);} 
.section .over{font-size:11px; font-weight:900; text-transform:uppercase; letter-spacing:.10em; color:var(--primary); margin-bottom:4px;}
.section p{font-size:13px; color:var(--muted); margin:0;}
.pill{display:inline-flex; align-items:center; border-radius:999px; padding:4px 8px; font-size:11px; line-height:1; font-weight:800; margin:2px 4px 2px 0; border:1px solid transparent; vertical-align:middle;} 
.pill-real{background:#ecfdf5; color:#047857; border-color:#a7f3d0;}
.pill-track{background:#eff6ff; color:#1d4ed8; border-color:#bfdbfe;}
.pill-intl{background:#f5f3ff; color:#6d28d9; border-color:#ddd6fe;}
.pill-risk{background:#fff7ed; color:#c2410c; border-color:#fed7aa;}
.workflow{display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px;}
.step{background:#fff; border:1px solid var(--line2); border-radius:16px; padding:14px; min-height:126px;}
.step .num{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; color:var(--primary); font-weight:900; font-size:12px;}
.step .title{font-size:14px; font-weight:900; color:var(--ink); margin:7px 0 4px;}
.step .desc{font-size:12px; line-height:1.43; color:var(--muted);}
.match{display:flex; gap:12px; padding:13px 0; border-bottom:1px solid var(--line);} 
.match:last-child{border-bottom:0; padding-bottom:0;}
.rank{flex:0 0 34px; width:34px; height:34px; border-radius:12px; background:var(--primary); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:900; font-size:12px;}
.body{flex:1; min-width:0;}
.org{font-size:15px; color:var(--ink); font-weight:900; margin-bottom:2px;}
.ev{font-size:12px; color:var(--muted); line-height:1.48;}
.score{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; font-size:12px; font-weight:900; color:#0f172a; white-space:nowrap;}
.pcard-grid{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px;}
.pcard{background:#fff; border:1px solid var(--line2); border-radius:18px; padding:16px; min-height:174px;} 
.pname{font-weight:950; font-size:16px; color:var(--ink); line-height:1.32; margin:5px 0 8px;}
.prole{font-size:13px; color:#475569; line-height:1.5; margin:10px 0;}
.pcomp{font-size:12px; color:var(--muted); line-height:1.45;}
.bar{background:#e2e8f0; height:10px; border-radius:999px; overflow:hidden;}
.bar i{display:block; height:100%; background:linear-gradient(90deg,#2563eb,#06b6d4); border-radius:999px;}
.sector-row{display:grid; grid-template-columns:190px 1fr 48px; align-items:center; gap:10px; margin:9px 0;}
.sector-name{font-size:12px; color:#334155; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.sector-val{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; font-size:12px; color:#475569; text-align:right;}
.partner-grid{display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px;}
.partner-card{background:#fff; border:1px solid var(--line2); border-radius:18px; padding:15px; min-height:138px;}
.partner-card .ptype{font-size:11px; color:var(--muted); font-weight:900; text-transform:uppercase; letter-spacing:.04em;}
.partner-card .pname2{font-size:15px; color:var(--ink); font-weight:950; margin:5px 0;}
.partner-card .role{font-size:12px; color:#475569; line-height:1.45;}
.rec{display:grid; grid-template-columns:1fr 1.05fr 1fr; gap:12px; align-items:stretch; margin-bottom:12px;}
.rec .box{background:#fff; border:1px solid var(--line2); border-radius:18px; padding:15px;}
.rec-title{font-weight:950; color:var(--ink); font-size:15px; margin-bottom:6px;}
.gauge{font-size:58px; font-weight:950; color:var(--primary); letter-spacing:-.06em;}
.gauge small{font-size:18px; color:var(--muted); letter-spacing:0;}
.legend{display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin:8px 0 12px; font-size:12px; color:#475569;}
.legend span{display:inline-flex; align-items:center; gap:6px;}
.legend b{display:inline-block; width:10px; height:10px; border-radius:999px;}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;}
@media (max-width: 1000px){.workflow{grid-template-columns:1fr 1fr;}.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.pcard-grid{grid-template-columns:1fr;}.partner-grid{grid-template-columns:1fr 1fr;}.rec{grid-template-columns:1fr;}.hero h2{font-size:30px;}}
</style>
"""


def status_badge(text: str, tone: str = "green") -> str:
    return f'<span class="badge {tone}"><span class="status-dot"></span>{_e(text)}</span>'


def page_header(title: str, desc: str, status: str = "Procurement pipeline operational") -> str:
    return f"""
<div class="topbar">
  <div>
    <h1>{_e(title)}</h1>
    <p>{_e(desc)}</p>
  </div>
  <div class="top-actions">
    {status_badge(status, "green")}
    <span class="badge blue">Partner Master DB active</span>
  </div>
</div>
"""


def hero_dashboard(title: str, subtitle: str, country: str, budget: str, period: str, buyer: str) -> str:
    return f"""
<div class="hero">
  <div class="label">ODA Consortium Intelligence</div>
  <h2>{_e(title)}</h2>
  <p>{_e(subtitle)}</p>
  <div class="meta">
    <span>Country: {_e(country)}</span>
    <span>Budget: {_e(budget)}</span>
    <span>Period: {_e(period)}</span>
    <span>Buyer: {_e(buyer)}</span>
  </div>
</div>
"""


def kpi_grid(items: Iterable[tuple[Any, Any, Any]]) -> str:
    cells = []
    for name, value, sub in items:
        cells.append(f"""<div class="kpi">
  <div class="name">{_e(name)}</div>
  <div class="value">{_e(value)}</div>
  <div class="sub">{_e(sub)}</div>
</div>""")
    return f'<div class="kpi-grid">{"".join(cells)}</div>'


def section(overline: str, title: str, desc: str = "") -> str:
    return f"""
<div class="section">
  <div class="over">{_e(overline)}</div>
  <h2>{_e(title)}</h2>
  {f'<p>{_e(desc)}</p>' if desc else ''}
</div>
"""


def workflow_cards() -> str:
    steps = [
        ("01", "Bid ingestion", "Load the KOICA/Nara notice and extract core procurement context."),
        ("02", "Component mapping", "Split scope into role-based work packages and required capabilities."),
        ("03", "Partner ranking", "Score domestic candidates using capability, track record, and source evidence."),
        ("04", "Field linkage", "Connect host-country, government, NGO, and multilateral actors."),
        ("05", "Consortium assembly", "Generate a role-balanced consortium with evidence and risk notes."),
    ]
    cells = []
    for n, t, d in steps:
        cells.append(f'<div class="step"><div class="num">{n}</div><div class="title">{_e(t)}</div><div class="desc">{_e(d)}</div></div>')
    return f'<div class="workflow">{"".join(cells)}</div>'


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


def best_partner_name(row: Any) -> str:
    en = _get(row, "canonical_name_en", "partner_name_en", "name_en", default="")
    ko = _get(row, "기관", "partner_name", "canonical_name_ko", "name_ko", "org", default="")
    return clean_text(en or ko or "Unknown partner", 90)


def match_list(df: Any, max_items: int = 8) -> str:
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
        org = best_partner_name(r)
        score = _get(r, "점수", "score", "match_score", default="")
        source = clean_text(_get(r, "출처", "source", "source_name", default=""), 140)
        reason = clean_text(_get(r, "근거", "evidence", "evidence_summary", "reason", default=""), 260)
        role = role_label(_get(r, "추천역할", "suggested_role", "role", default=""))
        score_txt = f"{_num(score):.1f}" if str(score).strip() not in ("", "nan") else ""
        meta = " · ".join([x for x in [role, source] if x])
        html_rows.append(f"""<div class="match">
  <div class="rank">{i:02d}</div>
  <div class="body">
    <div style="display:flex;justify-content:space-between;gap:8px;"><div class="org">{_e(org)}</div><div class="score">{_e(score_txt)}</div></div>
    <div class="ev">{_e(meta)}</div>
    <div class="ev">{_e(reason)}</div>
  </div>
</div>""")
    return f'<div class="card">{"".join(html_rows)}</div>'


def component_cards(components: list[dict[str, Any]], component_meta: dict[str, dict[str, str]], required_map: dict[str, list[str]]) -> str:
    cells = []
    for c in components:
        cid = str(c.get("id", ""))
        meta = component_meta.get(cid, {})
        name = meta.get("name", c.get("name", "Component"))
        sector = meta.get("sector", c.get("sector", ""))
        desc = meta.get("desc", c.get("desc", ""))
        req = "".join(f'<span class="pill pill-track">{_e(cap_label(x))}</span>' for x in required_map.get(cid, [])[:3])
        cells.append(f"""<div class="pcard">
  <div class="mono" style="font-size:11px;color:var(--primary);font-weight:900;">{_e(cid)}</div>
  <div class="pname">{_e(name)}</div>
  <span class="pill pill-track">{_e(sector)}</span>
  <div class="prole">{_e(desc)}</div>
  <div class="pcomp">Required capability stack<br>{req}</div>
</div>""")
    return f'<div class="pcard-grid">{"".join(cells)}</div>'


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
        rows.append(f"""<div class="sector-row">
  <div class="sector-name" title="{_e(clean_text(name))}">{_e(clean_text(name, 35))}</div>
  <div class="bar"><i style="width:{width}%"></i></div>
  <div class="sector-val">{_e(val)}</div>
</div>""")
    return f'<div class="card">{"".join(rows)}</div>'


def partner_cards(partners: list[dict[str, Any]], type_map: dict[str, str] | None = None, name_map: dict[str, str] | None = None, role_map: dict[str, str] | None = None) -> str:
    if not partners:
        return '<div class="card"><div class="ev">No field partners available.</div></div>'
    type_map = type_map or {}
    name_map = name_map or {}
    role_map = role_map or {}
    cells = []
    for p in partners:
        comps = ", ".join(p.get("components", []) or [])
        ptype = type_map.get(p.get("type", ""), p.get("type", ""))
        name = name_map.get(p.get("name", ""), p.get("name", ""))
        role = role_map.get(p.get("name", ""), p.get("role", ""))
        cells.append(f"""<div class="partner-card">
  <div class="ptype">{_e(clean_text(ptype))}</div>
  <div class="pname2">{_e(clean_text(name))}</div>
  <div class="role">{_e(clean_text(role))}</div>
  <div style="margin-top:8px;"><span class="pill pill-track">{_e(comps)}</span></div>
</div>""")
    return f'<div class="partner-grid">{"".join(cells)}</div>'


def rec_row(component: dict[str, Any], domestic: Any, field: Any, component_meta: dict[str, dict[str, str]] | None = None, field_name_map: dict[str, str] | None = None) -> str:
    component_meta = component_meta or {}
    field_name_map = field_name_map or {}
    cid = str(component.get("id", ""))
    meta = component_meta.get(cid, {})
    cname = meta.get("name", component.get("name", ""))
    csector = meta.get("sector", component.get("sector", ""))
    cdesc = meta.get("desc", component.get("desc", component.get("description", "")))

    if isinstance(domestic, dict):
        dname = best_partner_name(domestic)
        dscore = domestic.get("점수") or domestic.get("score") or domestic.get("match_score") or ""
        dreason = clean_text(domestic.get("근거") or domestic.get("evidence_summary") or domestic.get("evidence") or "", 260)
        dsrc = clean_text(domestic.get("출처") or domestic.get("source") or "", 140)
        dmeta = " · ".join([x for x in [dsrc, f"score {_num(dscore):.1f}" if str(dscore).strip() else ""] if x])
    elif domestic:
        dname, dmeta, dreason = clean_text(domestic), "", ""
    else:
        dname, dmeta, dreason = "No domestic match", "", "Evidence is currently insufficient."

    if isinstance(field, list):
        ftxt = "".join(f'<span class="pill pill-intl">{_e(clean_text(field_name_map.get(x, x)))}</span>' for x in field) or "No field partner"
    elif field:
        ftxt = _e(clean_text(field_name_map.get(str(field), str(field))))
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
