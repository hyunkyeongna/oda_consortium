"""
Procurement API clients for ODA Partner Master DB
-------------------------------------------------
Data sources:
- KOICA ODA procurement API
- Nara Jangteo bid / award / contract APIs

This module intentionally keeps endpoint operation names configurable because
public-data APIs occasionally change operation names or required parameters.
It normalizes JSON/XML responses into list[dict] so procurement_ingest.py can
append verified contracting evidence to Partner Master DB CSVs.

Environment variables supported:
- DATA_GO_KR_SERVICE_KEY
- KOICA_PROCUREMENT_BASE_URL
- NARA_BID_BASE_URL
- NARA_AWARD_BASE_URL
- NARA_CONTRACT_BASE_URL
- NARA_PROCESS_BASE_URL
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_KOICA_PROCUREMENT_BASE_URL = "http://apis.data.go.kr/B260003/PrcureService"
DEFAULT_NARA_BID_BASE_URL = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService"
DEFAULT_NARA_AWARD_BASE_URL = "http://apis.data.go.kr/1230000/as/ScsbidInfoService"
DEFAULT_NARA_CONTRACT_BASE_URL = "http://apis.data.go.kr/1230000/ao/CntrctInfoService"
DEFAULT_NARA_PROCESS_BASE_URL = "http://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService"


class ApiClientError(RuntimeError):
    pass


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).replace(",", ""))
    except Exception:
        return default


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _xml_element_to_dict(el: ET.Element) -> Dict[str, Any]:
    children = list(el)
    if not children:
        return { _strip_ns(el.tag): _safe_str(el.text) }
    out: Dict[str, Any] = {}
    for child in children:
        key = _strip_ns(child.tag)
        if list(child):
            value = _xml_element_to_dict(child)
        else:
            value = _safe_str(child.text)
        if isinstance(value, dict) and len(value) == 1 and key in value:
            value = value[key]
        if key in out:
            if not isinstance(out[key], list):
                out[key] = [out[key]]
            out[key].append(value)
        else:
            out[key] = value
    return out


def parse_response_bytes(data: bytes) -> Any:
    text = data.decode("utf-8", errors="replace").strip()
    if not text:
        return {}
    if text.startswith("{") or text.startswith("["):
        return json.loads(text)
    try:
        root = ET.fromstring(text)
        return _xml_element_to_dict(root).get(_strip_ns(root.tag), _xml_element_to_dict(root))
    except Exception as exc:
        raise ApiClientError(f"Could not parse response as JSON/XML: {exc}\n{text[:500]}")


def extract_items(payload: Any) -> List[Dict[str, Any]]:
    """Extract item rows from common data.go.kr response shapes."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []

    # Common shapes:
    # response.body.items.item
    # response.body.items
    # body.items.item
    # items.item
    # data.list
    candidates = [payload]
    for key in ["response", "body", "items", "item", "data", "list", "result"]:
        next_candidates = []
        for c in candidates:
            if isinstance(c, dict) and key in c:
                next_candidates.append(c[key])
        candidates.extend(next_candidates)

    for c in candidates:
        if isinstance(c, list):
            return [x for x in c if isinstance(x, dict)]
        if isinstance(c, dict):
            if "item" in c:
                item = c["item"]
                if isinstance(item, list):
                    return [x for x in item if isinstance(x, dict)]
                if isinstance(item, dict):
                    return [item]
            # Some APIs return rows directly under items as a dict.
            if any(k for k in c.keys() if k not in {"header", "body", "items", "totalCount", "numOfRows", "pageNo"}):
                # Avoid returning the entire response object as one item.
                if not {"response", "body", "header"}.intersection(c.keys()):
                    return [c]
    return []


def extract_total_count(payload: Any) -> Optional[int]:
    if not isinstance(payload, dict):
        return None
    keys = ["totalCount", "totalCnt", "total_count", "numOfRows"]
    stack = [payload]
    seen = set()
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, dict):
            for k in keys:
                if k in cur:
                    v = _to_int(cur.get(k), default=-1)
                    if v >= 0:
                        return v
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


