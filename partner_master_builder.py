"""
Partner Master DB Builder
-------------------------
Builds a minimum viable Partner Master DB for an ODA consortium recommendation engine.

Inputs expected in --data-dir:
- koica_humanitarian.csv
- koica_iati.csv
- nonprofit_national.csv

Outputs written to --out-dir:
- partners.csv
- partner_aliases.csv
- partner_sources.csv
- partner_projects.csv
- project_participants.csv
- partner_capabilities.csv
- partner_master_summary.csv

Run examples:
    python partner_master_builder.py
    python partner_master_builder.py --data-dir ./data --out-dir ./partner_db
    python partner_master_builder.py --data-dir /mnt/data --out-dir /mnt/data/partner_db
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


# -----------------------------------------------------------------------------
# Capability taxonomy
# -----------------------------------------------------------------------------

CAPABILITY_TAGS: Dict[str, List[str]] = {
    "ODA_PMC": [
        "pmc", "project management", "사업관리", "사업 수행관리", "수행관리",
        "성과관리", "pdm", "m&e", "monitoring", "evaluation", "평가",
        "모니터링", "사업성과", "산출물 관리", "project coordination",
    ],
    "project_design_policy_research": [
        "정책연구", "정책 연구", "전략", "타당성", "예비조사", "기초선",
        "baseline", "조사", "컨설팅", "consulting", "feasibility", "strategy",
        "master plan", "마스터플랜", "계획 수립", "관리계획", "manual", "매뉴얼",
    ],
    "forestry_restoration": [
        "산림", "임업", "조림", "복원", "생태", "맹그로브", "mangrove",
        "forest", "forestry", "restoration", "reforestation", "biodiversity",
        "생물다양성", "보호지역", "ecosystem", "wetland", "습지",
    ],
    "GIS_remote_sensing": [
        "gis", "드론", "drone", "원격탐사", "remote sensing", "mapping", "매핑",
        "공간정보", "geospatial", "gps", "위성", "satellite", "ict", "정보화",
        "데이터", "data", "forest geographic", "fgis",
    ],
    "aquaculture_livelihood": [
        "양식", "수산", "어업", "fisheries", "aquaculture", "shrimp", "새우",
        "livelihood", "생계", "소득", "income", "community", "커뮤니티", "주민",
        "지역개발", "value chain", "가치사슬", "농업", "agriculture",
    ],
    "capacity_building_training": [
        "역량강화", "capacity", "capacity building", "교육", "training", "연수",
        "훈련", "워크숍", "workshop", "초청연수", "교육프로그램", "홍보자료",
        "awareness", "인식제고", "세미나", "seminar",
    ],
    "construction_infrastructure": [
        "건축", "건설", "시공", "리모델링", "remodeling", "renovation",
        "infrastructure", "인프라", "building", "construction", "센터", "설계",
        "토목", "시설", "facility",
    ],
    "procurement_equipment": [
        "기자재", "장비", "조달", "equipment", "procurement", "실험실", "laboratory",
        "vehicle", "차량", "it 장비", "device", "기기", "material", "supplies",
    ],
    "health_wash_humanitarian": [
        "wash", "보건", "위생", "health", "sanitation", "water", "식수", "난민",
        "refugee", "인도적", "humanitarian", "긴급구호", "재난", "disaster",
    ],
    "education_youth": [
        "교육", "학교", "학생", "아동", "청소년", "youth", "school", "student",
        "child", "children", "curriculum", "교재", "literacy", "문해",
    ],
}

# Ministries that make a Korean registered non-profit more relevant for ODA/environment matching.
RELEVANT_REGISTRATION_BODIES = {
    "외교부",
    "기후에너지환경부",
    "환경부",
    "산림청",
    "해양수산부",
    "농림축산식품부",
    "중소벤처기업부",
    "국무조정실",
    "교육부",
}

# Multilateral / international agencies that often appear in KOICA IATI project titles.
MULTILATERAL_PATTERNS: Dict[str, Dict[str, str]] = {
    "WHO": {"name": "World Health Organization", "type": "multilateral"},
    "UNDP": {"name": "United Nations Development Programme", "type": "multilateral"},
    "UNICEF": {"name": "United Nations Children's Fund", "type": "multilateral"},
    "UNEP": {"name": "United Nations Environment Programme", "type": "multilateral"},
    "UNESCO": {"name": "United Nations Educational, Scientific and Cultural Organization", "type": "multilateral"},
    "UN-HABITAT": {"name": "United Nations Human Settlements Programme", "type": "multilateral"},
    "UNHABITAT": {"name": "United Nations Human Settlements Programme", "type": "multilateral"},
    "WFP": {"name": "World Food Programme", "type": "multilateral"},
    "FAO": {"name": "Food and Agriculture Organization", "type": "multilateral"},
    "IOM": {"name": "International Organization for Migration", "type": "multilateral"},
    "ADB": {"name": "Asian Development Bank", "type": "multilateral_development_bank"},
    "IFAD": {"name": "International Fund for Agricultural Development", "type": "multilateral"},
    "UNFPA": {"name": "United Nations Population Fund", "type": "multilateral"},
    "GGGI": {"name": "Global Green Growth Institute", "type": "international_organization"},
}


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def read_csv_safely(path: Path) -> pd.DataFrame:
    if not path.exists():
        logging.warning("Missing input file: %s", path)
        return pd.DataFrame()
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
    last_error: Optional[Exception] = None
    for enc in encodings:
        try:
            return pd.read_csv(path, dtype=str, encoding=enc).fillna("")
        except Exception as exc:  # pragma: no cover - defensive fallback
            last_error = exc
    raise RuntimeError(f"Could not read CSV: {path}. Last error: {last_error}")


def normalize_org_name(name: str) -> str:
    """Normalize organization names for deterministic identity matching."""
    text = safe_str(name).lower()
    if not text:
        return ""

    replacements = [
        "사단법인", "재단법인", "사회복지법인", "공익법인", "비영리법인",
        "특정비영리활동법인", "학교법인", "의료법인",
        "(사)", "㈔", "(재)", "㈜", "(주)", "주식회사",
        "incorporated", "foundation", "association", "corporation",
        "co.,ltd", "co. ltd", "co ltd", "ltd.", "ltd", "inc.", "inc",
        "the ",
    ]
    for token in replacements:
        text = text.replace(token, "")

    text = re.sub(r"[\s\.\,\-\_\(\)\[\]\{\}·ㆍ/\\:;|&]+", "", text)
    return text


def make_partner_id(normalized_name: str) -> str:
    """Stable short ID from normalized name."""
    digest = hashlib.md5(normalized_name.encode("utf-8")).hexdigest()[:10].upper()
    return f"P_{digest}"


def make_project_id(source_name: str, raw_id: str, fallback_text: str) -> str:
    raw = safe_str(raw_id) or safe_str(fallback_text)
    digest = hashlib.md5(f"{source_name}|{raw}".encode("utf-8")).hexdigest()[:12].upper()
    return f"PRJ_{digest}"


def split_orgs(raw: str) -> List[str]:
    """Conservative split for consortium-style organization fields."""
    text = safe_str(raw)
    if not text:
        return []

    # Normalize Korean list punctuation, but avoid aggressive slash split because many org names contain slashes.
    text = text.replace("，", ",").replace("、", ",")
    parts = re.split(r",|;|\n|\s+및\s+|\s*&\s+|\s+and\s+", text, flags=re.IGNORECASE)

    cleaned = []
    for part in parts:
        part = safe_str(part)
        part = re.sub(r"^[\-–—•\*\s]+", "", part)
        part = re.sub(r"[\-–—•\*\s]+$", "", part)
        if len(normalize_org_name(part)) >= 2:
            cleaned.append(part)
    return cleaned


def infer_org_type_from_name(name: str, default: str = "unknown") -> str:
    text = safe_str(name).lower()
    if any(x in text for x in ["united nations", "world health organization", "asian development bank"]):
        return "multilateral"
    if any(x in text for x in ["대학교", "university", "대학"]):
        return "university"
    if any(x in text for x in ["연구소", "institute", "research"]):
        return "research_institute"
    if any(x in text for x in ["재단", "foundation"]):
        return "foundation"
    if any(x in text for x in ["협회", "association", "사단법인", "ngo"]):
        return "nonprofit_or_association"
    if any(x in text for x in ["주식회사", "(주)", "㈜", "co.", "ltd", "inc"]):
        return "company"
    return default


def extract_year(value: Any) -> Optional[int]:
    text = safe_str(value)
    m = re.search(r"(19|20)\d{2}", text)
    if not m:
        return None
    return int(m.group(0))


def to_float(value: Any) -> Optional[float]:
    text = safe_str(value)
    if not text:
        return None
    text = re.sub(r"[^0-9\.\-]", "", text)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def compact_evidence(text: str, max_len: int = 260) -> str:
    text = re.sub(r"\s+", " ", safe_str(text))
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def find_capability_hits(text: str) -> Dict[str, List[str]]:
    lowered = safe_str(text).lower()
    result: Dict[str, List[str]] = {}
    if not lowered:
        return result

    for tag, keywords in CAPABILITY_TAGS.items():
        hits = []
        for kw in keywords:
            if kw.lower() in lowered:
                hits.append(kw)
        if hits:
            # Deduplicate while preserving order.
            result[tag] = list(dict.fromkeys(hits))
    return result


def extract_multilateral_names(text: str) -> List[Tuple[str, str, str]]:
    """Return tuples of (short_code, canonical_name, org_type)."""
    src = safe_str(text)
    if not src:
        return []

    found: List[Tuple[str, str, str]] = []
    normalized_src = src.replace("UN Habitat", "UN-HABITAT").replace("UN-Habitat", "UN-HABITAT")
    for code, meta in MULTILATERAL_PATTERNS.items():
        # Use strict word-ish boundaries to avoid false positives.
        pattern_code = re.escape(code).replace("\\-", "[- ]?")
        if re.search(rf"(?<![A-Za-z]){pattern_code}(?![A-Za-z])", normalized_src, flags=re.IGNORECASE):
            found.append((code, meta["name"], meta["type"]))
    return list(dict.fromkeys(found))


# -----------------------------------------------------------------------------
# Builder
# -----------------------------------------------------------------------------

class PartnerMasterBuilder:
    def __init__(self) -> None:
        self.partners: Dict[str, Dict[str, Any]] = {}
        self.aliases: List[Dict[str, Any]] = []
        self.sources: List[Dict[str, Any]] = []
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.participants: List[Dict[str, Any]] = []
        self.capability_evidence: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        self._alias_seen: set[Tuple[str, str, str]] = set()
        self._source_seen: set[Tuple[str, str, str, str]] = set()
        self._participant_seen: set[Tuple[str, str, str, str]] = set()
        self.created_at = now_iso()

    def add_partner(
        self,
        raw_name: str,
        source_name: str,
        org_type: str = "unknown",
        legal_type: str = "",
        country: str = "Korea",
        canonical_name_en: str = "",
        source_record_id: str = "",
        verified_field: str = "",
    ) -> Optional[str]:
        raw_name = safe_str(raw_name)
        normalized = normalize_org_name(raw_name)
        if not normalized:
            return None

        partner_id = make_partner_id(normalized)
        inferred_org_type = org_type if org_type != "unknown" else infer_org_type_from_name(raw_name, default="unknown")

        if partner_id not in self.partners:
            self.partners[partner_id] = {
                "partner_id": partner_id,
                "canonical_name_ko": raw_name,
                "canonical_name_en": canonical_name_en,
                "org_type": inferred_org_type,
                "legal_type": legal_type,
                "country": country,
                "registration_status": "unverified",
                "first_seen_source": source_name,
                "created_at": self.created_at,
                "updated_at": self.created_at,
            }
        else:
            # Prefer more informative org/legal type if newly available.
            p = self.partners[partner_id]
            if p.get("org_type") in ("unknown", "") and inferred_org_type:
                p["org_type"] = inferred_org_type
            if not p.get("legal_type") and legal_type:
                p["legal_type"] = legal_type
            if not p.get("canonical_name_en") and canonical_name_en:
                p["canonical_name_en"] = canonical_name_en

        self.add_alias(partner_id, raw_name, source_name, confidence=1.0)
        self.add_source(partner_id, source_name, source_record_id, raw_name, verified_field)
        return partner_id

    def add_alias(self, partner_id: str, alias: str, source_name: str, confidence: float = 1.0) -> None:
        alias = safe_str(alias)
        alias_norm = normalize_org_name(alias)
        if not alias_norm:
            return
        key = (partner_id, alias_norm, source_name)
        if key in self._alias_seen:
            return
        self._alias_seen.add(key)
        self.aliases.append({
            "partner_id": partner_id,
            "alias": alias,
            "alias_normalized": alias_norm,
            "source": source_name,
            "confidence": confidence,
        })

    def add_source(
        self,
        partner_id: str,
        source_name: str,
        source_record_id: str,
        raw_name: str,
        verified_field: str,
    ) -> None:
        key = (partner_id, source_name, safe_str(source_record_id), safe_str(raw_name))
        if key in self._source_seen:
            return
        self._source_seen.add(key)
        self.sources.append({
            "partner_id": partner_id,
            "source_name": source_name,
            "source_record_id": safe_str(source_record_id),
            "raw_name": safe_str(raw_name),
            "verified_field": safe_str(verified_field),
            "collected_at": self.created_at,
        })

    def add_project(self, project: Dict[str, Any]) -> str:
        project_id = safe_str(project["project_id"])
        if project_id not in self.projects:
            self.projects[project_id] = project
        return project_id

    def add_participant(
        self,
        project_id: str,
        partner_id: str,
        raw_name: str,
        role: str,
        source_name: str,
        evidence_text: str,
        confidence: float = 1.0,
    ) -> None:
        key = (project_id, partner_id, role, source_name)
        if key in self._participant_seen:
            return
        self._participant_seen.add(key)
        self.participants.append({
            "project_id": project_id,
            "partner_id": partner_id,
            "raw_name": safe_str(raw_name),
            "role": role,
            "source_name": source_name,
            "confidence": confidence,
            "evidence_text": compact_evidence(evidence_text),
        })

    def add_capability_evidence(
        self,
        partner_id: str,
        text: str,
        source_name: str,
        evidence_ref: str,
        year: Optional[int] = None,
        weight: float = 1.0,
    ) -> None:
        hits_by_tag = find_capability_hits(text)
        for tag, hits in hits_by_tag.items():
            self.capability_evidence[(partner_id, tag)].append({
                "source_name": source_name,
                "evidence_ref": safe_str(evidence_ref),
                "year": year,
                "hits": hits,
                "text": compact_evidence(text),
                "weight": weight,
            })

    # -------------------------------------------------------------------------
    # Source loaders
    # -------------------------------------------------------------------------

    def load_nonprofit_national(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        required = {"단체명"}
        missing = required - set(df.columns)
        if missing:
            logging.warning("nonprofit_national missing columns: %s", sorted(missing))
            return

        for idx, row in df.iterrows():
            name = safe_str(row.get("단체명"))
            if not name:
                continue
            source_record_id = safe_str(row.get("등록번호")) or str(idx)
            legal_type = safe_str(row.get("유형"))
            registration_body = safe_str(row.get("등록기관"))
            partner_id = self.add_partner(
                raw_name=name,
                source_name="nonprofit_national",
                org_type="domestic_nonprofit",
                legal_type=legal_type,
                country="Korea",
                source_record_id=source_record_id,
                verified_field="단체명",
            )
            if not partner_id:
                continue

            # Nonprofit registry is a weak but useful legal/eligibility signal.
            self.partners[partner_id]["registration_status"] = "registry_verified"

            evidence = " ".join([
                name,
                safe_str(row.get("주된사업")),
                registration_body,
                safe_str(row.get("주관과")),
            ])
            weight = 1.2 if registration_body in RELEVANT_REGISTRATION_BODIES else 0.8
            self.add_capability_evidence(
                partner_id=partner_id,
                text=evidence,
                source_name="nonprofit_national",
                evidence_ref=source_record_id,
                year=extract_year(row.get("등록일")),
                weight=weight,
            )

    def load_koica_humanitarian(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        required = {"수행기관", "사업명_국문"}
        missing = required - set(df.columns)
        if missing:
            logging.warning("koica_humanitarian missing columns: %s", sorted(missing))
            return

        for idx, row in df.iterrows():
            project_title_ko = safe_str(row.get("사업명_국문"))
            project_title_en = safe_str(row.get("사업명_영문"))
            raw_project_id = safe_str(row.get("사업번호")) or safe_str(row.get("번호")) or str(idx)
            project_id = make_project_id("koica_humanitarian", raw_project_id, project_title_ko)
            start_year = extract_year(row.get("시작연도"))
            end_year = extract_year(row.get("종료연도"))
            budget = to_float(row.get("예산총액_원화"))
            evidence_text = " ".join([
                project_title_ko,
                project_title_en,
                safe_str(row.get("국가명")),
                safe_str(row.get("지역")),
                safe_str(row.get("담당부서")),
            ])

            self.add_project({
                "project_id": project_id,
                "source_name": "koica_humanitarian",
                "source_record_id": raw_project_id,
                "project_title_ko": project_title_ko,
                "project_title_en": project_title_en,
                "country": safe_str(row.get("국가명")),
                "region": safe_str(row.get("지역")),
                "sector": safe_str(row.get("담당부서")),
                "start_year": start_year,
                "end_year": end_year,
                "budget_krw": budget,
                "description": compact_evidence(evidence_text, max_len=500),
            })

            for raw_org in split_orgs(row.get("수행기관")):
                partner_id = self.add_partner(
                    raw_name=raw_org,
                    source_name="koica_humanitarian",
                    org_type="domestic_oda_implementer",
                    legal_type="",
                    country="Korea",
                    source_record_id=raw_project_id,
                    verified_field="수행기관",
                )
                if not partner_id:
                    continue
                self.add_participant(
                    project_id=project_id,
                    partner_id=partner_id,
                    raw_name=raw_org,
                    role="implementing_partner",
                    source_name="koica_humanitarian",
                    evidence_text=evidence_text,
                    confidence=0.95,
                )
                self.add_capability_evidence(
                    partner_id=partner_id,
                    text=evidence_text,
                    source_name="koica_humanitarian",
                    evidence_ref=project_id,
                    year=end_year or start_year,
                    weight=1.5,
                )

    def load_koica_iati(self, df: pd.DataFrame) -> None:
        """
        IATI file does not usually contain domestic contractors in the available columns.
        We use it mainly to add multilateral / international partner footprint when an agency
        code appears in project title or description.
        """
        if df.empty:
            return
        title_cols = [c for c in ["사업명(한글)", "사업명(영문)", "사업설명(한글)", "사업설명(영문)"] if c in df.columns]
        if not title_cols:
            logging.warning("koica_iati has no expected title/description columns")
            return

        for idx, row in df.iterrows():
            project_title_ko = safe_str(row.get("사업명(한글)"))
            project_title_en = safe_str(row.get("사업명(영문)"))
            project_no = safe_str(row.get("프로젝트 번호")) or str(idx)
            project_id = make_project_id("koica_iati", project_no, project_title_ko or project_title_en)
            evidence_text = " ".join(safe_str(row.get(c)) for c in title_cols)
            country = safe_str(row.get("수원국"))
            sector = safe_str(row.get("사업분야명"))
            start_year = extract_year(row.get("사업착수계획년월")) or extract_year(row.get("집행시작예정일"))
            end_year = extract_year(row.get("사업완료계획년월")) or extract_year(row.get("집행종료예정일"))
            budget = to_float(row.get("총사업비(원화)")) or to_float(row.get("예산금액(원화)"))

            multilaterals = extract_multilateral_names(evidence_text)
            if not multilaterals:
                continue

            self.add_project({
                "project_id": project_id,
                "source_name": "koica_iati",
                "source_record_id": project_no,
                "project_title_ko": project_title_ko,
                "project_title_en": project_title_en,
                "country": country,
                "region": safe_str(row.get("수원지역")),
                "sector": sector,
                "start_year": start_year,
                "end_year": end_year,
                "budget_krw": budget,
                "description": compact_evidence(evidence_text, max_len=500),
            })

            for code, canonical_name, org_type in multilaterals:
                partner_id = self.add_partner(
                    raw_name=code,
                    source_name="koica_iati",
                    org_type=org_type,
                    legal_type="international_organization",
                    country="International",
                    canonical_name_en=canonical_name,
                    source_record_id=project_no,
                    verified_field="사업명/설명 내 기관 약어",
                )
                if not partner_id:
                    continue
                self.add_alias(partner_id, canonical_name, "koica_iati", confidence=0.95)
                self.add_participant(
                    project_id=project_id,
                    partner_id=partner_id,
                    raw_name=code,
                    role="multilateral_partner_mentioned",
                    source_name="koica_iati",
                    evidence_text=evidence_text,
                    confidence=0.7,
                )
                self.add_capability_evidence(
                    partner_id=partner_id,
                    text=evidence_text,
                    source_name="koica_iati",
                    evidence_ref=project_id,
                    year=end_year or start_year,
                    weight=1.0,
                )

    # -------------------------------------------------------------------------
    # Output assembly
    # -------------------------------------------------------------------------

    def build_capabilities_df(self) -> pd.DataFrame:
        rows = []
        for (partner_id, tag), evidences in sorted(self.capability_evidence.items()):
            if not evidences:
                continue
            all_hits: List[str] = []
            years: List[int] = []
            weighted_hit_score = 0.0
            for ev in evidences:
                hits = ev.get("hits", [])
                all_hits.extend(hits)
                if ev.get("year"):
                    years.append(int(ev["year"]))
                weighted_hit_score += len(hits) * 8 * float(ev.get("weight", 1.0))

            unique_hits = list(dict.fromkeys(all_hits))
            evidence_count = len(evidences)
            recency_bonus = 0.0
            last_year = max(years) if years else None
            current_year = datetime.now().year
            if last_year:
                age = max(0, current_year - last_year)
                recency_bonus = max(0, 10 - age)

            source_bonus = min(15, evidence_count * 3)
            score = min(100.0, round(weighted_hit_score + source_bonus + recency_bonus, 1))
            summaries = []
            for ev in evidences[:4]:
                summaries.append(f"[{ev['source_name']}] {ev['text']}")

            rows.append({
                "partner_id": partner_id,
                "capability_tag": tag,
                "score": score,
                "evidence_count": evidence_count,
                "last_evidence_year": last_year,
                "evidence_keywords": ", ".join(unique_hits[:20]),
                "evidence_summary": " | ".join(summaries),
            })
        return pd.DataFrame(rows).sort_values(["score", "evidence_count"], ascending=[False, False]) if rows else pd.DataFrame()

    def build_partners_df(self, capabilities_df: pd.DataFrame) -> pd.DataFrame:
        projects_by_partner = defaultdict(set)
        for part in self.participants:
            projects_by_partner[part["partner_id"]].add(part["project_id"])

        sources_by_partner = defaultdict(set)
        for src in self.sources:
            sources_by_partner[src["partner_id"]].add(src["source_name"])

        caps_by_partner = defaultdict(list)
        if not capabilities_df.empty:
            for _, row in capabilities_df.iterrows():
                caps_by_partner[row["partner_id"]].append(row["capability_tag"])

        rows = []
        for partner_id, p in self.partners.items():
            rows.append({
                **p,
                "source_count": len(sources_by_partner[partner_id]),
                "project_count": len(projects_by_partner[partner_id]),
                "capability_count": len(caps_by_partner[partner_id]),
                "top_capabilities": ", ".join(caps_by_partner[partner_id][:5]),
            })
        return pd.DataFrame(rows).sort_values(["project_count", "source_count", "canonical_name_ko"], ascending=[False, False, True])

    def write_outputs(self, out_dir: Path) -> Dict[str, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)

        capabilities_df = self.build_capabilities_df()
        partners_df = self.build_partners_df(capabilities_df)
        aliases_df = pd.DataFrame(self.aliases)
        sources_df = pd.DataFrame(self.sources)
        projects_df = pd.DataFrame(self.projects.values())
        participants_df = pd.DataFrame(self.participants)

        summary_df = self.build_summary_df(partners_df, capabilities_df)

        outputs = {
            "partners": out_dir / "partners.csv",
            "partner_aliases": out_dir / "partner_aliases.csv",
            "partner_sources": out_dir / "partner_sources.csv",
            "partner_projects": out_dir / "partner_projects.csv",
            "project_participants": out_dir / "project_participants.csv",
            "partner_capabilities": out_dir / "partner_capabilities.csv",
            "partner_master_summary": out_dir / "partner_master_summary.csv",
        }

        partners_df.to_csv(outputs["partners"], index=False, encoding="utf-8-sig")
        aliases_df.to_csv(outputs["partner_aliases"], index=False, encoding="utf-8-sig")
        sources_df.to_csv(outputs["partner_sources"], index=False, encoding="utf-8-sig")
        projects_df.to_csv(outputs["partner_projects"], index=False, encoding="utf-8-sig")
        participants_df.to_csv(outputs["project_participants"], index=False, encoding="utf-8-sig")
        capabilities_df.to_csv(outputs["partner_capabilities"], index=False, encoding="utf-8-sig")
        summary_df.to_csv(outputs["partner_master_summary"], index=False, encoding="utf-8-sig")

        return outputs

    def build_summary_df(self, partners_df: pd.DataFrame, capabilities_df: pd.DataFrame) -> pd.DataFrame:
        if partners_df.empty:
            return pd.DataFrame()
        if capabilities_df.empty:
            return partners_df.copy()

        top_cap = capabilities_df.sort_values("score", ascending=False).groupby("partner_id").head(3)
        cap_pivot = top_cap.groupby("partner_id").apply(
            lambda g: " / ".join(f"{r.capability_tag}({r.score})" for r in g.itertuples())
        ).reset_index(name="top_capability_scores")

        out = partners_df.merge(cap_pivot, on="partner_id", how="left")
        preferred_cols = [
            "partner_id", "canonical_name_ko", "canonical_name_en", "org_type", "legal_type",
            "registration_status", "source_count", "project_count", "capability_count",
            "top_capabilities", "top_capability_scores", "first_seen_source",
        ]
        return out[[c for c in preferred_cols if c in out.columns]]


def build_partner_master(data_dir: Path, out_dir: Path) -> Dict[str, Path]:
    logging.info("Reading input CSVs from %s", data_dir)
    humanitarian = read_csv_safely(data_dir / "koica_humanitarian.csv")
    iati = read_csv_safely(data_dir / "koica_iati.csv")
    nonprofit = read_csv_safely(data_dir / "nonprofit_national.csv")

    logging.info("Rows loaded: humanitarian=%s, iati=%s, nonprofit=%s", len(humanitarian), len(iati), len(nonprofit))

    builder = PartnerMasterBuilder()
    builder.load_nonprofit_national(nonprofit)
    builder.load_koica_humanitarian(humanitarian)
    builder.load_koica_iati(iati)

    outputs = builder.write_outputs(out_dir)
    logging.info("Build complete. partners=%s, projects=%s, participants=%s, capabilities=%s",
                 len(builder.partners), len(builder.projects), len(builder.participants), len(builder.capability_evidence))
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Partner Master DB CSVs from ODA data sources.")
    parser.add_argument("--data-dir", default="data", help="Directory containing input CSV files. Default: ./data")
    parser.add_argument("--out-dir", default="partner_db", help="Directory to write output CSVs. Default: ./partner_db")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")
    outputs = build_partner_master(Path(args.data_dir), Path(args.out_dir))
    print("\nGenerated Partner Master DB files:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
