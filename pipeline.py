"""
파이프라인: 데이터 로딩 / 매칭 / 스코어링 / API 호출.
streamlit에 의존하지 않음 → 단독 테스트 가능. app.py가 캐싱 래핑.
"""
import os
import re
import pandas as pd

# 관련도 가중치를 주는 등록 부처 (ODA/환경/산림/수산 계열)
RELEVANT_MINISTRIES = {"외교부", "기후에너지환경부", "산림청", "해양수산부", "농림축산식품부"}

# IATI 사업명에서 뽑아낼 다자·국제기구 패턴
MULTILATERAL_PAT = re.compile(
    r"(WHO|UNDP|UNICEF|UN-?Habitat|UNEP|UNESCO|WFP|FAO|IOM|ADB|GGGI|IFAD|UNFPA|UN\b)",
    re.IGNORECASE,
)


def load_data(data_dir):
    """세 CSV 로드 (utf-8 정규화본)."""
    d = {}
    d["iati"] = pd.read_csv(os.path.join(data_dir, "koica_iati.csv"), dtype=str).fillna("")
    d["humanitarian"] = pd.read_csv(os.path.join(data_dir, "koica_humanitarian.csv"), dtype=str).fillna("")
    d["nonprofit"] = pd.read_csv(os.path.join(data_dir, "nonprofit_national.csv"), dtype=str).fillna("")
    return d


# ---------- 모듈 B: 국내 파트너 매칭 ----------

def _kw_hits(text, keywords):
    t = text.lower()
    return [k for k in keywords if k.lower() in t]


def match_domestic(component, humanitarian, nonprofit, recipient_country="스리랑카", top_n=6):
    """
    한 component에 대해 국내 후보기관을 점수화.
    - 실적기반: KOICA 인도적지원 수행기관 (사업명 키워드 매칭 + 국가/분야 실적)
    - 등록기반: 전국 비영리민간단체 (주된사업 키워드 + 등록부처 관련도)
    """
    kws = component["keywords"]
    rows = []

    # (1) 실적기반 — 수행기관 이력
    hum = humanitarian.copy()
    hum["_txt"] = (hum.get("사업명_국문", "") + " " + hum.get("사업명_영문", "")
                   + " " + hum.get("지역", ""))
    for org, g in hum.groupby("수행기관"):
        # 컨소 표기(콤마)면 개별 기관으로 분해
        if not org.strip():
            continue
        hits = set()
        countries = set()
        for _, r in g.iterrows():
            hits.update(_kw_hits(r["_txt"], kws))
            countries.add(r.get("국가명", ""))
        if not hits:
            continue
        score = len(hits) * 3
        note = f"KOICA 수행실적 {len(g)}건"
        if recipient_country in countries:
            score += 5
            note += f" · {recipient_country} 경험"
        for sub in re.split(r"[,\u3001·/]", org):  # 컨소 분해
            sub = sub.strip()
            if sub:
                rows.append({"기관": sub, "점수": score, "출처": "실적기반",
                             "근거": f"{note} · 키워드 {sorted(hits)}"})

    # (2) 등록기반 — 전국 비영리단체
    npf = nonprofit.copy()
    npf["_txt"] = npf.get("단체명", "") + " " + npf.get("주된사업", "")
    for _, r in npf.iterrows():
        hits = _kw_hits(r["_txt"], kws)
        if not hits:
            continue
        score = len(hits) * 2
        note = ""
        if r.get("등록기관", "") in RELEVANT_MINISTRIES:
            score += 4
            note = f"{r['등록기관']} 등록"
        rows.append({"기관": r.get("단체명", ""), "점수": score, "출처": "등록기반",
                     "근거": f"{note} · 키워드 {hits}".strip(" ·")})

    if not rows:
        return pd.DataFrame(columns=["기관", "점수", "출처", "근거"])
    df = pd.DataFrame(rows)
    # 같은 기관 중복 시 최고점 유지
    df = df.sort_values("점수", ascending=False).drop_duplicates("기관").head(top_n)
    return df.reset_index(drop=True)