@dataclass
class DataGoKrClient:
    base_url: str
    service_key: str
    timeout: int = 30
    sleep_sec: float = 0.15
    default_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if not self.service_key:
            raise ApiClientError("service_key is required")

    def build_url(self, operation: str, params: Optional[Dict[str, Any]] = None) -> str:
        p: Dict[str, Any] = {
            "serviceKey": self.service_key,
            "pageNo": 1,
            "numOfRows": 100,
            "type": "json",
        }
        p.update(self.default_params)
        if params:
            # Drop empty values to avoid API validation errors.
            p.update({k: v for k, v in params.items() if _safe_str(v) != ""})
        query = urllib.parse.urlencode(p, doseq=True, safe="%")
        return f"{self.base_url}/{operation}?{query}"

    def request(self, operation: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = self.build_url(operation, params=params)
        req = urllib.request.Request(url, headers={"User-Agent": "oda-partner-master/0.1"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = resp.read()
        return parse_response_bytes(data)

    def fetch_all_pages(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        max_pages: int = 1,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        params = dict(params or {})
        total_count: Optional[int] = None
        for page in range(1, max_pages + 1):
            request_params = dict(params)
            request_params.update({"pageNo": page, "numOfRows": page_size})
            payload = self.request(operation, request_params)
            page_rows = extract_items(payload)
            if total_count is None:
                total_count = extract_total_count(payload)
            rows.extend(page_rows)
            if len(page_rows) < page_size:
                break
            if total_count is not None and len(rows) >= total_count:
                break
            if self.sleep_sec:
                time.sleep(self.sleep_sec)
        return rows


class KOICAProcurementClient(DataGoKrClient):
    def __init__(self, service_key: str, base_url: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(base_url or os.getenv("KOICA_PROCUREMENT_BASE_URL", DEFAULT_KOICA_PROCUREMENT_BASE_URL), service_key, **kwargs)

    def annual_plans(self, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> List[Dict[str, Any]]:
        return self.fetch_all_pages("getOrprPlanInfoList", params=params, **kwargs)

    def bid_notices(self, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> List[Dict[str, Any]]:
        return self.fetch_all_pages("getBidPblancInfoList", params=params, **kwargs)

    def sole_contracts(self, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> List[Dict[str, Any]]:
        return self.fetch_all_pages("getVltrnCntrctList", params=params, **kwargs)


class NaraBidClient(DataGoKrClient):
    def __init__(self, service_key: str, base_url: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(base_url or os.getenv("NARA_BID_BASE_URL", DEFAULT_NARA_BID_BASE_URL), service_key, **kwargs)


class NaraAwardClient(DataGoKrClient):
    def __init__(self, service_key: str, base_url: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(base_url or os.getenv("NARA_AWARD_BASE_URL", DEFAULT_NARA_AWARD_BASE_URL), service_key, **kwargs)


class NaraContractClient(DataGoKrClient):
    def __init__(self, service_key: str, base_url: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(base_url or os.getenv("NARA_CONTRACT_BASE_URL", DEFAULT_NARA_CONTRACT_BASE_URL), service_key, **kwargs)


class NaraContractProcessClient(DataGoKrClient):
    def __init__(self, service_key: str, base_url: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(base_url or os.getenv("NARA_PROCESS_BASE_URL", DEFAULT_NARA_PROCESS_BASE_URL), service_key, **kwargs)


NARA_CONTRACT_OPS = {
    "service": "getCntrctInfoListServcPPSSrch",
    "goods": "getCntrctInfoListThngPPSSrch",
    "construction": "getCntrctInfoListCnstwkPPSSrch",
    "foreign": "getCntrctInfoListFrgcptPPSSrch",
}

NARA_AWARD_OPS = {
    "service": "getScsbidListSttusServcPPSSrch",
    "goods": "getScsbidListSttusThngPPSSrch",
    "construction": "getScsbidListSttusCnstwkPPSSrch",
    "foreign": "getScsbidListSttusFrgcptPPSSrch",
}

NARA_PROCESS_OPS = {
    "service": "getCntrctProcssIntgOpenServc",
    "goods": "getCntrctProcssIntgOpenThng",
    "construction": "getCntrctProcssIntgOpen",
    "foreign": "getCntrctProcssIntgOpenFrgcpt",
}
