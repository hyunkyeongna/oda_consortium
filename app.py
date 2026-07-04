"""
ODA Consortium Intelligence — executive dashboard
Run: streamlit run app.py
"""
from __future__ import annotations

import os
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

import graph_view as GV
import pipeline as P
import ui
from demo_data import COMPONENTS, DEMO_BID, FIELD_PARTNERS

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
PARTNER_DB_DIR = os.path.join(BASE_DIR, "partner_db")

# -----------------------------------------------------------------------------
# English presentation layer
# -----------------------------------------------------------------------------
PROJECT = {
    "title": "Sri Lanka Northern & Northwestern Mangrove Ecosystem Restoration and Capacity Building",
    "subtitle": "AI-supported consortium design for a KOICA ecosystem restoration, GIS, livelihood, infrastructure, procurement, and training package.",
    "country": "Sri Lanka",
    "budget": "KRW 16.56B",
    "period": "2026–2030",
    "buyer": "KOICA",
}

COMPONENT_META = {
    "C1": {
        "name": "ICT-based Integrated Management Plan",
        "sector": "Forestry / ICT",
        "desc": "Drone, GIS, and remote-sensing based mangrove mapping, management planning, and survey manuals.",
    },
    "C2": {
        "name": "Mangrove Nursery and Restoration",
        "sector": "Forestry / Environment",
        "desc": "Nursery development, planting, degraded-site restoration, and post-restoration maintenance.",
    },
    "C3": {
        "name": "Mangrove-based Aquaculture and Livelihood",
        "sector": "Fisheries / Agriculture",
        "desc": "Integrated mangrove-shrimp aquaculture model and alternative income generation for local communities.",
    },
    "C4": {
        "name": "Mangrove Training Center Infrastructure",
        "sector": "Architecture / Infrastructure",
        "desc": "Construction of a 1,141㎡ training center and renovation of a 390㎡ information facility.",
    },
    "C5": {
        "name": "Equipment and Procurement Package",
        "sector": "Procurement",
        "desc": "Laboratory and survey equipment, drones, vehicles, and IT equipment procurement.",
    },
    "C6": {
        "name": "Capacity Building and Training",
        "sector": "Education / Capacity Building",
        "desc": "Government official training, local workshops, learning modules, and public-awareness materials.",
    },
}

FIELD_TYPE_MAP = {
    "수원국 정부": "Recipient government",
    "현지 학계": "Local university",
    "현지 NGO": "Local NGO",
    "국제기구": "International organization",
    "다자개발은행": "Multilateral development bank",
}

FIELD_NAME_MAP = {
    "산림보전국(DoFC)": "Department of Forest Conservation (DoFC)",
    "야생동물보전국(DoWC)": "Department of Wildlife Conservation (DoWC)",
    "Wayamba University": "Wayamba University",
    "Wildlife & Nature Protection Society": "Wildlife & Nature Protection Society",
    "Sudeesa": "Sudeesa",
    "NAQDA(양식개발청)": "National Aquaculture Development Authority (NAQDA)",
    "GGGI": "GGGI",
    "UNEP": "UNEP",
    "ADB": "ADB",
}

FIELD_ROLE_MAP = {
    "산림보전국(DoFC)": "Restoration governance and protected-area management.",
    "야생동물보전국(DoWC)": "Protected areas and biodiversity coordination.",
    "Wayamba University": "Mangrove research, field surveys, and technical validation.",
    "Wildlife & Nature Protection Society": "Restoration pilots and site-level monitoring.",
    "Sudeesa": "Community-based restoration, livelihood support, and microfinance linkage.",
    "NAQDA(양식개발청)": "Aquaculture pilot design and technical implementation.",
    "GGGI": "Household livelihood, value-chain, and baseline survey linkage.",
    "UNEP": "Ecosystem restoration agenda and international finance linkage.",
    "ADB": "Infrastructure linkage around the Vankalai exhibition and outreach facility.",
}

