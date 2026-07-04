# Procurement API Ingest Patch

이 패치는 기존 `partner_master_builder.py`로 만든 Partner Master DB에 **KOICA 조달 API + 나라장터 계약/낙찰 API evidence**를 추가하는 레이어입니다.

## 추가 파일

- `procurement_api_clients.py`  
  data.go.kr API 공통 호출, JSON/XML 파싱, KOICA/Nara client.

- `procurement_ingest.py`  
  API 결과를 `partners.csv`, `partner_projects.csv`, `project_participants.csv`, `partner_capabilities.csv`, `partner_edges.csv`에 반영.

## 실행 순서

```bash
# 1) 기존 CSV 기반 Partner DB 먼저 생성
python partner_master_builder.py --data-dir ./data --out-dir ./partner_db

# 2) API key 환경변수 설정
export DATA_GO_KR_SERVICE_KEY="발급받은_일반_인증키"

# 3) KOICA 조달 API 반영
python procurement_ingest.py --partner-db ./partner_db --koica --max-pages 3

# 4) 나라장터 계약/낙찰 API 반영
python procurement_ingest.py --partner-db ./partner_db --nara \
  --keyword 한국국제협력단 --keyword KOICA \
  --date-from 20240101 --date-to 20261231 \
  --nara-work-type service --max-pages 2
```

## 생성/갱신 파일

```text
partner_db/
  partners.csv
  partner_aliases.csv
  partner_sources.csv
  partner_projects.csv
  project_participants.csv
  partner_capabilities.csv
  partner_master_summary.csv
  partner_edges.csv
  procurement_records.csv
```

## 주의

- KOICA 조달 API 기본 Base URL은 `http://apis.data.go.kr/B260003/PrcureService`로 설정되어 있음.
- 나라장터 API는 조달업무 구분별 operation이 달라서 기본은 `service` 중심으로 둠.
- API별 필수 조회 파라미터가 데이터포털 운영 상태에 따라 달라질 수 있으므로, 실패하면 `--nara-param-json`으로 추가 파라미터를 넣어 테스트.

예:

```bash
python procurement_ingest.py --partner-db ./partner_db --nara \
  --nara-param-json '{"dminsttNm":"한국국제협력단","cntrctCnclsBgnDate":"20240101","cntrctCnclsEndDate":"20241231"}'
```