# ---------- 모듈 C: 현장·수원국 footprint (IATI) ----------

def iati_country_footprint(iati, country="스리랑카"):
    sl = iati[iati.get("수원국", "").str.contains(country, na=False)].copy()
    sectors = sl["사업분야명"].value_counts()
    # 사업명에서 다자기구 추출
    partners = {}
    for name in sl["사업명(한글)"].tolist() + sl["사업명(영문)"].tolist():
        for m in MULTILATERAL_PAT.findall(name):
            key = m.upper().replace("-", "")
            partners[key] = partners.get(key, 0) + 1
    return sl, sectors, partners


# ---------- 모듈 D: 협업이력 엣지 ----------

def co_implementation_edges(humanitarian):
    """수행기관이 복수(콤마 등)인 사업 = 실제 협업(공동수행) 엣지."""
    edges = []
    for _, r in humanitarian.iterrows():
        org = r.get("수행기관", "")
        parts = [p.strip() for p in re.split(r"[,\u3001·]", org) if p.strip()]
        if len(parts) > 1:
            for i in range(len(parts)):
                for j in range(i + 1, len(parts)):
                    edges.append((parts[i], parts[j], r.get("사업명_국문", "")))
    return edges


# ---------- 모듈 E: 컨소 추천 스코어링 ----------

def recommend_consortium(components, humanitarian, nonprofit, field_partners,
                         recipient_country="스리랑카"):
    """component별 top 국내기관 + 현지파트너를 묶어 컨소 후보 + 종합점수."""
    rec = []
    for c in components:
        dom = match_domestic(c, humanitarian, nonprofit, recipient_country, top_n=1)
        lead = dom.iloc[0].to_dict() if len(dom) else None
        fps = [f["name"] for f in field_partners if c["id"] in f["components"]]
        rec.append({"component": c, "국내후보": lead, "현지파트너": fps})

    # 종합점수(데모): 분야 커버리지 + 국내 매칭 평균 + 현지 연계
    covered = sum(1 for r in rec if r["국내후보"])
    coverage = covered / len(components)
    avg_match = (sum(r["국내후보"]["점수"] for r in rec if r["국내후보"])
                 / max(covered, 1))
    field_link = sum(1 for r in rec if r["현지파트너"]) / len(components)
    total = round(coverage * 40 + min(avg_match, 20) + field_link * 40, 1)
    breakdown = {"분야 커버리지(40)": round(coverage * 40, 1),
                 "국내 매칭 강도(20)": round(min(avg_match, 20), 1),
                 "현지 연계(40)": round(field_link * 40, 1)}
    return rec, total, breakdown


# ---------- data.go.kr / KOICA API 스텁 ----------
# 실호출 함수. service_key 없으면 None 반환 → app은 데모(PDF) 모드로 동작.
# data.go.kr은 서버사이드 호출 필요(브라우저 CORS 차단) → Streamlit(파이썬)에서 호출.

import urllib.request
import urllib.parse
import json

NARA_CNTRCT_PROCESS = "http://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService"
KOICA_ODA_PROCUREMENT_BASE = "http://apis.data.go.kr/B260004"  # 포털에서 정확 오퍼레이션 확인


def fetch_nara_bid_process(bid_no, service_key, num_rows=10):
    """나라장터 계약과정통합공개: 공고번호로 사전규격→공고→낙찰→계약 통합 조회."""
    if not service_key:
        return None
    op = "getCntrctProcssIntgOpenUsrvc"  # 용역. 포털 Swagger로 오퍼레이션명 확정 필요
    params = {"serviceKey": service_key, "bidNtceNo": bid_no,
              "numOfRows": num_rows, "pageNo": 1, "type": "json"}
    url = f"{NARA_CNTRCT_PROCESS}/{op}?" + urllib.parse.urlencode(params, safe="%")
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}