PAGE_DESCRIPTIONS = {
    "Overview": "Executive view of project scope, partner intelligence, and consortium readiness.",
    "01 · Bid decomposition": "Review the AI-generated component structure and required capability stack.",
    "02 · Domestic matching": "Rank domestic candidates by capability evidence and role fit.",
    "03 · Host-country partners": "Map recipient-country, local, and multilateral stakeholders.",
    "04 · Partner graph": "Explore relationships across components, candidates, field actors, and co-delivery history.",
    "05 · Consortium": "Review a role-balanced consortium package and scoring rationale.",
}


def bid_get(*keys: str, default: Any = "") -> Any:
    for k in keys:
        if isinstance(DEMO_BID, dict) and k in DEMO_BID and DEMO_BID[k] not in (None, ""):
            return DEMO_BID[k]
    return default


BID_COUNTRY_KO = bid_get("country_ko", "country", "수원국", default="스리랑카")

st.set_page_config(
    page_title="ODA Consortium Intelligence",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(ui.inject(), unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load():
    return P.load_data(DATA_DIR, partner_db_dir=PARTNER_DB_DIR)


@st.cache_data(show_spinner=False)
def compute():
    d = load()
    partner_db = d.get("partner_db", {})
    rec, total, bd = P.recommend_consortium(
        COMPONENTS,
        d.get("humanitarian"),
        d.get("nonprofit"),
        FIELD_PARTNERS,
        recipient_country=BID_COUNTRY_KO,
        partner_db=partner_db,
    )
    edges = P.co_implementation_edges(d.get("humanitarian"), partner_db=partner_db)
    sl, sectors, partners = P.iati_country_footprint(d.get("iati"), BID_COUNTRY_KO)
    return d, rec, total, bd, edges, sl, sectors, partners


d, rec, total, bd, coedges, sl, sectors, mult_partners = compute()
partner_db = d.get("partner_db", {})
partner_db_on = P.partner_db_available(partner_db)
partner_count = len(partner_db.get("summary", [])) if partner_db_on else len(d.get("nonprofit", []))
capability_count = len(partner_db.get("capabilities", [])) if partner_db_on else 0
procurement_rows = len(partner_db.get("procurement", [])) if isinstance(partner_db, dict) else 0
edge_count = len(coedges)
required_map = {
    str(c.get("id", "")): [r["capability_tag"] for r in P.infer_required_capabilities(c)]
    for c in COMPONENTS
}

# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="brand"><span class="mark"></span>ODA Consortium<br>Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Navigate</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        list(PAGE_DESCRIPTIONS.keys()),
        label_visibility="collapsed",
    )
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">System status</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="side-card">
  <div class="statline"><span>Nara / KOICA pipeline</span><b>CONNECTED</b></div>
  <div class="statline"><span>Partner Master DB</span><b>{'ACTIVE' if partner_db_on else 'READY'}</b></div>
  <div class="statline"><span>Partners indexed</span><b>{partner_count:,}</b></div>
  <div class="statline"><span>Capability signals</span><b>{capability_count:,}</b></div>
  <div class="statline"><span>Procurement records</span><b>{procurement_rows:,}</b></div>
  <div class="statline"><span>Co-delivery links</span><b>{edge_count:,}</b></div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown(ui.page_header("Consortium Command Center", PAGE_DESCRIPTIONS.get(page, "")), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Overview
# -----------------------------------------------------------------------------
if page == "Overview":
    st.markdown(
        ui.hero_dashboard(
            PROJECT["title"],
            PROJECT["subtitle"],
            PROJECT["country"],
            PROJECT["budget"],
            PROJECT["period"],
            PROJECT["buyer"],
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        ui.kpi_grid(
            [
                ("Components", len(COMPONENTS), "work packages identified"),
                ("Sri Lanka footprint", len(sl), "KOICA country records"),
                ("Partner pool", f"{partner_count:,}", "indexed candidate organizations"),
                ("Readiness score", f"{total}", "composite consortium score"),
            ]
        ),
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1.45, 1])
    with c1:
        st.markdown(ui.section("Operating model", "From bid document to consortium strategy", "The system decomposes scope, matches role-specific partners, and assembles an evidence-based delivery structure."), unsafe_allow_html=True)
        st.markdown(ui.workflow_cards(), unsafe_allow_html=True)
    with c2:
        st.markdown(ui.section("Data stack", "Connected intelligence layers", "Public-sector procurement, project records, registration data, and field-partner evidence are integrated into one matching layer."), unsafe_allow_html=True)
        st.markdown(
            """
<div class="card" style="line-height:1.95;">
  <span class="pill pill-real">Connected</span> KOICA procurement and project records<br>
  <span class="pill pill-real">Connected</span> Nara contract and award pipeline<br>
  <span class="pill pill-real">Connected</span> Partner Master DB and capability index<br>
  <span class="pill pill-real">Connected</span> Recipient-country stakeholder cards<br>
  <span class="pill pill-track">Next</span> PQ eligibility and JV history scoring
</div>
""",
            unsafe_allow_html=True,
        )

# -----------------------------------------------------------------------------
# 01 Bid decomposition
# -----------------------------------------------------------------------------
elif page.startswith("01"):
    st.markdown(ui.section("Step 01", "Bid decomposition", "Scope is split into work packages, each translated into a required capability stack for partner matching."), unsafe_allow_html=True)
    st.markdown(ui.component_cards(COMPONENTS, COMPONENT_META, required_map), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 02 Domestic matching
# -----------------------------------------------------------------------------
elif page.startswith("02"):
    st.markdown(ui.section("Step 02", "Domestic partner matching", "Candidates are ranked by capability fit, project evidence, source coverage, and role suitability."), unsafe_allow_html=True)
    tabs = st.tabs([COMPONENT_META.get(c.get("id"), {}).get("name", c.get("name", "Component")) for c in COMPONENTS])
    for tab, c in zip(tabs, COMPONENTS):
        with tab:
            cid = str(c.get("id", ""))
            req_pills = " ".join(f'<span class="pill pill-track">{ui.cap_label(x)}</span>' for x in required_map.get(cid, []))
            st.markdown(f"<div style='margin-bottom:10px;'>{req_pills}</div>", unsafe_allow_html=True)
            m = P.match_domestic(
                c,
                d.get("humanitarian"),
                d.get("nonprofit"),
                recipient_country=BID_COUNTRY_KO,
                partner_db=partner_db,
            )
            st.markdown(ui.match_list(m), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 03 Host-country partners
# -----------------------------------------------------------------------------
elif page.startswith("03"):
    st.markdown(ui.section("Step 03", "Host-country partner discovery", "Recipient-country and multilateral actors are surfaced against the component structure."), unsafe_allow_html=True)
    st.markdown(
        ui.kpi_grid(
            [
                ("Country records", len(sl), "Sri Lanka project footprint"),
                ("Active sectors", sectors.shape[0], "distinct sector categories"),
                ("Multilaterals", len(mult_partners), "identified from project titles"),
                ("Field actors", len(FIELD_PARTNERS), "linked to components"),
            ]
        ),
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.markdown(ui.section("Country footprint", "Sector distribution"), unsafe_allow_html=True)
        st.markdown(ui.sector_bars(sectors), unsafe_allow_html=True)
    with c2:
        if mult_partners:
            pills = " ".join(f'<span class="pill pill-intl">{ui.clean_text(k)}</span>' for k in mult_partners)
            st.markdown(ui.section("Multilateral signals", "Organizations detected"), unsafe_allow_html=True)
            st.markdown(f'<div class="card">{pills}</div>', unsafe_allow_html=True)
        st.markdown(ui.section("Field linkage", "Government, local, and multilateral partners"), unsafe_allow_html=True)
        st.markdown(ui.partner_cards(FIELD_PARTNERS, FIELD_TYPE_MAP, FIELD_NAME_MAP, FIELD_ROLE_MAP), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 04 Partner graph
# -----------------------------------------------------------------------------
elif page.startswith("04"):
    st.markdown(ui.section("Step 04", "Partner ecosystem graph", "Graph view of the bid, components, domestic candidates, field actors, and co-delivery links."), unsafe_allow_html=True)
    graph_bid = {"사업명": PROJECT["title"], "수원국": PROJECT["country"], "예산_백만원": "16,560"}
    G = GV.build_graph(graph_bid, COMPONENTS, rec, FIELD_PARTNERS, coedges, component_meta=COMPONENT_META, field_name_map=FIELD_NAME_MAP)
    st.markdown(
        ui.kpi_grid(
            [
                ("Nodes", G.number_of_nodes(), "actors and components"),
                ("Links", G.number_of_edges(), "relationships"),
                ("Co-delivery", len(coedges), "partner relationship signals"),
                ("Candidate layers", 4, "domestic, field, MDB, IO"),
            ]
        ),
        unsafe_allow_html=True,
    )
    legend = "".join(f'<span><b style="background:{c}"></b>{n}</span>' for n, c in GV.LEGEND)
    st.markdown(f'<div class="legend">{legend}</div>', unsafe_allow_html=True)
    components.html(GV.render_html(G), height=620)
    if coedges:
        st.markdown(ui.section("Relationship evidence", "Co-delivery links"), unsafe_allow_html=True)
        rows = "".join(
            f'<div class="match"><div class="body"><div class="org">{ui.clean_text(a)} &harr; {ui.clean_text(b)}</div>'
            f'<div class="ev">{ui.clean_text(proj, 180)}</div></div></div>'
            for a, b, proj in coedges[:12]
        )
        st.markdown(f'<div class="card">{rows}</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 05 Consortium
# -----------------------------------------------------------------------------
elif page.startswith("05"):
    st.markdown(ui.section("Step 05", "Consortium recommendation", "Component-level partner combination and composite scoring rationale."), unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.6])
    with c1:
        st.markdown(
            f'<div class="card" style="text-align:center;padding:26px;"><div class="eyebrow">Composite readiness</div><div class="gauge">{total}<small>/100</small></div><div class="ev">Role coverage, domestic fit, and field linkage.</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        bars = ""
        label_map = {
            "분야 커버리지(40)": "Component coverage (40)",
            "국내 매칭 강도(30)": "Domestic fit strength (30)",
            "현지 연계(30)": "Field linkage (30)",
        }
        for k, v in bd.items():
            label = label_map.get(k, ui.clean_text(k))
            cap = 40 if "40" in label else 30
            w = int(round(float(v) / cap * 100)) if cap else 0
            bars += f"""<div style="margin-bottom:10px;">
              <div style="display:flex;justify-content:space-between;font-size:13px;">
                <span>{label}</span><span class="mono" style="font-weight:800;">{v}</span></div>
              <div class="bar" style="height:9px;"><i style="width:{w}%"></i></div></div>"""
        st.markdown(f'<div class="card">{bars}</div>', unsafe_allow_html=True)

    st.markdown(ui.section("Recommended delivery structure", "Component-level consortium package"), unsafe_allow_html=True)
    for r in rec:
        st.markdown(
            ui.rec_row(
                r["component"],
                r.get("domestic") or r.get("국내후보"),
                r.get("field") or r.get("현지파트너"),
                component_meta=COMPONENT_META,
                field_name_map=FIELD_NAME_MAP,
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        """
<div class="card" style="margin-top:10px;">
  <div class="eyebrow">Implementation note</div>
  <div class="ev">Final award strategy should validate PQ eligibility, local registration requirements, construction licensing, and formal joint-venture constraints before outreach.</div>
</div>
""",
        unsafe_allow_html=True,
    )
