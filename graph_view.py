"""
파트너 생태계 그래프.
중심: 사업 → component → (국내후보 / 현지·다자 파트너)
+ 협업이력 엣지(공동수행 실적).
pyvis로 HTML 생성 → app에서 components.html로 임베드.
"""
import networkx as nx
from pyvis.network import Network

COLORS = {
    "bid": "#1f2d3d",
    "component": "#3b82f6",
    "domestic": "#10b981",
    "field": "#f59e0b",
    "multilateral": "#8b5cf6",
}


def build_graph(bid, components, rec, field_partners, coimpl_edges=None):
    G = nx.Graph()
    G.add_node(bid["사업명"], group="bid", size=34, title=f'{bid["수원국"]} · {bid["예산_백만원"]}백만원')

    for r in rec:
        c = r["component"]
        cid = c["name"]
        G.add_node(cid, group="component", size=20, title=c["desc"])
        G.add_edge(bid["사업명"], cid, width=2)

        # 국내 후보
        if r["국내후보"]:
            org = r["국내후보"]["기관"]
            G.add_node(org, group="domestic", size=16,
                       title=f'국내 · {r["국내후보"]["출처"]} · {r["국내후보"]["근거"]}')
            G.add_edge(cid, org, width=1 + r["국내후보"]["점수"] / 6)

        # 현지·다자 파트너
        for f in field_partners:
            if c["id"] in f["components"]:
                grp = "multilateral" if f["type"] in ("국제기구", "다자개발은행") else "field"
                G.add_node(f["name"], group=grp, size=15, title=f'{f["type"]} · {f["role"]}')
                G.add_edge(cid, f["name"], width=1, dashes=True)

    # 협업이력(공동수행) 엣지 — 두 노드가 모두 그래프에 있으면 굵게 연결
    if coimpl_edges:
        for a, b, proj in coimpl_edges:
            if G.has_node(a) and G.has_node(b):
                G.add_edge(a, b, width=4, color="#ef4444", title=f"공동수행: {proj}")
    return G


def render_html(G, height="620px"):
    net = Network(height=height, width="100%", bgcolor="#ffffff",
                  font_color="#222", notebook=False, directed=False)
    net.barnes_hut(gravity=-8000, spring_length=120)
    for n, d in G.nodes(data=True):
        net.add_node(n, label=n if len(n) < 22 else n[:20] + "…",
                     color=COLORS.get(d.get("group"), "#999"),
                     size=d.get("size", 14), title=d.get("title", n))
    for a, b, d in G.edges(data=True):
        net.add_edge(a, b, width=d.get("width", 1),
                     color=d.get("color", "#cbd5e1"),
                     dashes=d.get("dashes", False), title=d.get("title", ""))
    net.set_options('{"physics":{"stabilization":{"iterations":150}}}')
    return net.generate_html()
