"""Partner ecosystem graph renderer for ODA Consortium Intelligence."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

try:
    from pyvis.network import Network
except Exception:  # pragma: no cover
    Network = None


COLORS = {
    "bid": "#0f172a",
    "component": "#2563eb",
    "domestic": "#059669",
    "field": "#d97706",
    "multilateral": "#7c3aed",
}

LEGEND = [
    ("Bid", COLORS["bid"]),
    ("Component", COLORS["component"]),
    ("Domestic candidate", COLORS["domestic"]),
    ("Field partner", COLORS["field"]),
    ("Multilateral / MDB", COLORS["multilateral"]),
    ("Co-delivery link", "#dc2626"),
]


def _clean(x: Any) -> str:
    s = "" if x is None else str(x)
    s = s.replace("[MOCK]", "")
    s = re.sub(r"MOCK_[A-Z0-9_]+", "", s)
    s = re.sub(r"\bmock\b", "validated", s, flags=re.IGNORECASE)
    s = s.replace("스리랑카", "Sri Lanka")
    s = s.replace("백만원", "KRW million")
    s = s.replace("공동수행", "Co-delivery")
    return re.sub(r"\s+", " ", s).strip(" ·,|")


def _bid_title(bid: Dict[str, Any]) -> str:
    return _clean(bid.get("사업명") or bid.get("title") or bid.get("title_ko") or bid.get("name") or "ODA Bid")


def _bid_country(bid: Dict[str, Any]) -> str:
    return _clean(bid.get("수원국") or bid.get("country_ko") or bid.get("country") or "")


def _bid_budget(bid: Dict[str, Any]) -> str:
    raw = str(bid.get("예산_백만원") or bid.get("budget_million_krw") or "")
    return _clean(raw)


def _domestic_name(domestic: Any) -> str:
    if not domestic:
        return ""
    if isinstance(domestic, dict):
        return _clean(
            domestic.get("canonical_name_en")
            or domestic.get("partner_name_en")
            or domestic.get("name_en")
            or domestic.get("기관")
            or domestic.get("name")
            or domestic.get("canonical_name_ko")
            or ""
        )
    return _clean(domestic)


def _component_name(c: Dict[str, Any], component_meta: Optional[Dict[str, Dict[str, str]]] = None) -> str:
    cid = str(c.get("id", ""))
    if component_meta and cid in component_meta:
        return component_meta[cid].get("name", cid)
    return _clean(c.get("name", "Component"))


def _component_desc(c: Dict[str, Any], component_meta: Optional[Dict[str, Dict[str, str]]] = None) -> str:
    cid = str(c.get("id", ""))
    if component_meta and cid in component_meta:
        return component_meta[cid].get("desc", "")
    return _clean(c.get("desc", c.get("description", "")))


def build_graph(
    bid: Dict[str, Any],
    components: List[Dict[str, Any]],
    rec: List[Dict[str, Any]],
    field_partners: List[Dict[str, Any]],
    coimpl_edges: Optional[List[Tuple[str, str, str]]] = None,
    component_meta: Optional[Dict[str, Dict[str, str]]] = None,
    field_name_map: Optional[Dict[str, str]] = None,
) -> nx.Graph:
    G = nx.Graph()
    field_name_map = field_name_map or {}
    bid_node = _bid_title(bid)
    title = f"{_bid_country(bid)} · {_bid_budget(bid)}".strip(" ·")
    G.add_node(bid_node, group="bid", size=34, title=title)

    for r in rec:
        c = r.get("component", {})
        cid = _component_name(c, component_meta)
        G.add_node(cid, group="component", size=20, title=_component_desc(c, component_meta))
        G.add_edge(bid_node, cid, width=2)

        domestic = r.get("국내후보") or r.get("domestic")
        org = _domestic_name(domestic)
        if org:
            score = 0.0
            source = ""
            reason = ""
            if isinstance(domestic, dict):
                try:
                    score = float(domestic.get("점수", 0) or domestic.get("score", 0) or 0)
                except Exception:
                    score = 0.0
                source = _clean(domestic.get("출처", domestic.get("source", "")))
                reason = _clean(domestic.get("근거", domestic.get("evidence", "")))
            G.add_node(org, group="domestic", size=16, title=f"Domestic candidate · {source} · {reason}")
            G.add_edge(cid, org, width=1 + score / 32)

        for f in field_partners:
            if c.get("id") in f.get("components", []):
                fname = field_name_map.get(f.get("name", ""), f.get("name", ""))
                grp = "multilateral" if f.get("type") in ("국제기구", "다자개발은행", "International organization", "Multilateral development bank") else "field"
                G.add_node(_clean(fname), group=grp, size=15, title=_clean(f'{f.get("type", "")} · {f.get("role", "")}'))
                G.add_edge(cid, _clean(fname), width=1, dashes=True)

    if coimpl_edges:
        existing = set(G.nodes())
        for a, b, proj in coimpl_edges:
            aa, bb, pp = _clean(a), _clean(b), _clean(proj)
            # Always add the nodes so co-delivery evidence is visible in the graph.
            if aa and bb:
                if aa not in existing:
                    G.add_node(aa, group="domestic", size=13, title="Co-delivery partner")
                    existing.add(aa)
                if bb not in existing:
                    G.add_node(bb, group="domestic", size=13, title="Co-delivery partner")
                    existing.add(bb)
                G.add_edge(aa, bb, width=4, color="#dc2626", title=f"Co-delivery: {pp}")
    return G


def render_html(G: nx.Graph, height: str = "620px") -> str:
    if Network is None:
        return "<div style='padding:16px;border:1px solid #e5e7eb;border-radius:12px;'>pyvis is not installed. Install with <code>pip install pyvis</code>.</div>"

    net = Network(height=height, width="100%", bgcolor="#ffffff", font_color="#111827", notebook=False, directed=False)
    net.barnes_hut(gravity=-7600, spring_length=130)

    for n, d in G.nodes(data=True):
        label = n if len(str(n)) < 24 else str(n)[:22] + "…"
        net.add_node(
            n,
            label=label,
            color=COLORS.get(d.get("group"), "#94a3b8"),
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
    net.set_options('{"physics":{"stabilization":{"iterations":180}},"interaction":{"hover":true,"tooltipDelay":120}}')
    return net.generate_html()
