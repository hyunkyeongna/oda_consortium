"""
ODA Consortium Intelligence — demo (KOICA Sri Lanka mangrove bid)
Run: streamlit run app.py

Patched version:
- Uses Partner Master DB from ./partner_db when available.
- Fixes DEMO_BID Korean/English key mismatch.
- Fixes recommendation key mismatch: domestic/field and 국내후보/현지파트너 are both supported.
"""

from __future__ import annotations

import os
import inspect

import streamlit as st
import streamlit.components.v1 as components

import graph_view as GV
import pipeline as P
import ui
from demo_data import COMPONENTS, DEMO_BID, FIELD_PARTNERS

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
PARTNER_DB_DIR = os.path.join(BASE_DIR, "partner_db")

st.set_page_config(
    page_title="ODA Consortium Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(ui.inject(), unsafe_allow_html=True)


def bid_get(*keys, default=""):
    """Support both old English keys and current Korean keys in demo_data.py."""
    for k in keys:
        if isinstance(DEMO_BID, dict) and k in DEMO_BID and DEMO_BID[k] not in (None, ""):
            return DEMO_BID[k]
    return default


BID_COUNTRY = bid_get("country_ko", "country", "수원국", default="스리랑카")
BID_TITLE = bid_get("title_ko", "사업명", default="ODA Project")


def _load_partner_db_safely():
    """Cloud-safe loader: works even if Streamlit Cloud has an older pipeline.py."""
    try:
        if hasattr(P, "load_partner_db"):
            return P.load_partner_db(PARTNER_DB_DIR)
    except Exception:
        pass
    return {}


@st.cache_data(show_spinner=False)
def load():
    try:
        params = inspect.signature(P.load_data).parameters
        if "partner_db_dir" in params:
            return P.load_data(DATA_DIR, partner_db_dir=PARTNER_DB_DIR)
    except Exception:
        pass

    # Backward-compatible path for older pipeline.py
    d = P.load_data(DATA_DIR)
    if isinstance(d, dict) and "partner_db" not in d:
        d["partner_db"] = _load_partner_db_safely()
    return d


@st.cache_data(show_spinner=False)
def compute():
    d = load()
    partner_db = d.get("partner_db", {}) if isinstance(d, dict) else {}

    try:
        rec, total, bd = P.recommend_consortium(
            COMPONENTS,
            d.get("humanitarian"),
            d.get("nonprofit"),
            FIELD_PARTNERS,
            recipient_country=BID_COUNTRY,
            partner_db=partner_db,
        )
    except TypeError:
        # Older pipeline.py without Partner Master DB support
        rec, total, bd = P.recommend_consortium(
            COMPONENTS,
            d.get("humanitarian"),
            d.get("nonprofit"),
            FIELD_PARTNERS,
            recipient_country=BID_COUNTRY,
        )

    try:
        edges = P.co_implementation_edges(d.get("humanitarian"), partner_db=partner_db)
    except TypeError:
        edges = P.co_implementation_edges(d.get("humanitarian"))

    sl, sectors, partners = P.iati_country_footprint(d.get("iati"), BID_COUNTRY)
    return d, rec, total, bd, edges, sl, sectors, partners


d, rec, total, bd, coedges, sl, sectors, mult_partners = compute()
partner_db = d.get("partner_db", {}) if isinstance(d, dict) else {}
try:
    partner_db_on = P.partner_db_available(partner_db)
except Exception:
    partner_db_on = bool(partner_db)
partner_count = len(partner_db.get("summary", [])) if partner_db_on and isinstance(partner_db, dict) else 0
capability_count = len(partner_db.get("capabilities", [])) if partner_db_on and isinstance(partner_db, dict) else 0


def get_key():
    try:
        return st.secrets.get("DATA_GO_KR_SERVICE_KEY", "")
    except Exception:
        return ""


key = get_key()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="mark"></span>ODA Consortium<br>Intelligence</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="eyebrow" style="margin-top:14px;">Navigate</div>', unsafe_allow_html=True)
    page = st.radio(
        "nav",
        [
            "Overview",
            "01 · Bid decomposition",
            "02 · Domestic matching",
            "03 · Host-country partners",
            "04 · Partner graph",
            "05 · Consortium",
        ],
        label_visibility="collapsed",
    )
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Data status</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
      <div class="statline"><span>Nara / KOICA API</span><b>{'LIVE' if key else 'DEMO'}</b></div>
      <div class="statline"><span>Partner Master DB</span><b>{'ON' if partner_db_on else 'OFF'}</b></div>
      <div class="statline"><span>Partners</span><b>{partner_count:,}</b></div>
      <div class="statline"><span>Capabilities</span><b>{capability_count:,}</b></div>
      <div class="statline"><span>IATI projects</span><b>{len(d.get('iati', [])):,}</b></div>
      <div class="statline"><span>NPO registry</span><b>{len(d.get('nonprofit', [])):,}</b></div>
      <div class="statline"><span>Track record</span><b>{len(d.get('humanitarian', [])):,}</b></div>
    """,
        unsafe_allow_html=True,
    )

# ---------------- Overview ----------------
if page == "Overview":
    st.markdown(ui.hero(DEMO_BID), unsafe_allow_html=True)
    st.markdown(
        ui.kpi_grid(
            [
                ("Components", len(COMPONENTS), "decomposed from bid"),
                (f"{BID_COUNTRY} projects", len(sl), "KOICA footprint (IATI)"),
                ("Partner pool", f"{partner_count:,}" if partner_db_on else f"{len(d.get('nonprofit', [])):,}", "Partner Master DB" if partner_db_on else "NPO registry"),
                ("Consortium score", f"{total}", "out of 100"),
            ]
        ),
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1.3, 1])
    with c1:
        st.markdown(
            ui.section(
                "Pipeline",
                "Bid to consortium in five steps",
                "Each step is evidence-backed where data exists, and clearly flagged where evidence is weak.",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            """<div class="card">
          <div class="match"><div class="rank">01</div><div class="body"><div class="org">Bid decomposition</div>
            <div class="ev">Ingest a Nara-Jangteo / KOICA notice, split into components</div></div></div>
          <div class="match"><div class="rank">02</div><div class="body"><div class="org">Partner Master matching</div>
            <div class="ev">Rank Korean orgs by capability tags + track record + registry evidence</div></div></div>
          <div class="match"><div class="rank">03</div><div class="body"><div class="org">Host-country partners</div>
            <div class="ev">Surface in-country and multilateral actors</div></div></div>
          <div class="match"><div class="rank">04</div><div class="body"><div class="org">Partner graph</div>
            <div class="ev">Weave a network incl. real co-delivery history when available</div></div></div>
          <div class="match"><div class="rank">05</div><div class="body"><div class="org">Consortium recommendation</div>
            <div class="ev">Assemble and score a defensible combination</div></div></div>
        </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(ui.section("Sources", "Data", ""), unsafe_allow_html=True)
        st.markdown(
            f"""<div class="card" style="font-size:13px;line-height:1.9;">
          <span class="pill {'pill-real' if partner_db_on else 'pill-mock'}">{'Live' if partner_db_on else 'Missing'}</span> Partner Master DB<br>
          <span class="pill pill-real">Live</span> KOICA IATI · National NPO registry · KOICA track record<br>
          <span class="pill {'pill-real' if key else 'pill-mock'}">{'Live' if key else 'Demo'}</span> Nara-Jangteo / KOICA procurement API<br>
          <span class="pill pill-mock">Mock</span> Field-partner cards from bid document<br>
          <span class="pill pill-mock">Mock</span> OECD CRS / WB / ADB not yet acquired
        </div>""",
            unsafe_allow_html=True,
        )

# ---------------- 01 Bid decomposition ----------------
elif page.startswith("01"):
    st.markdown(
        ui.section(
            "Step 01",
            "Bid decomposition",
            "In production a Nara-Jangteo notice is ingested and split by NLP. Demo: parsed from the execution plan.",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<span class="pill {"pill-real" if key else "pill-mock"}">'
        f'{"API connected — live ingest available" if key else "Demo mode — add serviceKey for live ingest"}'
        f"</span>",
        unsafe_allow_html=True,
    )
    st.write("")
    cells = ""
    for c in COMPONENTS:
        required = P.infer_required_capabilities(c)
        req_txt = ", ".join([x["capability_tag"] for x in required[:3]])
        cells += f"""<div class="pcard">
          <div style="font-family:'IBM Plex Mono';font-size:11px;color:var(--primary);font-weight:600;">{c['id']}</div>
          <div class="pname" style="margin-top:2px;">{c['name']}</div>
          <span class="pill pill-track">{c['sector']}</span>
          <div class="prole">{c['desc']}</div>
          <div class="pcomp">Required capability: {req_txt}</div>
        </div>"""
    st.markdown(f'<div class="pcard-grid">{cells}</div>', unsafe_allow_html=True)

# ---------------- 02 Domestic matching ----------------
elif page.startswith("02"):
    st.markdown(
        ui.section(
            "Step 02",
            "Domestic partner matching",
            "Each component is matched against the Partner Master DB. Score = capability fit + evidence count + recency + source credibility.",
        ),
        unsafe_allow_html=True,
    )
    tabs = st.tabs([c["name"] for c in COMPONENTS])
    for tab, c in zip(tabs, COMPONENTS):
        with tab:
            required = P.infer_required_capabilities(c)
            req_pills = " ".join(
                f'<span class="pill pill-track">{r["capability_tag"]}</span>' for r in required
            )
            st.markdown(f"<div style='margin-bottom:10px;'>{req_pills}</div>", unsafe_allow_html=True)
            m = P.match_domestic(
                c,
                d.get("humanitarian"),
                d.get("nonprofit"),
                recipient_country=BID_COUNTRY,
                partner_db=partner_db,
            )
            st.markdown(ui.match_list(m), unsafe_allow_html=True)

# ---------------- 03 Host-country partners ----------------
elif page.startswith("03"):
    st.markdown(
        ui.section(
            "Step 03",
            "Host-country partner discovery",
            "What generic bid tools cannot do: show what is actually running in the recipient country.",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        ui.kpi_grid(
            [
                (f"{BID_COUNTRY} projects", len(sl), "KOICA (IATI)"),
                ("Sectors active", sectors.shape[0], "distinct fields"),
                ("Multilaterals found", len(mult_partners), "parsed from titles"),
                ("Field partners", len(FIELD_PARTNERS), "named in bid doc"),
            ]
        ),
        unsafe_allow_html=True,
    )
    st.markdown('<div class="eyebrow" style="margin-top:10px;">Sector footprint</div>', unsafe_allow_html=True)
    st.markdown(ui.sector_bars(sectors), unsafe_allow_html=True)
    if mult_partners:
        pills = " ".join(f'<span class="pill pill-intl">{k}</span>' for k in mult_partners)
        st.markdown(f'<div style="margin:2px 0 14px;">Parsed from project titles: {pills}</div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Field and multilateral partners</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    st.markdown(ui.partner_cards(FIELD_PARTNERS), unsafe_allow_html=True)

# ---------------- 04 Partner graph ----------------
elif page.startswith("04"):
    st.markdown(
        ui.section(
            "Step 04",
            "Partner ecosystem graph",
            "Bid to components to domestic / field / multilateral. Red = verified co-delivery history where available.",
        ),
        unsafe_allow_html=True,
    )
    G = GV.build_graph(DEMO_BID, COMPONENTS, rec, FIELD_PARTNERS, coedges)
    st.markdown(
        ui.kpi_grid(
            [
                ("Nodes", G.number_of_nodes(), "actors + components"),
                ("Links", G.number_of_edges(), "relationships"),
                ("Co-delivery", len(coedges), "verified partnerships"),
            ]
        ),
        unsafe_allow_html=True,
    )
    legend = "".join(f'<span><b style="background:{c}"></b>{n}</span>' for n, c in GV.LEGEND)
    st.markdown(f'<div class="legend">{legend}</div>', unsafe_allow_html=True)
    components.html(GV.render_html(G), height=640)
    if coedges:
        st.markdown('<div class="eyebrow">Verified co-delivery</div>', unsafe_allow_html=True)
        rows = "".join(
            f'<div class="match"><div class="body"><div class="org">{a} &harr; {b}</div>'
            f'<div class="ev">{proj}</div></div></div>'
            for a, b, proj in coedges
        )
        st.markdown(f'<div class="card">{rows}</div>', unsafe_allow_html=True)

# ---------------- 05 Consortium ----------------
elif page.startswith("05"):
    st.markdown(
        ui.section(
            "Step 05",
            "Consortium recommendation",
            "Component-level combination with a composite score. Weights are demo values.",
        ),
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1, 1.6])
    with c1:
        st.markdown(
            f'<div class="card" style="text-align:center;padding:26px;">'
            f'<div class="eyebrow">Composite score</div>'
            f'<div class="gauge">{total}<small>/100</small></div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        bars = ""
        for k, v in bd.items():
            cap = float(k.split("(")[-1].rstrip(")"))
            w = int(round(v / cap * 100)) if cap else 0
            bars += f"""<div style="margin-bottom:10px;">
              <div style="display:flex;justify-content:space-between;font-size:13px;">
                <span>{k}</span><span class="mono" style="font-weight:600;">{v}</span></div>
              <div class="bar" style="height:9px;"><i style="width:{w}%"></i></div></div>"""
        st.markdown(f'<div class="card">{bars}</div>', unsafe_allow_html=True)

    st.markdown('<div class="eyebrow" style="margin-top:6px;">Recommended combination</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    for r in rec:
        st.markdown(ui.rec_row(r["component"], r.get("domestic") or r.get("국내후보"), r.get("field") or r.get("현지파트너")), unsafe_allow_html=True)

    st.caption(
        "Scoring weights and keywords are demo values. Production should refine with KOICA procurement, Nara contract, PQ eligibility, and joint-venture history."
    )
