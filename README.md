# Procurement ingest patch v2

Replace these files in your project root:
- procurement_api_clients.py
- procurement_ingest.py

Fixes:
1. Empty KOICA API envelopes with TOTAL_COUNT=0 are no longer ingested as fake records.
2. Nara contract PPSSrch date parameters now use inqryBgnDate / inqryEndDate.
3. Nara contract institution search now uses insttDivCd + insttNm.
4. Nara award fetch is off by default because the award API has weak institution-level request filtering.

Recommended command:
python procurement_ingest.py --partner-db ./partner_db --nara --keyword 한국국제협력단 --keyword KOICA --date-from 20240101 --date-to 20241231 --nara-work-type service --max-pages 2
