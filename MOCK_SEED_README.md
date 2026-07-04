# Mock Procurement Seed Patch

This patch lets you simulate KOICA/Nara procurement ingestion without running the live APIs.

## Files

- `mock_procurement_seed.py`  
  Adds mock procurement records, mock project participants, mock capability evidence, and mock joint-contract edges to `partner_db/`.

- `pipeline.py`  
  Updated to load `partner_edges.csv` and show those edges in the partner ecosystem graph.

## Important

All seeded data is mock evidence. It is flagged by:

- `partner_id` prefix: `MOCK_`
- `source_name`: `mock_procurement_seed`
- `registration_status`: `mock`
- `evidence_text` prefix: `[MOCK]`

Use this for demos only. Do not present the seeded contracts as verified procurement history.

## Install

Copy these files into the project root:

```text
oda_consortium/
  mock_procurement_seed.py
  pipeline.py
```

## Run

Do **not** rebuild Partner DB after seeding, unless you want to reset the demo data.

```powershell
python mock_procurement_seed.py --partner-db ./partner_db
```

Then check:

```powershell
(Import-Csv .\partner_db\procurement_records.csv).Count
(Import-Csv .\partner_db\project_participants.csv).Count
(Import-Csv .\partner_db\partner_edges.csv).Count
```

Expected addition:

```text
mock partners: 10
mock contracts: 10
mock edges: 9
```

Then run Streamlit:

```powershell
streamlit run app.py
```

## Reset mock rows only

Running the seed script again automatically removes previous mock rows and re-adds them. You can also use:

```powershell
python mock_procurement_seed.py --partner-db ./partner_db --reset-mock
```

`--reset-mock` is accepted for clarity; the script is idempotent either way.
