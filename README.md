# ODA 컨소시엄 인텔리전스 — 데모

KOICA/ODA 공고 한 건에서 → 사업 component 분해 → 국내·현장 파트너 매칭 → **실현 가능한 컨소 추천**까지.
데모 케이스: **KOICA 스리랑카 북부·북서부 맹그로브숲 복원 및 역량강화 사업**.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

키 없이 바로 **데모 모드**로 실행됩니다. (나라장터/KOICA 라이브 호출은 아래 참고)

## 화면 구성 (사이드바)

| # | 화면 | 내용 |
|---|---|---|
| 개요 | 사업·점수·데이터 상태 | |
| ① 공고 분해 | 공고 → 6개 component (드론 CT계획/복원/양식/건축/기자재/연수) | |
| ② 국내 파트너 매칭 | component별 국내기관 추천 + 점수·근거 | **실데이터** |
| ③ 현장·수원국 파트너 | 스리랑카 KOICA footprint 52건 + 현지 파트너 카드 | 실데이터+목업 |
| ④ 파트너 그래프 | 사업–component–파트너 네트워크(pyvis), 공동수행 엣지 | **실데이터** |
| ⑤ 컨소 추천 | component별 조합 + 종합점수 | |

## 데이터 소스

**실데이터**
- `data/koica_iati.csv` — KOICA IATI 사업정보 (2,019건, 스리랑카 52건)
- `data/nonprofit_national.csv` — 전국 비영리민간단체 등록현황 (행안부, 1,487곳)
- `data/koica_humanitarian.csv` — KOICA 인도적지원 민관협력 실적 (수행기관·국가·분야)
- 나라장터·KOICA 조달 API — 키 입력 시 라이브 (`pipeline.fetch_nara_bid_process`)

**목업 / 미확보**
- 현지·다자 파트너 카드 (`demo_data.FIELD_PARTNERS`) — 집행계획 문서 실명 기반
- OECD CRS / WB / ADB — 미확보 (추후 연동)

## 라이브 API 활성화

1. `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` 로 복사
2. data.go.kr에서 발급받은 serviceKey 입력
3. 재실행 → 사이드바에 "🟢 연결" 표시

> data.go.kr API는 브라우저 직접 호출 시 CORS로 차단됨 → Streamlit(서버사이드)에서 호출하는 이유.

## 정직한 한계 (발표 시 인지)

- **IATI 시행기관은 전부 KOICA로만 기재** → 하위 파트너는 사업명 파싱 + 목업으로 보완.
- **인도적지원 실적 31건**으로 표본이 작음 → 국내 매칭은 "분야/국가 실적" 개념 증명 수준.
- **키워드 기반 매칭** → 노이즈 존재. 실서비스는 실적/PQ자격/공동수급 이력으로 정교화 필요.
- **공동수급 구성원 데이터** — 나라장터 계약 API 노출 여부 검증 후 모듈 D 국내 그래프 강화.

## 다음 단계

- 나라장터 계약 API 실호출 → 공고 자동 인입 + 공동수급 그래프 실데이터화
- 중소벤처부 비영리법인 API로 기관 프로필 보강
- 스코어링 가중치 튜닝, 현지 파트너 IATI/MDB 자동 발견

## 구조

```
app.py          Streamlit UI (6개 화면)
pipeline.py     데이터 로딩·매칭·스코어링·API 스텁 (streamlit 비의존)
graph_view.py   파트너 그래프 (networkx→pyvis)
demo_data.py    스리랑카 component·현지파트너 정의
data/           정규화된 CSV 3종 (utf-8)
```
