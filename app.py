"""
ODA Consortium Intelligence — demo (KOICA Sri Lanka mangrove bid)
Run:  streamlit run app.py
"""
import os
import streamlit as st
import streamlit.components.v1 as components

import pipeline as P
import graph_view as GV
import ui
from demo_data import DEMO_BID, COMPONENTS, FIELD_PARTNERS

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
st.set_page_config(page_title="ODA Consortium Intelligence", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(ui.inject(), unsafe_allow_html=True)


@st.cache_data
def load():
    return P.load_data(DATA_DIR)


@st.cache_data
def compute():
    d = load()
    rec, total, bd = P.recommend_consortium(COMPONENTS, d["humanitarian"], d["nonprofit"], FIELD_PARTNERS)
    edges = P.co_implementation_edges(d["humanitarian"])
    sl, sectors, partners = P.iati_country_footprint(d["iati"], DEMO_BID["country_ko"])
    return d, rec, total, bd, edges, sl, sectors, partners


d, rec, total, bd, coedges, sl, sectors, mult_partners = compute()


def get_key():
    try:
        return st.secrets.get("DATA_GO_KR_SERVICE_KEY", "")
    except Exception:
        return ""


key = get_key()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown('<div class="brand"><span class="mark"></span>ODA Consortium<br>Intelligence</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="eyebrow" style="margin-top:14px;">Navigate</div>', unsafe_allow_html=True)
    page = st.radio("nav", [
        "Overview",
        "01 · Bid decomposition",
        "02 · Domestic matching",
        "03 · Host-country partners",
        "04 · Partner graph",
        "05 · Consortium",
    ], label_visibility="collapsed")
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Data status</div>', unsafe_allow_html=True)
    st.markdown(f"""
      <div class="statline"><span>Nara / KOICA API</span><b>{'LIVE' if key else 'DEMO'}</b></div>
      <div class="statline"><span>IATI projects</span><b>{len(d['iati']):,}</b></div>
      <div class="statline"><span>NPO registry</span><b>{len(d['nonprofit']):,}</b></div>
      <div class="statline"><span>Track record</span><b>{len(d['humanitarian'])}</b></div>
    """, unsafe_allow_html=True)

# ---------------- Overview ----------------
if page == "Overview":
    st.markdown(ui.hero(DEMO_BID), unsafe_allow_html=True)
    st.markdown(ui.kpi_grid([
        ("Components", len(COMPONENTS), "decomposed from bid"),
        (f"{DEMO_BID['country']} projects", len(sl), "KOICA footprint (IATI)"),
        ("Domestic pool", f"{len(d['nonprofit']):,}", "non-profits + track record"),
        ("Consortium score", f"{total}", "out of 100"),
    ]), unsafe_allow_html=True)
    c1, c2 = st.columns([1.3, 1])
    with c1:
        st.markdown(ui.section("Pipeline", "Bid to consortium in five steps",
                    "Each step is data-backed where the data exists, and clearly flagged where it is a mockup."),
                    unsafe_allow_html=True)
        st.markdown("""<div class="card">
          <div class="match"><div class="rank">01</div><div class="body"><div class="org">Bid decomposition</div>
            <div class="ev">Ingest a Nara-Jangteo / KOICA notice, split into components</div></div></div>
          <div class="match"><div class="rank">02</div><div class="body"><div class="org">Domestic matching</div>
            <div class="ev">Rank Korean orgs by track record + registry relevance</div></div></div>
          <div class="match"><div class="rank">03</div><div class="body"><div class="org">Host-country partners</div>
            <div class="ev">Surface in-country and multilateral actors (IATI)</div></div></div>
          <div class="match"><div class="rank">04</div><div class="body"><div class="org">Partner graph</div>
            <div class="ev">Weave a network incl. real co-delivery history</div></div></div>
          <div class="match"><div class="rank">05</div><div class="body"><div class="org">Consortium recommendation</div>
            <div class="ev">Assemble and score a defensible combination</div></div></div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(ui.section("Sources", "Data", ""), unsafe_allow_html=True)
        st.markdown("""<div class="card" style="font-size:13px;line-height:1.9;">
          <span class="pill pill-real">Live</span> KOICA IATI · National NPO registry · KOICA track record<br>
          <span class="pill pill-real">Live</span> Nara-Jangteo / KOICA procurement API <i>(key)</i><br>
          <span class="pill pill-mock">Mock</span> Field-partner cards (from bid document)<br>
          <span class="pill pill-mock">Mock</span> OECD CRS / WB / ADB <i>(not yet acquired)</i>
        </div>""", unsafe_allow_html=True)

# ---------------- 01 Bid decomposition ----------------
elif page.startswith("01"):
    st.markdown(ui.section("Step 01", "Bid decomposition",
                "In production a Nara-Jangteo notice is ingested and split by NLP. Demo: parsed from the execution plan."),
                unsafe_allow_html=True)
    st.markdown(f'<span class="pill {"pill-real" if key else "pill-mock"}">'
                f'{"API connected — live ingest available" if key else "Demo mode — add serviceKey for live ingest"}'
                f'</span>', unsafe_allow_html=True)
    st.write("")
    cells = ""
    for c in COMPONENTS:
        cells += f"""<div class="pcard">
          <div style="font-family:'IBM Plex Mono';font-size:11px;color:var(--primary);font-weight:600;">{c['id']}</div>
          <div class="pname" style="margin-top:2px;">{c['name']}</div>
          <span class="pill pill-track">{c['sector']}</span>
          <div class="prole">{c['desc']}</div>
          <div class="pcomp">{len(c['keywords'])} matching keywords</div>
        </div>"""
    st.markdown(f'<div class="pcard-grid">{cells}</div>', unsafe_allow_html=True)

# ---------------- 02 Domestic matching ----------------
elif page.startswith("02"):
    st.markdown(ui.section("Step 02", "Domestic partner matching",
                "Each component is matched against KOICA track record + the national non-profit registry. "
                "Score = keyword fit + track-record / registering-ministry weight."),
                unsafe_allow_html=True)
    tabs = st.tabs([c["name"] for c in COMPONENTS])
    for tab, c in zip(tabs, COMPONENTS):
        with tab:
            m = P.match_domestic(c, d["humanitarian"], d["nonprofit"])
            st.markdown(ui.match_list(m), unsafe_allow_html=True)

# ---------------- 03 Host-country partners ----------------
elif page.startswith("03"):
    st.markdown(ui.section("Step 03", "Host-country partner discovery",
                "What generic bid tools cannot do: show what is actually running in the recipient country (IATI, live)."),
                unsafe_allow_html=True)
    st.markdown(ui.kpi_grid([
        (f"{DEMO_BID['country']} projects", len(sl), "KOICA (IATI)"),
        ("Sectors active", sectors.shape[0], "distinct fields"),
        ("Multilaterals found", len(mult_partners), "parsed from titles"),
        ("Field partners", len(FIELD_PARTNERS), "named in bid doc"),
    ]), unsafe_allow_html=True)
    st.markdown('<div class="eyebrow" style="margin-top:10px;">Sector footprint</div>', unsafe_allow_html=True)
    st.markdown(ui.sector_bars(sectors), unsafe_allow_html=True)
    if mult_partners:
        pills = " ".join(f'<span class="pill pill-intl">{k}</span>' for k in mult_partners)
        st.markdown(f'<div style="margin:2px 0 14px;">Parsed from project titles: {pills}</div>',
                    unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Field and multilateral partners</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    st.markdown(ui.partner_cards(FIELD_PARTNERS), unsafe_allow_html=True)

# ---------------- 04 Partner graph ----------------
elif page.startswith("04"):
    st.markdown(ui.section("Step 04", "Partner ecosystem graph",
                "Bid to components to domestic (blue) / field (amber) / multilateral (violet). "
                "Red = real co-delivery history."), unsafe_allow_html=True)
    G = GV.build_graph(DEMO_BID, COMPONENTS, rec, FIELD_PARTNERS, coedges)
    st.markdown(ui.kpi_grid([
        ("Nodes", G.number_of_nodes(), "actors + components"),
        ("Links", G.number_of_edges(), "relationships"),
        ("Co-delivery", len(coedges), "verified partnerships"),
    ]), unsafe_allow_html=True)
    legend = "".join(f'<span><b style="background:{c}"></b>{n}</span>' for n, c in GV.LEGEND)
    st.markdown(f'<div class="legend">{legend}</div>', unsafe_allow_html=True)
    components.html(GV.render_html(G), height=640)
    if coedges:
        st.markdown('<div class="eyebrow">Verified co-delivery</div>', unsafe_allow_html=True)
        rows = "".join(f'<div class="match"><div class="body"><div class="org">{a} &harr; {b}</div>'
                       f'<div class="ev">{proj}</div></div></div>' for a, b, proj in coedges)
        st.markdown(f'<div class="card">{rows}</div>', unsafe_allow_html=True)

# ---------------- 05 Consortium ----------------
elif page.startswith("05"):
    st.markdown(ui.section("Step 05", "Consortium recommendation",
                "Component-level combination with a composite score. Weights are demo values."),
                unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.6])
    with c1:
        st.markdown(f'<div class="card" style="text-align:center;padding:26px;">'
                    f'<div class="eyebrow">Composite score</div>'
                    f'<div class="gauge">{total}<small>/100</small></div></div>', unsafe_allow_html=True)
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
    st.markdown('<div class="eyebrow" style="margin-top:6px;">Recommended combination</div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    for r in rec:
        st.markdown(ui.rec_row(r["component"], r["domestic"], r["field"]), unsafe_allow_html=True)
    st.caption("Scoring weights and keywords are demo values — production refines with track record, "
               "PQ eligibility and joint-venture (공동수급) history.")
