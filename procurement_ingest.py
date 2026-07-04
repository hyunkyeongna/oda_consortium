"""
Append KOICA/Nara procurement evidence to Partner Master DB.

Usage examples:

  # 1) Dry run with no API calls; validates existing Partner DB files.
  python procurement_ingest.py --partner-db ./partner_db --dry-run

  # 2) Fetch KOICA procurement records.
  python procurement_ingest.py --partner-db ./partner_db --service-key "$DATA_GO_KR_SERVICE_KEY" --koica --max-pages 3

  # 3) Fetch Nara contract/award records for KOICA-related terms.
  python procurement_ingest.py --partner-db ./partner_db --service-key "$DATA_GO_KR_SERVICE_KEY" --nara \
      --keyword 한국국제협력단 --keyword KOICA --date-from 20240101 --date-to 20261231 --max-pages 2

Outputs updated / created in --partner-db:
- partners.csv
- partner_aliases.csv
- partner_sources.csv
- partner_projects.csv
- project_participants.csv
- partner_capabilities.csv
- partner_master_summary.csv
- partner_edges.csv
- procurement_records.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from procurement_api_clients import (
    ApiClientError,
    KOICAProcurementClient,
    NaraAwardClient,
    NaraContractClient,
    NaraContractProcessClient,
    NARA_AWARD_OPS,
    NARA_CONTRACT_OPS,
    NARA_PROCESS_OPS,
)

# Reuse normalization/taxonomy from the builder when available.
try:
    from partner_master_builder import (
        CAPABILITY_TAGS,
        compact_evidence,
        find_capability_hits,
        make_partner_id,
        normalize_org_name,
        safe_str,
        split_orgs,
        to_float,
    )
except Exception:  # pragma: no cover
    CAPABILITY_TAGS = {}

    def safe_str(value: Any) -> str:
        return "" if value is None else str(value).strip()

    def normalize_org_name(name: str) -> str:
        text = safe_str(name).lower()
        for token in ["사단법인", "재단법인", "(사)", "㈔", "주식회사", "(주)", "㈜"]:
            text = text.replace(token, "")
        return re.sub(r"[\s\.\,\-\_\(\)\[\]·/\\:;|&]+", "", text)

    def make_partner_id(normalized_name: str) -> str:
        return "P_" + hashlib.md5(normalized_name.encode("utf-8")).hexdigest()[:10].upper()

    def compact_evidence(text: str, max_len: int = 260) -> str:
        text = re.sub(r"\s+", " ", safe_str(text))
        return text if len(text) <= max_len else text[: max_len - 1] + "…"

    def split_orgs(raw: str) -> List[str]:
        parts = re.split(r",|;|\n|\s+및\s+|\s*&\s+|\s+and\s+", safe_str(raw), flags=re.I)
        return [p.strip() for p in parts if len(normalize_org_name(p)) >= 2]

    def to_float(value: Any) -> Optional[float]:
        text = re.sub(r"[^0-9\.\-]", "", safe_str(value))
        try:
            return float(text) if text else None
        except Exception:
            return None

    def find_capability_hits(text: str) -> Dict[str, List[str]]:
        return {}


TITLE_FIELDS = [
    "project_title_ko", "project_title_en", "사업명", "사업명(국문)", "사업명_국문", "bizNm",
    "bidNtceNm", "bidNm", "입찰명", "공고명", "cntrctNm", "계약명", "prdctClsfcNoNm", "품명",
]
COUNTRY_FIELDS = ["수원국", "국가", "country", "rcpntNtnNm", "ntnNm", "recipientCountry"]
BUYER_FIELDS = ["발주기관", "발주처", "ntceInsttNm", "dminsttNm", "cntrctInsttNm", "orderInsttNm", "계약기관명", "수요기관명"]
SUPPLIER_FIELDS = [
    "계약상대자", "계약상대자명", "낙찰자", "낙찰자명", "업체명", "수의계약상대자",
    "cntrctEntrpsNm", "cntrctCorpNm", "cntrctCnclsEntrpsNm", "entrpsNm", "bizrnoNm",
    "scsbidCorpNm", "scsbidEntrpsNm", "finalSucsfEntrpsNm", "opengCorpNm", "prtcptCnum", "corpNm",
]
BID_NO_FIELDS = ["공고번호", "입찰공고번호", "bidNtceNo", "bidPblancNo", "ntceNo"]
CONTRACT_NO_FIELDS = ["계약번호", "cntrctNo", "untyCntrctNo", "계약참조번호"]
DATE_FIELDS = ["계약일자", "cntrctDate", "cntrctCnclsDate", "개찰일자", "opengDate", "bidOpenDt", "공고일자", "ntceDate", "발주시기"]
AMOUNT_FIELDS = ["계약금액", "cntrctAmt", "sucsfbidAmt", "scsbidAmt", "낙찰금액", "입찰한도금액", "budget", "예산"]
METHOD_FIELDS = ["계약방법", "cntrctMthdNm", "bidMthdNm", "계약구분", "조달구분", "procureSeNm"]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, dtype=str, encoding=enc).fillna("")
        except Exception:
            pass
    raise RuntimeError(f"Could not read {path}")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def first_value(record: Dict[str, Any], candidates: Sequence[str]) -> str:
    # exact candidates first
    for field in candidates:
        value = safe_str(record.get(field))
        if value:
            return value
    # case-insensitive fallback
    lower_map = {safe_str(k).lower(): v for k, v in record.items()}
    for field in candidates:
        value = safe_str(lower_map.get(field.lower()))
        if value:
            return value
    return ""


def record_text(record: Dict[str, Any]) -> str:
    return " ".join(safe_str(v) for v in record.values() if safe_str(v))


def make_project_id(source_name: str, source_record_id: str, title: str) -> str:
    raw = safe_str(source_record_id) or safe_str(title) or now_iso()
    digest = hashlib.md5(f"{source_name}|{raw}".encode("utf-8")).hexdigest()[:12].upper()
    return f"PRJ_{digest}"


def extract_year(value: Any) -> Optional[int]:
    m = re.search(r"(19|20)\d{2}", safe_str(value))
    return int(m.group(0)) if m else None


def classify_role(source_name: str, record_type: str) -> str:
    if "award" in record_type:
        return "awarded_contractor"
    if "contract" in record_type:
        return "contractor"
    if "sole" in record_type:
        return "sole_source_contractor"
    if "bid" in record_type:
        return "bid_notice_related_party"
    return "procurement_party"


def normalize_procurement_record(record: Dict[str, Any], source_name: str, record_type: str) -> Dict[str, Any]:
    title = first_value(record, TITLE_FIELDS)
    supplier = first_value(record, SUPPLIER_FIELDS)
    buyer = first_value(record, BUYER_FIELDS)
    bid_no = first_value(record, BID_NO_FIELDS)
    contract_no = first_value(record, CONTRACT_NO_FIELDS)
    source_record_id = contract_no or bid_no or first_value(record, ["id", "seq", "no", "번호"])
    amount_raw = first_value(record, AMOUNT_FIELDS)
    date_raw = first_value(record, DATE_FIELDS)
    country = first_value(record, COUNTRY_FIELDS)
    method = first_value(record, METHOD_FIELDS)
    return {
        "source_name": source_name,
        "record_type": record_type,
        "source_record_id": source_record_id,
        "title": title,
        "supplier_raw": supplier,
        "buyer": buyer,
        "bid_notice_no": bid_no,
        "contract_no": contract_no,
        "amount_krw": to_float(amount_raw),
        "date_raw": date_raw,
        "year": extract_year(date_raw),
        "country": country,
        "method": method,
        "raw_json": json.dumps(record, ensure_ascii=False),
        "evidence_text": compact_evidence(record_text(record), 800),
    }


def split_suppliers(raw: str) -> List[str]:
    text = safe_str(raw)
    if not text:
        return []
    # Remove common business registration fragments but keep organization names.
    text = re.sub(r"\([^)]*사업자[^)]*\)", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    # Some Nara rows use comma/plus/slash for joint contractors. Slash is risky, but useful for JV strings.
    parts = re.split(r",|;|\n|\+|\s*/\s*|\s+및\s+|\s*&\s+|\s+and\s+|\s+외\s+\d+\s*개사", text, flags=re.I)
    out = []
    for p in parts:
        p = safe_str(p)
        p = re.sub(r"^(대표사|공동수급체|공동이행|분담이행)[:：\s]+", "", p)
        if len(normalize_org_name(p)) >= 2:
            out.append(p)
    return list(dict.fromkeys(out))


class PartnerDbUpdater:
    def __init__(self, partner_db_dir: Path) -> None:
        self.partner_db_dir = partner_db_dir
        self.created_at = now_iso()
        self.partners = read_csv(partner_db_dir / "partners.csv")
        self.aliases = read_csv(partner_db_dir / "partner_aliases.csv")
        self.sources = read_csv(partner_db_dir / "partner_sources.csv")
        self.projects = read_csv(partner_db_dir / "partner_projects.csv")
        self.participants = read_csv(partner_db_dir / "project_participants.csv")
        self.capabilities = read_csv(partner_db_dir / "partner_capabilities.csv")
        self.summary = read_csv(partner_db_dir / "partner_master_summary.csv")
        self.edges = read_csv(partner_db_dir / "partner_edges.csv")
        self.procurement_records = read_csv(partner_db_dir / "procurement_records.csv")

        self.partners_by_id = set(self.partners.get("partner_id", pd.Series(dtype=str)).astype(str).tolist())
        self.alias_norm_to_partner: Dict[str, str] = {}
        if not self.aliases.empty and {"alias_normalized", "partner_id"}.issubset(self.aliases.columns):
            for _, r in self.aliases.iterrows():
                self.alias_norm_to_partner[safe_str(r.get("alias_normalized"))] = safe_str(r.get("partner_id"))
        if not self.partners.empty and {"partner_id", "canonical_name_ko"}.issubset(self.partners.columns):
            for _, r in self.partners.iterrows():
                self.alias_norm_to_partner[normalize_org_name(r.get("canonical_name_ko"))] = safe_str(r.get("partner_id"))

    def resolve_or_create_partner(self, raw_name: str, source_name: str, source_record_id: str, role_field: str) -> Optional[str]:
        raw_name = safe_str(raw_name)
        norm = normalize_org_name(raw_name)
        if not norm:
            return None
        partner_id = self.alias_norm_to_partner.get(norm) or make_partner_id(norm)
        if partner_id not in self.partners_by_id:
            row = {
                "partner_id": partner_id,
                "canonical_name_ko": raw_name,
                "canonical_name_en": "",
                "org_type": "procurement_contractor",
                "legal_type": "",
                "country": "Korea",
                "registration_status": "procurement_verified",
                "first_seen_source": source_name,
                "created_at": self.created_at,
                "updated_at": self.created_at,
                "source_count": "",
                "project_count": "",
                "capability_count": "",
                "top_capabilities": "",
            }
            self.partners = pd.concat([self.partners, pd.DataFrame([row])], ignore_index=True)
            self.partners_by_id.add(partner_id)
        self.add_alias(partner_id, raw_name, source_name)
        self.add_source(partner_id, source_name, source_record_id, raw_name, role_field)
        self.alias_norm_to_partner[norm] = partner_id
        return partner_id

    def add_alias(self, partner_id: str, alias: str, source_name: str) -> None:
        alias_norm = normalize_org_name(alias)
        if not alias_norm:
            return
        if not self.aliases.empty and {"partner_id", "alias_normalized", "source"}.issubset(self.aliases.columns):
            exists = (
                (self.aliases["partner_id"].astype(str) == partner_id)
                & (self.aliases["alias_normalized"].astype(str) == alias_norm)
                & (self.aliases["source"].astype(str) == source_name)
            ).any()
            if exists:
                return
        row = {"partner_id": partner_id, "alias": alias, "alias_normalized": alias_norm, "source": source_name, "confidence": 1.0}
        self.aliases = pd.concat([self.aliases, pd.DataFrame([row])], ignore_index=True)

    def add_source(self, partner_id: str, source_name: str, source_record_id: str, raw_name: str, verified_field: str) -> None:
        row = {
            "partner_id": partner_id,
            "source_name": source_name,
            "source_record_id": source_record_id,
            "raw_name": raw_name,
            "verified_field": verified_field,
            "collected_at": self.created_at,
        }
        self.sources = pd.concat([self.sources, pd.DataFrame([row])], ignore_index=True)

    def add_project_once(self, row: Dict[str, Any]) -> str:
        project_id = row["project_id"]
        if not self.projects.empty and "project_id" in self.projects.columns:
            if (self.projects["project_id"].astype(str) == project_id).any():
                return project_id
        self.projects = pd.concat([self.projects, pd.DataFrame([row])], ignore_index=True)
        return project_id

    def add_participant_once(self, row: Dict[str, Any]) -> None:
        keys = ["project_id", "partner_id", "role", "source_name"]
        if not self.participants.empty and set(keys).issubset(self.participants.columns):
            mask = pd.Series([True] * len(self.participants))
            for k in keys:
                mask = mask & (self.participants[k].astype(str) == safe_str(row.get(k)))
            if mask.any():
                return
        self.participants = pd.concat([self.participants, pd.DataFrame([row])], ignore_index=True)

    def add_capability_evidence(self, partner_id: str, text: str, source_name: str, evidence_ref: str, year: Optional[int], weight: float = 2.0) -> None:
        hits_by_tag = find_capability_hits(text)
        for tag, hits in hits_by_tag.items():
            score = min(100, max(20, len(hits) * 12 * weight))
            row = {
                "partner_id": partner_id,
                "capability_tag": tag,
                "score": round(score, 1),
                "evidence_count": 1,
                "last_evidence_year": year,
                "evidence_keywords": ", ".join(list(dict.fromkeys(hits))[:20]),
                "evidence_summary": f"[{source_name}] {compact_evidence(text, 260)}",
            }
            self.capabilities = pd.concat([self.capabilities, pd.DataFrame([row])], ignore_index=True)

    def add_edge(self, partner_a: str, partner_b: str, relation_type: str, project_id: str, evidence_text: str, weight: float = 4.0) -> None:
        if partner_a == partner_b:
            return
        # Ensure stable order for undirected graph.
        a, b = sorted([partner_a, partner_b])
        row = {
            "partner_a": a,
            "partner_b": b,
            "relation_type": relation_type,
            "project_id": project_id,
            "evidence_text": compact_evidence(evidence_text, 300),
            "weight": weight,
        }
        if not self.edges.empty and {"partner_a", "partner_b", "project_id", "relation_type"}.issubset(self.edges.columns):
            mask = (
                (self.edges["partner_a"].astype(str) == a)
                & (self.edges["partner_b"].astype(str) == b)
                & (self.edges["project_id"].astype(str) == project_id)
                & (self.edges["relation_type"].astype(str) == relation_type)
            )
            if mask.any():
                return
        self.edges = pd.concat([self.edges, pd.DataFrame([row])], ignore_index=True)

    def ingest_normalized_record(self, rec: Dict[str, Any]) -> None:
        title = safe_str(rec.get("title")) or safe_str(rec.get("source_record_id"))
        source_name = safe_str(rec.get("source_name"))
        project_id = make_project_id(source_name, safe_str(rec.get("source_record_id")), title)
        text = " ".join([title, safe_str(rec.get("country")), safe_str(rec.get("method")), safe_str(rec.get("evidence_text"))])
        self.add_project_once({
            "project_id": project_id,
            "source_name": source_name,
            "source_record_id": safe_str(rec.get("source_record_id")),
            "project_title_ko": title,
            "project_title_en": "",
            "country": safe_str(rec.get("country")),
            "region": "",
            "sector": safe_str(rec.get("method")),
            "start_year": rec.get("year"),
            "end_year": rec.get("year"),
            "budget_krw": rec.get("amount_krw"),
            "description": compact_evidence(text, 500),
        })
        self.procurement_records = pd.concat([self.procurement_records, pd.DataFrame([rec])], ignore_index=True)

        supplier_raw = safe_str(rec.get("supplier_raw"))
        suppliers = split_suppliers(supplier_raw)
        partner_ids: List[str] = []
        for supplier in suppliers:
            partner_id = self.resolve_or_create_partner(supplier, source_name, safe_str(rec.get("source_record_id")), "supplier/contractor")
            if not partner_id:
                continue
            partner_ids.append(partner_id)
            self.add_participant_once({
                "project_id": project_id,
                "partner_id": partner_id,
                "raw_name": supplier,
                "role": classify_role(source_name, safe_str(rec.get("record_type"))),
                "source_name": source_name,
                "confidence": 0.95,
                "evidence_text": compact_evidence(text, 300),
            })
            self.add_capability_evidence(partner_id, text, source_name, project_id, rec.get("year"), weight=2.0)

        if len(partner_ids) > 1:
            for i in range(len(partner_ids)):
                for j in range(i + 1, len(partner_ids)):
                    self.add_edge(partner_ids[i], partner_ids[j], "co_contract_or_award", project_id, text, weight=5.0)

    def rebuild_capability_summary(self) -> None:
        if self.capabilities.empty:
            return
        # Consolidate duplicate partner/capability rows after API append.
        caps = self.capabilities.copy()
        for c in ["score", "evidence_count"]:
            if c in caps.columns:
                caps[c] = pd.to_numeric(caps[c], errors="coerce").fillna(0)
        grouped = []
        for (partner_id, tag), g in caps.groupby(["partner_id", "capability_tag"]):
            keywords = []
            summaries = []
            years = []
            for _, r in g.iterrows():
                keywords.extend([x.strip() for x in safe_str(r.get("evidence_keywords")).split(",") if x.strip()])
                summaries.append(safe_str(r.get("evidence_summary")))
                y = extract_year(r.get("last_evidence_year"))
                if y:
                    years.append(y)
            score = min(100, round(float(g["score"].max()) + min(15, len(g) * 2), 1))
            grouped.append({
                "partner_id": partner_id,
                "capability_tag": tag,
                "score": score,
                "evidence_count": int(g["evidence_count"].sum()) if "evidence_count" in g else len(g),
                "last_evidence_year": max(years) if years else "",
                "evidence_keywords": ", ".join(list(dict.fromkeys(keywords))[:20]),
                "evidence_summary": " | ".join([s for s in summaries if s][:4]),
            })
        self.capabilities = pd.DataFrame(grouped).sort_values(["score", "evidence_count"], ascending=[False, False])

    def rebuild_partner_summary(self) -> None:
        self.rebuild_capability_summary()
        projects_by_partner = defaultdict(set)
        if not self.participants.empty and {"partner_id", "project_id"}.issubset(self.participants.columns):
            for _, r in self.participants.iterrows():
                projects_by_partner[safe_str(r.get("partner_id"))].add(safe_str(r.get("project_id")))
        sources_by_partner = defaultdict(set)
        if not self.sources.empty and {"partner_id", "source_name"}.issubset(self.sources.columns):
            for _, r in self.sources.iterrows():
                sources_by_partner[safe_str(r.get("partner_id"))].add(safe_str(r.get("source_name")))
        caps_by_partner = defaultdict(list)
        if not self.capabilities.empty and {"partner_id", "capability_tag", "score"}.issubset(self.capabilities.columns):
            for _, r in self.capabilities.sort_values("score", ascending=False).iterrows():
                caps_by_partner[safe_str(r.get("partner_id"))].append(f"{safe_str(r.get('capability_tag'))}({safe_str(r.get('score'))})")

        rows = []
        for _, p in self.partners.iterrows():
            pid = safe_str(p.get("partner_id"))
            rows.append({
                "partner_id": pid,
                "canonical_name_ko": safe_str(p.get("canonical_name_ko")),
                "canonical_name_en": safe_str(p.get("canonical_name_en")),
                "org_type": safe_str(p.get("org_type")),
                "legal_type": safe_str(p.get("legal_type")),
                "registration_status": safe_str(p.get("registration_status")),
                "source_count": len(sources_by_partner[pid]),
                "project_count": len(projects_by_partner[pid]),
                "capability_count": len(caps_by_partner[pid]),
                "top_capabilities": ", ".join([x.split("(")[0] for x in caps_by_partner[pid][:5]]),
                "top_capability_scores": " / ".join(caps_by_partner[pid][:3]),
                "first_seen_source": safe_str(p.get("first_seen_source")),
            })
        self.summary = pd.DataFrame(rows).sort_values(["project_count", "source_count", "canonical_name_ko"], ascending=[False, False, True])

    def write(self) -> None:
        self.rebuild_partner_summary()
        write_csv(self.partners, self.partner_db_dir / "partners.csv")
        write_csv(self.aliases, self.partner_db_dir / "partner_aliases.csv")
        write_csv(self.sources, self.partner_db_dir / "partner_sources.csv")
        write_csv(self.projects, self.partner_db_dir / "partner_projects.csv")
        write_csv(self.participants, self.partner_db_dir / "project_participants.csv")
        write_csv(self.capabilities, self.partner_db_dir / "partner_capabilities.csv")
        write_csv(self.summary, self.partner_db_dir / "partner_master_summary.csv")
        write_csv(self.edges, self.partner_db_dir / "partner_edges.csv")
        write_csv(self.procurement_records, self.partner_db_dir / "procurement_records.csv")


def fetch_koica_records(args: argparse.Namespace) -> List[Dict[str, Any]]:
    client = KOICAProcurementClient(args.service_key, base_url=args.koica_base_url, timeout=args.timeout)
    out: List[Dict[str, Any]] = []
    for record_type, fn in [
        ("koica_annual_plan", client.annual_plans),
        ("koica_bid_notice", client.bid_notices),
        ("koica_sole_contract", client.sole_contracts),
    ]:
        try:
            rows = fn(max_pages=args.max_pages, page_size=args.page_size)
            for r in rows:
                out.append(normalize_procurement_record(r, "koica_procurement_api", record_type))
            logging.info("KOICA %s: %s rows", record_type, len(rows))
        except Exception as exc:
            logging.warning("KOICA %s fetch failed: %s", record_type, exc)
    return out


def nara_params_for_keyword(args: argparse.Namespace, keyword: str) -> Dict[str, Any]:
    # Contract service docs include cntrctCnclsBgnDate / cntrctCnclsEndDate.
    # Bid/award/contract service APIs also commonly use inqryDiv=1/2 and keyword fields.
    params: Dict[str, Any] = {
        "inqryDiv": args.inqry_div,
        "cntrctCnclsBgnDate": args.date_from,
        "cntrctCnclsEndDate": args.date_to,
        "opengBgnDate": args.date_from,
        "opengEndDate": args.date_to,
    }
    if keyword:
        # Try both buyer/demand institution and title/product fields. APIs ignore unknown fields poorly on some endpoints,
        # so procurement teams can adjust via --nara-param-json when needed.
        params.update({
            "ntceInsttNm": keyword,
            "dminsttNm": keyword,
            "cntrctNm": keyword,
            "prdctClsfcNoNm": keyword,
        })
    if args.nara_param_json:
        params.update(json.loads(args.nara_param_json))
    return {k: v for k, v in params.items() if safe_str(v)}


def fetch_nara_records(args: argparse.Namespace) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    contract_client = NaraContractClient(args.service_key, base_url=args.nara_contract_base_url, timeout=args.timeout)
    award_client = NaraAwardClient(args.service_key, base_url=args.nara_award_base_url, timeout=args.timeout)
    process_client = NaraContractProcessClient(args.service_key, base_url=args.nara_process_base_url, timeout=args.timeout)

    work_types = args.nara_work_type or ["service"]
    keywords = args.keyword or [""]

    for work_type in work_types:
        if args.fetch_nara_contracts:
            op = NARA_CONTRACT_OPS.get(work_type)
            if op:
                for kw in keywords:
                    try:
                        rows = contract_client.fetch_all_pages(op, params=nara_params_for_keyword(args, kw), max_pages=args.max_pages, page_size=args.page_size)
                        for r in rows:
                            records.append(normalize_procurement_record(r, "nara_contract_api", f"nara_contract_{work_type}"))
                        logging.info("Nara contract %s %s: %s rows", work_type, kw, len(rows))
                    except Exception as exc:
                        logging.warning("Nara contract fetch failed: work_type=%s keyword=%s error=%s", work_type, kw, exc)
        if args.fetch_nara_awards:
            op = NARA_AWARD_OPS.get(work_type)
            if op:
                for kw in keywords:
                    try:
                        rows = award_client.fetch_all_pages(op, params=nara_params_for_keyword(args, kw), max_pages=args.max_pages, page_size=args.page_size)
                        for r in rows:
                            records.append(normalize_procurement_record(r, "nara_award_api", f"nara_award_{work_type}"))
                        logging.info("Nara award %s %s: %s rows", work_type, kw, len(rows))
                    except Exception as exc:
                        logging.warning("Nara award fetch failed: work_type=%s keyword=%s error=%s", work_type, kw, exc)
        if args.bid_notice_no:
            op = NARA_PROCESS_OPS.get(work_type)
            if op:
                for bid_no in args.bid_notice_no:
                    try:
                        params = {"inqryDiv": args.inqry_div, "bidNtceNo": bid_no}
                        rows = process_client.fetch_all_pages(op, params=params, max_pages=args.max_pages, page_size=args.page_size)
                        for r in rows:
                            records.append(normalize_procurement_record(r, "nara_contract_process_api", f"nara_process_{work_type}"))
                        logging.info("Nara process %s %s: %s rows", work_type, bid_no, len(rows))
                    except Exception as exc:
                        logging.warning("Nara process fetch failed: work_type=%s bid_no=%s error=%s", work_type, bid_no, exc)
    return records


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Append KOICA/Nara procurement evidence to Partner Master DB.")
    p.add_argument("--partner-db", default="partner_db", help="Directory containing Partner Master DB CSVs")
    p.add_argument("--service-key", default=os.getenv("DATA_GO_KR_SERVICE_KEY", ""), help="data.go.kr service key")
    p.add_argument("--koica", action="store_true", help="Fetch KOICA procurement API")
    p.add_argument("--nara", action="store_true", help="Fetch Nara contract/award APIs")
    p.add_argument("--dry-run", action="store_true", help="Do not call APIs or write files")
    p.add_argument("--max-pages", type=int, default=1)
    p.add_argument("--page-size", type=int, default=100)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--keyword", action="append", default=[], help="Nara search keyword; can be repeated")
    p.add_argument("--date-from", default="", help="YYYYMMDD")
    p.add_argument("--date-to", default="", help="YYYYMMDD")
    p.add_argument("--inqry-div", default="1", help="Nara inquiry division. Common values: 1/2 depending operation")
    p.add_argument("--nara-work-type", action="append", choices=["service", "goods", "construction", "foreign"], default=[])
    p.add_argument("--bid-notice-no", action="append", default=[], help="Nara bid notice number for contract-process lookup")
    p.add_argument("--fetch-nara-contracts", action="store_true", default=True)
    p.add_argument("--fetch-nara-awards", action="store_true", default=True)
    p.add_argument("--nara-param-json", default="", help='Extra Nara params as JSON, e.g. {"dminsttNm":"한국국제협력단"}')
    p.add_argument("--koica-base-url", default=os.getenv("KOICA_PROCUREMENT_BASE_URL", ""))
    p.add_argument("--nara-contract-base-url", default=os.getenv("NARA_CONTRACT_BASE_URL", ""))
    p.add_argument("--nara-award-base-url", default=os.getenv("NARA_AWARD_BASE_URL", ""))
    p.add_argument("--nara-process-base-url", default=os.getenv("NARA_PROCESS_BASE_URL", ""))
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")
    partner_db_dir = Path(args.partner_db)
    updater = PartnerDbUpdater(partner_db_dir)
    logging.info("Loaded Partner DB: partners=%s projects=%s participants=%s", len(updater.partners), len(updater.projects), len(updater.participants))

    if args.dry_run:
        print("Dry run OK. No API calls or writes performed.")
        return
    if (args.koica or args.nara) and not args.service_key:
        raise SystemExit("--service-key or DATA_GO_KR_SERVICE_KEY is required for API fetch")

    records: List[Dict[str, Any]] = []
    if args.koica:
        records.extend(fetch_koica_records(args))
    if args.nara:
        records.extend(fetch_nara_records(args))

    logging.info("Normalized procurement records: %s", len(records))
    for rec in records:
        updater.ingest_normalized_record(rec)
    updater.write()
    print(f"Updated Partner Master DB at {partner_db_dir}")
    print(f"- added/processed procurement records: {len(records)}")
    print(f"- partners: {len(updater.partners)}")
    print(f"- projects: {len(updater.projects)}")
    print(f"- participants: {len(updater.participants)}")
    print(f"- edges: {len(updater.edges)}")


if __name__ == "__main__":
    main()
