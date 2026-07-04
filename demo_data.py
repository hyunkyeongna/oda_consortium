"""
데모 케이스 정적 데이터 (KOICA 스리랑카 맹그로브 사업).
공고 원문(집행계획 PDF)에서 추출한 component + 매칭 키워드 + 현지/다자 파트너 목업.
실제 서비스에서는 모듈 A(공고 NLP 분해)가 이 구조를 자동 생성한다.
"""

DEMO_BID = {
    "사업명": "스리랑카 북부 및 북서부주 맹그로브숲 생태계 복원 및 역량강화 사업",
    "사업명_영문": "Restoration and Capacity Building on Mangrove Ecosystem in Sri Lanka",
    "수원국": "스리랑카",
    "예산_백만원": 16560,   # 1,200만불
    "기간": "2026-2030",
    "발주": "KOICA",
}

# 공고에서 분해된 component (모듈 A 산출물의 데모 버전)
# keywords: 국내/현지 파트너 매칭에 쓰이는 검색어 (한/영)
COMPONENTS = [
    {
        "id": "C1",
        "name": "ICT 기반 종합관리계획 수립",
        "desc": "드론·GIS·원격탐사 기반 맹그로브 지도 제작 및 관리계획, 조사 매뉴얼",
        "sector": "산림/ICT",
        "keywords": ["ICT", "드론", "GIS", "원격탐사", "매핑", "관리계획", "조사",
                     "mapping", "survey", "remote sensing", "정보화", "데이터"],
    },
    {
        "id": "C2",
        "name": "맹그로브 양묘·복원",
        "desc": "양묘장 조성, 조림, 훼손지 복원 및 사후 관리",
        "sector": "산림/환경",
        "keywords": ["산림", "조림", "복원", "양묘", "맹그로브", "식재", "임업", "생태",
                     "환경", "forestry", "mangrove", "restoration", "reforestation"],
    },
    {
        "id": "C3",
        "name": "맹그로브 기반 양식(산림어업)",
        "desc": "맹그로브-새우 종합양식(IMS) 모델, 대체 소득원",
        "sector": "수산/농업",
        "keywords": ["양식", "수산", "어업", "산림어업", "소득", "생계", "농업",
                     "aquaculture", "fisheries", "livelihood"],
    },
    {
        "id": "C4",
        "name": "맹그로브 교육센터 건축",
        "desc": "교육센터 신축(1,141㎡) 및 정보센터 리모델링(390㎡)",
        "sector": "건축/인프라",
        "keywords": ["건축", "건설", "시공", "리모델링", "인프라", "설계", "센터",
                     "construction", "building", "infrastructure"],
    },
    {
        "id": "C5",
        "name": "기자재·장비 지원",
        "desc": "실험·조사 기자재, 드론, 차량, IT 장비 조달",
        "sector": "조달",
        "keywords": ["기자재", "장비", "조달", "실험실", "equipment", "procurement"],
    },
    {
        "id": "C6",
        "name": "역량강화·연수",
        "desc": "공무원 초청연수, 현지 워크숍, 교육 프로그램/홍보자료",
        "sector": "교육/역량강화",
        "keywords": ["역량강화", "교육", "연수", "훈련", "워크숍", "교육프로그램",
                     "capacity", "training", "역량"],
    },
]

# 현지·다자 파트너 목업 (집행계획 문서에 실명 등장 — 모듈 C)
# 실제 서비스에서는 IATI/MDB 조달 데이터로 일부 대체, 나머지는 이 카드 유지
FIELD_PARTNERS = [
    {"name": "산림보전국(DoFC)", "type": "수원국 정부", "role": "복원 주관·보호지역 관리", "components": ["C1", "C2"]},
    {"name": "야생동물보전국(DoWC)", "type": "수원국 정부", "role": "보호지역·생물다양성", "components": ["C1", "C2"]},
    {"name": "Wayamba University", "type": "현지 학계", "role": "맹그로브 조사·연구", "components": ["C1", "C2"]},
    {"name": "Wildlife & Nature Protection Society", "type": "현지 NGO", "role": "복원 파일럿·모니터링", "components": ["C2"]},
    {"name": "Sudeesa", "type": "현지 NGO", "role": "커뮤니티 기반 복원·소액대출", "components": ["C3", "C6"]},
    {"name": "NAQDA(양식개발청)", "type": "수원국 정부", "role": "양식 시범·기술", "components": ["C3"]},
    {"name": "GGGI", "type": "국제기구", "role": "가구별 생계·가치사슬 기초선 조사", "components": ["C3"]},
    {"name": "UNEP", "type": "국제기구", "role": "생태계 복원 10년·재정지원", "components": ["C2"]},
    {"name": "ADB", "type": "다자개발은행", "role": "Vankalai 전시홍보센터 건축", "components": ["C4"]},
]
