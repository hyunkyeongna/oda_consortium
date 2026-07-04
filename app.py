"""
ODA 컨소시엄 인텔리전스 — 데모 (KOICA 스리랑카 맹그로브 사업)
실행:  streamlit run app.py
"""
import os
import streamlit as st
import streamlit.components.v1 as components

import pipeline as P
import graph_view as GV
from demo_data import DEMO_BID, COMPONENTS, FIELD_PARTNERS

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
st.set_page_config(page_title="ODA 컨소시엄 인텔리전스", layout="wide")


@st.cache_data
def load():
    return P.load_data(DATA_DIR)


@st.cache_data
def compute():
    d = load()
    rec, total, bd = P.recommend_consortium(COMPONENTS, d["humanitarian"], d["nonprofit"], FIELD_PARTNERS)
    edges = P.co_implementation_edges(d["humanitarian"])
    return d, rec, total, bd, edges


d, rec, total, bd, coedges = compute()


def get_service_key():
    """secrets.toml 없으면 예외 → 데모 모드로 안전 처리."""
    try:
        return st.secrets.get("DATA_GO_KR_SERVICE_KEY", "")
    except Exception:
        return ""


service_key = get_service_key()

# ---------- 사이드바 ----------
st.sidebar.title("ODA 컨소시엄 인텔리전스")
st.sidebar.caption("공고 한 건 → 실현 가능한 컨소까지")
page = st.sidebar.radio("메뉴", [
    "개요",
    "① 공고 분해",
    "② 국내 파트너 매칭",
    "③ 현장·수원국 파트너",
    "④ 파트너 그래프",
    "⑤ 컨소 추천",
], label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.markdown("**데이터 연결 상태**")
st.sidebar.write("나라장터/KOICA 조달 API:",
                 "🟢 연결" if service_key else "⚪ 데모 모드(키 미입력)")
st.sidebar.write(f"KOICA IATI 사업: {len(d['iati'])}건")
st.sidebar.write(f"전국 비영리단체: {len(d['nonprofit'])}곳")
st.sidebar.write(f"KOICA 인도적지원 실적: {len(d['humanitarian'])}건")

# ---------- 개요 ----------
if page == "개요":
    st.title("ODA 컨소시엄 인텔리전스")
    st.markdown("인맥·정보 비대칭으로 굴러가던 **ODA 컨소 형성을 데이터로 투명화·가속화**합니다.")
    c1, c2, c3 = st.columns(3)
    c1.metric("데모 사업", DEMO_BID["수원국"] + " 맹그로브")
    c2.metric("사업 예산", f'{DEMO_BID["예산_백만원"]:,}백만원')
    c3.metric("컨소 종합점수", f"{total}/100")
    st.info(f'**{DEMO_BID["사업명"]}**  \n{DEMO_BID["사업명_영문"]} · {DEMO_BID["기간"]} · {DEMO_BID["발주"]}')
    st.subheader("파이프라인")
    st.markdown(
        "① 공고 인입·분해 → ② 국내 파트너 매칭 → ③ 현장·수원국 파트너 발견 "
        "→ ④ 파트너 그래프 → ⑤ 컨소 추천")
    st.subheader("데이터 소스")
    st.markdown(
        "- **실데이터**: KOICA IATI 사업정보, 전국 비영리민간단체(행안부), KOICA 인도적지원 민관협력 실적, 나라장터·KOICA 조달 API(키 입력 시 라이브)\n"
        "- **목업**: 현지 파트너 카드(집행계획 문서 실명), OECD/WB/ADB(미확보)")

# ---------- ① 공고 분해 ----------
elif page == "① 공고 분해":
    st.header("① 공고 인입 & Component 분해")
    st.caption("실서비스: 나라장터 API로 공고 인입 → NLP로 component 분해. (데모: 집행계획 PDF 기반)")
    if service_key:
        st.success("API 키 감지됨 — 나라장터 라이브 호출 가능")
    else:
        st.warning("데모 모드: `.streamlit/secrets.toml`에 DATA_GO_KR_SERVICE_KEY 입력 시 라이브 호출")
    st.subheader(f'분해 결과 — {len(COMPONENTS)}개 component')
    for c in COMPONENTS:
        with st.container(border=True):
            st.markdown(f"**[{c['id']}] {c['name']}**  ·  _{c['sector']}_")
            st.caption(c["desc"])
            st.write("매칭 키워드:", ", ".join(c["keywords"][:8]), "…")

# ---------- ② 국내 파트너 매칭 ----------
elif page == "② 국내 파트너 매칭":
    st.header("② 국내 파트너 매칭")
    st.caption("각 component를 KOICA 수행실적 + 전국 비영리단체 등록정보와 매칭. 점수=키워드 적합 + 실적/등록부처 가중.")
    tabs = st.tabs([c["name"] for c in COMPONENTS])
    for tab, c in zip(tabs, COMPONENTS):
        with tab:
            m = P.match_domestic(c, d["humanitarian"], d["nonprofit"])
            if len(m):
                st.dataframe(m, use_container_width=True, hide_index=True)
            else:
                st.info("매칭 후보 없음 — 키워드 확장 필요")

# ---------- ③ 현장·수원국 파트너 ----------
elif page == "③ 현장·수원국 파트너":
    st.header("③ 현장·수원국 파트너 발견")
    sl, sectors, partners = P.iati_country_footprint(d["iati"], DEMO_BID["수원국"])
    st.subheader(f'KOICA {DEMO_BID["수원국"]} 사업 footprint — {len(sl)}건')
    st.caption("일반 입찰툴이 못 하는 영역: 수원국에서 실제로 무엇이 돌아가는지 (IATI 실데이터)")
    st.bar_chart(sectors.head(8))
    if partners:
        st.write("사업명에서 추출된 다자기구:", ", ".join(partners.keys()))
    st.subheader("현지·다자 파트너 (집행계획 문서 기반)")
    cols = st.columns(3)
    for i, f in enumerate(FIELD_PARTNERS):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{f['name']}**")
                st.caption(f"{f['type']} · {f['role']}")
                st.write("연계 component:", ", ".join(f["components"]))

# ---------- ④ 파트너 그래프 ----------
elif page == "④ 파트너 그래프":
    st.header("④ 파트너 생태계 그래프")
    st.caption("사업 → component → 국내(초록)/현지(주황)/다자(보라). 빨간 굵은선 = 실제 공동수행 이력.")
    G = GV.build_graph(DEMO_BID, COMPONENTS, rec, FIELD_PARTNERS, coedges)
    c1, c2 = st.columns(2)
    c1.metric("노드", G.number_of_nodes())
    c2.metric("연결", G.number_of_edges())
    components.html(GV.render_html(G), height=640)
    if coedges:
        st.markdown("**실제 공동수행 이력(협업 엣지):**")
        for a, b, proj in coedges:
            st.write(f"- {a} ↔ {b}  ·  _{proj}_")

# ---------- ⑤ 컨소 추천 ----------
elif page == "⑤ 컨소 추천":
    st.header("⑤ 컨소 조합 추천")
    c1, c2 = st.columns([1, 2])
    c1.metric("종합 점수", f"{total}/100")
    with c2:
        st.write("**점수 구성**")
        for k, v in bd.items():
            st.write(f"- {k}: **{v}**")
    st.divider()
    st.subheader("component별 추천 조합")
    for r in rec:
        with st.container(border=True):
            c = r["component"]
            lead = r["국내후보"]
            st.markdown(f"**[{c['id']}] {c['name']}**")
            colA, colB = st.columns(2)
            with colA:
                st.markdown("국내 파트너")
                if lead:
                    st.success(f"{lead['기관']}  ·  {lead['출처']}")
                    st.caption(lead["근거"])
                else:
                    st.info("후보 없음")
            with colB:
                st.markdown("현지·다자 파트너")
                st.write(", ".join(r["현지파트너"]) if r["현지파트너"] else "—")
    st.caption("※ 스코어링 가중치·키워드는 데모 값 — 실서비스에서 실적/PQ자격/공동수급 이력으로 정교화")
