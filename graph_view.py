"""
Partner ecosystem graph renderer.

Patched version:
- Adds LEGEND used by app.py.
- Accepts both Korean and English recommendation keys.
- Keeps graph rendering stable when pyvis is unavailable.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

import networkx as nx

try:
    from pyvis.network import Network
except Exception:  # pragma: no cover
    Network = None


COLORS = {
    "bid": "#1f2d3d",
    "component": "#3b82f6",
    "domestic": "#10b981",
    "field": "#f59e0b",
    "multilateral": "#8b5cf6",
}

LEGEND = [
    ("Bid", COLORS["bid"]),
    ("Component", COLORS["component"]),
    ("Domestic candidate", COLORS["domestic"]),
    ("Field partner", COLORS["field"]),
    ("Multilateral", COLORS["multilateral"]),
    ("Verified co-delivery", "#ef4444"),
]


def _bid_title(bid: Dict[str, Any]) -> str:
    return bid.get("사업명") or bid.get("title_ko") or bid.get("name") or "ODA Bid"


def _bid_country(bid: Dict[str, Any]) -> str:
    return bid.get("수원국") or bid.get("country_ko") or bid.get("country") or ""


def _bid_budget(bid: Dict[str, Any]) -> str:
    return str(bid.get("예산_백만원") or bid.get("budget_million_krw") or "")


def _domestic_name(domestic: Any) -> str:
    if not domestic:
        return ""
    if isinstance(domestic, dict):
        return domestic.get("기관") or domestic.get("name") or domestic.get("canonical_name_ko") or ""
    return str(domestic)


def build_graph(
    bid: Dict[str, Any],
    components: List[Dict[str, Any]],
    rec: List[Dict[str, Any]],
    field_partners: List[Dict[str, Any]],
    coimpl_edges: Optional[List[Tuple[str, str, str]]] = None,
) -> nx.Graph:
    G = nx.Graph()
    bid_node = _bid_title(bid)
    title = f"{_bid_country(bid)} · {_bid_budget(bid)}백만원".strip(" ·")
    G.add_node(bid_node, group="bid", size=34, title=title)

    for r in rec:
        c = r.get("component", {})
        cid = c.get("name", "Component")
        G.add_node(cid, group="component", size=20, title=c.get("desc", c.get("description", cid)))
        G.add_edge(bid_node, cid, width=2)

        domestic = r.get("국내후보") or r.get("domestic")
        org = _domestic_name(domestic)
        if org:
            score = 0
            source = ""
            reason = ""
            if isinstance(domestic, dict):
                score = float(domestic.get("점수", 0) or 0)
                source = domestic.get("출처", "")
                reason = domestic.get("근거", "")
            G.add_node(org, group="domestic", size=16, title=f"국내 · {source} · {reason}")
            G.add_edge(cid, org, width=1 + score / 30)

        for f in field_partners:
            if c.get("id") in f.get("components", []):
                grp = "multilateral" if f.get("type") in ("국제기구", "다자개발은행") else "field"
                G.add_node(f["name"], group=grp, size=15, title=f'{f.get("type", "")} · {f.get("role", "")}')
                G.add_edge(cid, f["name"], width=1, dashes=True)

    if coimpl_edges:
        for a, b, proj in coimpl_edges:
            if G.has_node(a) and G.has_node(b):
                G.add_edge(a, b, width=4, color="#ef4444", title=f"공동수행: {proj}")
    return G


def render_html(G: nx.Graph, height: str = "620px") -> str:
    if Network is None:
        return "<div style='padding:16px;border:1px solid #e5e7eb;border-radius:12px;'>pyvis is not installed. Install with <code>pip install pyvis</code>.</div>"

    net = Network(height=height, width="100%", bgcolor="#ffffff", font_color="#222", notebook=False, directed=False)
    net.barnes_hut(gravity=-8000, spring_length=120)

    for n, d in G.nodes(data=True):
        label = n if len(str(n)) < 22 else str(n)[:20] + "…"
        net.add_node(
            n,
            label=label,
            color=COLORS.get(d.get("group"), "#999"),
            size=d.get("size", 14),
            title=d.get("title", n),
        )
    for a, b, d in G.edges(data=True):
        net.add_edge(
            a,
            b,
            width=d.get("width", 1),
            color=d.get("color", "#cbd5e1"),
            dashes=d.get("dashes", False),
            title=d.get("title", ""),
        )
    net.set_options('{"physics":{"stabilization":{"iterations":150}}}')
    return net.generate_html()
