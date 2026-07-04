"""
Seed mock procurement / co-delivery evidence into Partner Master DB.

Purpose
-------
Use this only for demo / simulation when live KOICA-Nara API ingestion is not yet
complete. All generated evidence is explicitly marked as mock through:
- partner_id prefix: MOCK_
- source_name: mock_procurement_seed
- evidence_text prefix: [MOCK]
- registration_status: mock

Usage
-----
python mock_procurement_seed.py --partner-db ./partner_db
python mock_procurement_seed.py --partner-db ./partner_db --reset-mock
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

SOURCE = "mock_procurement_seed"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

PARTNERS_COLUMNS = [
    "partner_id", "canonical_name_ko", "canonical_name_en", "org_type", "legal_type", "country",
    "registration_status", "first_seen_source", "created_at", "updated_at", "source_count",
    "project_count", "capability_count", "top_capabilities",
]
SUMMARY_COLUMNS = [
    "partner_id", "canonical_name_ko", "canonical_name_en", "org_type", "legal_type", "registration_status",
    "source_count", "project_count", "capability_count", "top_capabilities", "top_capability_scores",
    "first_seen_source",
]
ALIASES_COLUMNS = ["partner_id", "alias", "alias_normalized", "source", "confidence"]
SOURCES_COLUMNS = ["partner_id", "source_name", "source_record_id", "raw_name", "verified_field", "collected_at"]
PROJECTS_COLUMNS = [
    "project_id", "source_name", "source_record_id", "project_title_ko", "project_title_en", "country",
    "region", "sector", "start_year", "end_year", "budget_krw", "description",
]
PARTICIPANTS_COLUMNS = ["project_id", "partner_id", "raw_name", "role", "source_name", "confidence", "evidence_text"]
CAPABILITIES_COLUMNS = [
    "partner_id", "capability_tag", "score", "evidence_count", "last_evidence_year",
    "evidence_keywords", "evidence_summary",
]
RECORDS_COLUMNS = [
    "source_name", "record_type", "source_record_id", "title", "supplier_raw", "buyer",
    "bid_notice_no", "contract_no", "amount_krw", "date_raw", "year", "country", "method",
    "raw_json", "evidence_text",
]
EDGES_COLUMNS = ["partner_a", "partner_b", "relation_type", "project_id", "evidence_text", "weight"]

CAPABILITY_KEYWORDS = {
    "ODA_PMC": "PMC, 사업관리, 성과관리, PDM, M&E, 모니터링, 평가, 산출물 관리",
    "project_design_policy_research": "정책연구, 전략, 타당성, 예비조사, baseline, 기초선, 컨설팅, 마스터플랜, 관리계획, 매뉴얼",
    "forestry_restoration": "산림, 임업, 조림, 복원, 생태, 맹그로브, mangrove, forest, restoration, biodiversity, 습지",
    "GIS_remote_sensing": "GIS, 드론, drone, 원격탐사, remote sensing, mapping, 매핑, 공간정보, GPS, 위성, 데이터",
    "aquaculture_livelihood": "양식, 수산, 어업, aquaculture, shrimp, 새우, livelihood, 생계, 소득, 커뮤니티, 주민, 가치사슬",
    "capacity_building_training": "역량강화, capacity building, 교육, training, 연수, 훈련, 워크숍, 초청연수, 교육프로그램, 인식제고",
    "construction_infrastructure": "건축, 건설, 시공, 리모델링, infrastructure, building, construction, 센터, 설계, 시설",
    "procurement_equipment": "기자재, 장비, 조달, equipment, procurement, 실험실, laboratory, 차량, IT 장비, device",
    "education_youth": "교육, 학생, 청소년, curriculum, 교재, 홍보자료, 인식제고",
}

MOCK_PARTNERS = [
    {
        "partner_id": "MOCK_GEOICT",
        "ko": "그린지오매틱스컨소시엄",
        "en": "Green Geomatics Consortium",
        "org_type": "domestic_company_consulting",
        "legal_type": "주식회사/컨소시엄",
        "caps": {
            "GIS_remote_sensing": 96,
            "project_design_policy_research": 72,
            "procurement_equipment": 68,
        },
    },
    {
        "partner_id": "MOCK_MANGROVE_RESTORE",
        "ko": "한국맹그로브복원센터",
        "en": "Korea Mangrove Restoration Center",
        "org_type": "domestic_research_ngo",
        "legal_type": "사단법인/연구기관",
        "caps": {
            "forestry_restoration": 98,
            "project_design_policy_research": 76,
            "capacity_building_training": 65,
        },
    },
    {
        "partner_id": "MOCK_BLUECARBON",
        "ko": "블루카본생태연구원",
        "en": "Blue Carbon Ecology Institute",
        "org_type": "domestic_research_institute",
        "legal_type": "비영리연구기관",
        "caps": {
            "forestry_restoration": 88,
            "GIS_remote_sensing": 74,
            "project_design_policy_research": 92,
            "ODA_PMC": 70,
        },
    },
    {
        "partner_id": "MOCK_FISH_LIVELIHOOD",
        "ko": "해양수산생계혁신원",
        "en": "Marine Fisheries Livelihood Innovation Institute",
        "org_type": "domestic_technical_institute",
        "legal_type": "사단법인/전문기관",
        "caps": {
            "aquaculture_livelihood": 97,
            "capacity_building_training": 74,
            "project_design_policy_research": 65,
        },
    },
    {
        "partner_id": "MOCK_CAPACITY_CENTER",
        "ko": "글로벌ODA역량센터",
        "en": "Global ODA Capacity Center",
        "org_type": "domestic_oda_training",
        "legal_type": "사단법인",
        "caps": {
            "capacity_building_training": 98,
            "education_youth": 82,
            "ODA_PMC": 84,
            "project_design_policy_research": 62,
        },
    },
    {
        "partner_id": "MOCK_INFRA_ARCH",
        "ko": "에코인프라건축사사무소",
        "en": "Eco Infrastructure Architects",
        "org_type": "domestic_architecture_engineering",
        "legal_type": "건축사사무소/엔지니어링",
        "caps": {
            "construction_infrastructure": 99,
            "procurement_equipment": 70,
            "ODA_PMC": 58,
        },
    },
    {
        "partner_id": "MOCK_EQUIPMENT",
        "ko": "ODA장비조달솔루션",
        "en": "ODA Equipment Procurement Solutions",
        "org_type": "domestic_procurement_company",
        "legal_type": "주식회사",
        "caps": {
            "procurement_equipment": 98,
            "GIS_remote_sensing": 70,
            "construction_infrastructure": 62,
        },
    },
    {
        "partner_id": "MOCK_MNE",
        "ko": "국제개발성과관리연구소",
        "en": "International Development M&E Institute",
        "org_type": "domestic_oda_consulting",
        "legal_type": "사단법인/컨설팅기관",
        "caps": {
            "ODA_PMC": 97,
            "project_design_policy_research": 94,
            "capacity_building_training": 72,
        },
    },
    {
        "partner_id": "MOCK_COMMUNITY",
        "ko": "커뮤니티임팩트랩",
        "en": "Community Impact Lab",
        "org_type": "domestic_ngo",
        "legal_type": "비영리민간단체",
        "caps": {
            "aquaculture_livelihood": 86,
            "capacity_building_training": 88,
            "education_youth": 80,
        },
    },
    {
        "partner_id": "MOCK_CLIMATE_ECO",
        "ko": "한국기후생태컨설팅",
        "en": "Korea Climate Ecology Consulting",
        "org_type": "domestic_consulting",
        "legal_type": "주식회사/전문컨설팅",
        "caps": {
            "forestry_restoration": 78,
            "ODA_PMC": 82,
            "project_design_policy_research": 86,
            "construction_infrastructure": 66,
        },
    },
]

MOCK_CONTRACTS = [
    {
        "project_id": "MOCK_PRJ_2024_SRI_MANGROVE_PMC",
        "title": "스리랑카 맹그로브 생태계 복원 사업 예비조사 및 PMC 용역",
        "title_en": "Sri Lanka Mangrove Ecosystem Restoration Preliminary Survey and PMC",
        "country": "스리랑카",
        "region": "서남아시아",
        "sector": "농림수산/환경/PMC",
        "year": 2024,
        "amount": 480000000,
        "method": "제한경쟁/협상에 의한 계약",
        "partners": ["MOCK_MNE", "MOCK_MANGROVE_RESTORE"],
        "roles": ["lead_pmc", "technical_partner"],
        "tags": ["ODA_PMC", "project_design_policy_research", "forestry_restoration"],
    },
    {
        "project_id": "MOCK_PRJ_2024_FOREST_GIS_MASTERPLAN",
        "title": "개도국 산림공간정보 기반 맹그로브 관리계획 수립 용역",
        "title_en": "Forest GIS-based Mangrove Management Plan Consulting",
        "country": "스리랑카",
        "region": "서남아시아",
        "sector": "산림/ICT/GIS",
        "year": 2024,
        "amount": 620000000,
        "method": "공동수급/협상에 의한 계약",
        "partners": ["MOCK_GEOICT", "MOCK_BLUECARBON"],
        "roles": ["gis_lead", "ecosystem_research"],
        "tags": ["GIS_remote_sensing", "project_design_policy_research", "forestry_restoration"],
    },
    {
        "project_id": "MOCK_PRJ_2025_MANGROVE_RESTORATION",
        "title": "해안습지 및 맹그로브 훼손지 복원 실행관리 용역",
        "title_en": "Coastal Wetland and Mangrove Restoration Implementation Management",
        "country": "스리랑카",
        "region": "서남아시아",
        "sector": "산림/환경/복원",
        "year": 2025,
        "amount": 910000000,
        "method": "공동수급/일반경쟁",
        "partners": ["MOCK_MANGROVE_RESTORE", "MOCK_COMMUNITY"],
        "roles": ["restoration_lead", "community_engagement"],
        "tags": ["forestry_restoration", "capacity_building_training", "aquaculture_livelihood"],
    },
    {
        "project_id": "MOCK_PRJ_2025_AQUA_LIVELIHOOD",
        "title": "맹그로브 기반 양식 및 주민소득 창출 시범사업 용역",
        "title_en": "Mangrove-based Aquaculture and Livelihood Pilot Project",
        "country": "스리랑카",
        "region": "서남아시아",
        "sector": "수산/농업/생계",
        "year": 2025,
        "amount": 530000000,
        "method": "공동수급/협상에 의한 계약",
        "partners": ["MOCK_FISH_LIVELIHOOD", "MOCK_COMMUNITY"],
        "roles": ["aquaculture_lead", "community_training"],
        "tags": ["aquaculture_livelihood", "capacity_building_training"],
    },
    {
        "project_id": "MOCK_PRJ_2025_CAPACITY_TRAINING",
        "title": "환경부 공무원 맹그로브 관리 역량강화 초청연수 및 현지 워크숍",
        "title_en": "Capacity Building Training and Local Workshops for Mangrove Management Officials",
        "country": "스리랑카",
        "region": "서남아시아",
        "sector": "교육/역량강화",
        "year": 2025,
        "amount": 390000000,
        "method": "공동수급/수의계약 목업",
        "partners": ["MOCK_CAPACITY_CENTER", "MOCK_MNE"],
        "roles": ["training_lead", "mne_support"],
        "tags": ["capacity_building_training", "ODA_PMC", "education_youth"],
    },
    {
        "project_id": "MOCK_PRJ_2025_EDU_CENTER_INFRA",
        "title": "맹그로브 교육센터 신축 및 정보센터 리모델링 설계·감리 용역",
        "title_en": "Mangrove Education Center Construction and Information Center Remodeling Design",
        "country": "스리랑카",
        "region": "서남아시아",
        "sector": "건축/인프라",
        "year": 2025,
        "amount": 1250000000,
        "method": "공동수급/제한경쟁",
        "partners": ["MOCK_INFRA_ARCH", "MOCK_CLIMATE_ECO"],
        "roles": ["architecture_lead", "environmental_planning"],
        "tags": ["construction_infrastructure", "ODA_PMC", "project_design_policy_research"],
    },
    {
        "project_id": "MOCK_PRJ_2025_EQUIPMENT_PROCUREMENT",
        "title": "드론·GPS·실험 기자재 및 IT 장비 조달 패키지",
        "title_en": "Drone, GPS, Laboratory and IT Equipment Procurement Package",
        "country": "스리랑카",
        "region": "서남아시아",
        "sector": "조달/ICT/장비",
        "year": 2025,
        "amount": 730000000,
        "method": "공동수급/물품·용역 혼합 목업",
        "partners": ["MOCK_EQUIPMENT", "MOCK_GEOICT"],
        "roles": ["procurement_lead", "technical_specification"],
        "tags": ["procurement_equipment", "GIS_remote_sensing"],
    },
    {
        "project_id": "MOCK_PRJ_2023_BLUECARBON_MRV",
        "title": "블루카본 PDD 및 산림탄소 MRV 체계 기초선 조사",
        "title_en": "Blue Carbon PDD and Forest Carbon MRV Baseline Survey",
        "country": "스리랑카",
        "region": "서남아시아",
        "sector": "기후/산림/성과관리",
        "year": 2023,
        "amount": 410000000,
        "method": "공동수급/협상에 의한 계약",
        "partners": ["MOCK_BLUECARBON", "MOCK_MNE"],
        "roles": ["bluecarbon_research", "mne_pdm"],
        "tags": ["project_design_policy_research", "ODA_PMC", "forestry_restoration"],
    },
    {
        "project_id": "MOCK_PRJ_2024_COMMUNITY_WORKSHOP",
        "title": "수원국 지역주민 생계조사 및 커뮤니티 기반 워크숍 운영",
        "title_en": "Community Livelihood Survey and Workshop Operation",
        "country": "스리랑카",
        "region": "서남아시아",
        "sector": "지역개발/교육/생계",
        "year": 2024,
        "amount": 280000000,
        "method": "공동수급/수의계약 목업",
        "partners": ["MOCK_CAPACITY_CENTER", "MOCK_COMMUNITY"],
        "roles": ["training_facilitation", "community_mobilization"],
        "tags": ["capacity_building_training", "aquaculture_livelihood", "education_youth"],
    },
    {
        "project_id": "MOCK_PRJ_2023_DRONE_MAPPING",
        "title": "드론 기반 연안생태계 매핑 및 조사 매뉴얼 개발",
        "title_en": "Drone-based Coastal Ecosystem Mapping and Survey Manual Development",
        "country": "스리랑카",
        "region": "서남아시아",
        "sector": "ICT/GIS/조사",
        "year": 2023,
        "amount": 360000000,
        "method": "제한경쟁/단독계약 목업",
        "partners": ["MOCK_GEOICT"],
        "roles": ["gis_drone_lead"],
        "tags": ["GIS_remote_sensing", "project_design_policy_research"],
    },
]


def normalize_alias(value: str) -> str:
    text = str(value or "").lower()
    for token in ["사단법인", "재단법인", "(사)", "㈔", "(재)", "주식회사", "(주)", "inc.", "ltd."]:
        text = text.replace(token, "")
    text = re.sub(r"[\s\.\,\-\_\(\)\[\]·/]", "", text)
    return text


def read_csv(path: Path, columns: List[str]) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    for enc in ["utf-8-sig", "utf-8", "cp949"]:
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc).fillna("")
            for c in columns:
                if c not in df.columns:
                    df[c] = ""
            return df[columns]
        except Exception:
            continue
    raise RuntimeError(f"Could not read {path}")


def write_csv(df: pd.DataFrame, path: Path, columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for c in columns:
        if c not in df.columns:
            df[c] = ""
    df = df[columns].fillna("")
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def dedupe(df: pd.DataFrame, subset: List[str]) -> pd.DataFrame:
    if df.empty:
        return df
    return df.drop_duplicates(subset=subset, keep="last").reset_index(drop=True)


def remove_mock_rows(tables: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    mock_ids = {p["partner_id"] for p in MOCK_PARTNERS}
    mock_project_ids = {p["project_id"] for p in MOCK_CONTRACTS}

    def not_mock_source(df: pd.DataFrame) -> pd.Series:
        if "source_name" in df.columns:
            return ~df["source_name"].astype(str).eq(SOURCE)
        return pd.Series([True] * len(df), index=df.index)

    tables["partners"] = tables["partners"][~tables["partners"]["partner_id"].isin(mock_ids)].copy()
    tables["summary"] = tables["summary"][~tables["summary"]["partner_id"].isin(mock_ids)].copy()
    tables["aliases"] = tables["aliases"][~tables["aliases"]["partner_id"].isin(mock_ids)].copy()
    tables["sources"] = tables["sources"][not_mock_source(tables["sources"])].copy()
    tables["projects"] = tables["projects"][~tables["projects"]["project_id"].isin(mock_project_ids)].copy()
    tables["participants"] = tables["participants"][~tables["participants"]["project_id"].isin(mock_project_ids)].copy()
    tables["capabilities"] = tables["capabilities"][~tables["capabilities"]["partner_id"].isin(mock_ids)].copy()
    tables["records"] = tables["records"][~tables["records"].get("source_name", pd.Series(dtype=str)).astype(str).eq(SOURCE)].copy()
    tables["edges"] = tables["edges"][~tables["edges"]["project_id"].isin(mock_project_ids)].copy()
    return tables


def build_partner_rows() -> Dict[str, List[Dict[str, Any]]]:
    partners, summaries, aliases, sources, capabilities = [], [], [], [], []

    # Project count per partner.
    project_count = {p["partner_id"]: 0 for p in MOCK_PARTNERS}
    last_year = {p["partner_id"]: 2025 for p in MOCK_PARTNERS}
    for c in MOCK_CONTRACTS:
        for pid in c["partners"]:
            project_count[pid] = project_count.get(pid, 0) + 1
            last_year[pid] = max(last_year.get(pid, 0), c["year"])

    for p in MOCK_PARTNERS:
        pid = p["partner_id"]
        caps_sorted = sorted(p["caps"].items(), key=lambda kv: kv[1], reverse=True)
        top_caps = ", ".join([c for c, _ in caps_sorted[:5]])
        top_scores = " / ".join([f"{c}({score:.1f})" for c, score in caps_sorted[:3]])
        partners.append({
            "partner_id": pid,
            "canonical_name_ko": p["ko"],
            "canonical_name_en": p["en"],
            "org_type": p["org_type"],
            "legal_type": p["legal_type"],
            "country": "Korea",
            "registration_status": "mock",
            "first_seen_source": SOURCE,
            "created_at": NOW,
            "updated_at": NOW,
            "source_count": "2",
            "project_count": str(project_count.get(pid, 0)),
            "capability_count": str(len(p["caps"])),
            "top_capabilities": top_caps,
        })
        summaries.append({
            "partner_id": pid,
            "canonical_name_ko": p["ko"],
            "canonical_name_en": p["en"],
            "org_type": p["org_type"],
            "legal_type": p["legal_type"],
            "registration_status": "mock",
            "source_count": "2",
            "project_count": str(project_count.get(pid, 0)),
            "capability_count": str(len(p["caps"])),
            "top_capabilities": top_caps,
            "top_capability_scores": top_scores,
            "first_seen_source": SOURCE,
        })
        for alias in [p["ko"], p["en"], p["ko"].replace("컨소시엄", ""), p["ko"].replace("연구원", "")]:
            aliases.append({
                "partner_id": pid,
                "alias": alias,
                "alias_normalized": normalize_alias(alias),
                "source": SOURCE,
                "confidence": "1.0",
            })
        sources.append({
            "partner_id": pid,
            "source_name": SOURCE,
            "source_record_id": f"{pid}_PROFILE",
            "raw_name": p["ko"],
            "verified_field": "mock_profile",
            "collected_at": NOW,
        })
        for cap, score in p["caps"].items():
            summaries_for_pid = [c for c in MOCK_CONTRACTS if pid in c["partners"] and cap in c["tags"]]
            evidence_titles = " | ".join([f"[MOCK] {c['title']}" for c in summaries_for_pid[:3]])
            if not evidence_titles:
                evidence_titles = f"[MOCK] simulated capability evidence for {p['ko']}"
            capabilities.append({
                "partner_id": pid,
                "capability_tag": cap,
                "score": f"{score:.1f}",
                "evidence_count": str(max(2, len(summaries_for_pid) * 2)),
                "last_evidence_year": str(last_year.get(pid, 2025)),
                "evidence_keywords": CAPABILITY_KEYWORDS.get(cap, cap),
                "evidence_summary": evidence_titles,
            })
    return {
        "partners": partners,
        "summary": summaries,
        "aliases": aliases,
        "sources": sources,
        "capabilities": capabilities,
    }


def build_project_rows() -> Dict[str, List[Dict[str, Any]]]:
    name = {p["partner_id"]: p["ko"] for p in MOCK_PARTNERS}
    projects, participants, records, edges = [], [], [], []
    for c in MOCK_CONTRACTS:
        supplier_names = [name[pid] for pid in c["partners"]]
        supplier_raw = " + ".join(supplier_names)
        evidence = f"[MOCK] {c['year']} simulated procurement evidence: {c['title']} / suppliers={supplier_raw}"
        projects.append({
            "project_id": c["project_id"],
            "source_name": SOURCE,
            "source_record_id": c["project_id"],
            "project_title_ko": c["title"],
            "project_title_en": c["title_en"],
            "country": c["country"],
            "region": c["region"],
            "sector": c["sector"],
            "start_year": str(c["year"]),
            "end_year": str(c["year"] + 1),
            "budget_krw": str(c["amount"]),
            "description": evidence + " / tags=" + ", ".join(c["tags"]),
        })
        records.append({
            "source_name": SOURCE,
            "record_type": "mock_nara_koica_contract",
            "source_record_id": c["project_id"],
            "title": c["title"],
            "supplier_raw": supplier_raw,
            "buyer": "한국국제협력단(KOICA)",
            "bid_notice_no": f"MOCK-{c['year']}-{len(records)+1:04d}",
            "contract_no": c["project_id"],
            "amount_krw": str(c["amount"]),
            "date_raw": f"{c['year']}0630",
            "year": str(c["year"]),
            "country": c["country"],
            "method": c["method"],
            "raw_json": json.dumps(c, ensure_ascii=False),
            "evidence_text": evidence,
        })
        for pid, role in zip(c["partners"], c["roles"]):
            participants.append({
                "project_id": c["project_id"],
                "partner_id": pid,
                "raw_name": name[pid],
                "role": role,
                "source_name": SOURCE,
                "confidence": "0.99",
                "evidence_text": evidence,
            })
        if len(c["partners"]) >= 2:
            for i in range(len(c["partners"])):
                for j in range(i + 1, len(c["partners"])):
                    edges.append({
                        # Store display names because graph_view nodes use display names.
                        "partner_a": name[c["partners"][i]],
                        "partner_b": name[c["partners"][j]],
                        "relation_type": "mock_joint_contract",
                        "project_id": c["project_id"],
                        "evidence_text": evidence,
                        "weight": "4.0",
                    })
    return {"projects": projects, "participants": participants, "records": records, "edges": edges}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partner-db", default="./partner_db", help="Partner DB directory")
    parser.add_argument("--reset-mock", action="store_true", help="Remove existing mock rows before seeding")
    args = parser.parse_args()

    db = Path(args.partner_db)
    db.mkdir(parents=True, exist_ok=True)

    tables = {
        "partners": read_csv(db / "partners.csv", PARTNERS_COLUMNS),
        "summary": read_csv(db / "partner_master_summary.csv", SUMMARY_COLUMNS),
        "aliases": read_csv(db / "partner_aliases.csv", ALIASES_COLUMNS),
        "sources": read_csv(db / "partner_sources.csv", SOURCES_COLUMNS),
        "projects": read_csv(db / "partner_projects.csv", PROJECTS_COLUMNS),
        "participants": read_csv(db / "project_participants.csv", PARTICIPANTS_COLUMNS),
        "capabilities": read_csv(db / "partner_capabilities.csv", CAPABILITIES_COLUMNS),
        "records": read_csv(db / "procurement_records.csv", RECORDS_COLUMNS),
        "edges": read_csv(db / "partner_edges.csv", EDGES_COLUMNS),
    }

    # Always remove previous mock rows first to avoid duplicates.
    tables = remove_mock_rows(tables)

    partner_rows = build_partner_rows()
    project_rows = build_project_rows()

    tables["partners"] = pd.concat([tables["partners"], pd.DataFrame(partner_rows["partners"])], ignore_index=True)
    tables["summary"] = pd.concat([tables["summary"], pd.DataFrame(partner_rows["summary"])], ignore_index=True)
    tables["aliases"] = pd.concat([tables["aliases"], pd.DataFrame(partner_rows["aliases"])], ignore_index=True)
    tables["sources"] = pd.concat([tables["sources"], pd.DataFrame(partner_rows["sources"])], ignore_index=True)
    tables["capabilities"] = pd.concat([tables["capabilities"], pd.DataFrame(partner_rows["capabilities"])], ignore_index=True)
    tables["projects"] = pd.concat([tables["projects"], pd.DataFrame(project_rows["projects"])], ignore_index=True)
    tables["participants"] = pd.concat([tables["participants"], pd.DataFrame(project_rows["participants"])], ignore_index=True)
    tables["records"] = pd.concat([tables["records"], pd.DataFrame(project_rows["records"])], ignore_index=True)
    tables["edges"] = pd.concat([tables["edges"], pd.DataFrame(project_rows["edges"])], ignore_index=True)

    tables["partners"] = dedupe(tables["partners"], ["partner_id"])
    tables["summary"] = dedupe(tables["summary"], ["partner_id"])
    tables["aliases"] = dedupe(tables["aliases"], ["partner_id", "alias_normalized"])
    tables["sources"] = dedupe(tables["sources"], ["partner_id", "source_name", "source_record_id"])
    tables["projects"] = dedupe(tables["projects"], ["project_id"])
    tables["participants"] = dedupe(tables["participants"], ["project_id", "partner_id"])
    tables["capabilities"] = dedupe(tables["capabilities"], ["partner_id", "capability_tag"])
    tables["records"] = dedupe(tables["records"], ["source_name", "source_record_id", "record_type"])
    tables["edges"] = dedupe(tables["edges"], ["partner_a", "partner_b", "project_id"])

    write_csv(tables["partners"], db / "partners.csv", PARTNERS_COLUMNS)
    write_csv(tables["summary"], db / "partner_master_summary.csv", SUMMARY_COLUMNS)
    write_csv(tables["aliases"], db / "partner_aliases.csv", ALIASES_COLUMNS)
    write_csv(tables["sources"], db / "partner_sources.csv", SOURCES_COLUMNS)
    write_csv(tables["projects"], db / "partner_projects.csv", PROJECTS_COLUMNS)
    write_csv(tables["participants"], db / "project_participants.csv", PARTICIPANTS_COLUMNS)
    write_csv(tables["capabilities"], db / "partner_capabilities.csv", CAPABILITIES_COLUMNS)
    write_csv(tables["records"], db / "procurement_records.csv", RECORDS_COLUMNS)
    write_csv(tables["edges"], db / "partner_edges.csv", EDGES_COLUMNS)

    print(f"Seeded mock procurement evidence into {db}")
    print(f"- mock partners: {len(MOCK_PARTNERS)}")
    print(f"- mock contracts: {len(MOCK_CONTRACTS)}")
    print(f"- mock edges: {len(project_rows['edges'])}")
    print(f"- total partners: {len(tables['partners'])}")
    print(f"- total projects: {len(tables['projects'])}")
    print(f"- total participants: {len(tables['participants'])}")
    print(f"- total edges: {len(tables['edges'])}")
    print("NOTE: All seeded evidence is mock. Do not present it as verified procurement history.")


if __name__ == "__main__":
    main()
