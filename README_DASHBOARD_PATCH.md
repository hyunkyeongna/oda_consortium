# Dashboard Patch v3

Files to replace in the project root:

- `app.py`
- `ui.py`
- `pipeline.py`
- `graph_view.py`

What changed:

- Reworked UI into an executive dashboard layout.
- Removed top Streamlit header spacing to prevent the hero section from being cut or pushed down.
- Converted all visible labels, page copy, components, and field-partner cards to English.
- Removed internal seed terminology from the visible UI.
- Displays Nara/KOICA and Partner Master as connected operational data layers for the demo flow.
- Reads `partner_edges.csv` from Partner Master DB so co-delivery links appear in the graph.
- Prefers English partner names when available.

Deployment:

```powershell
git add app.py ui.py pipeline.py graph_view.py
git commit -m "Improve dashboard UI and operational data display"
git push
```

If Streamlit Cloud still shows old UI, clear the app cache or reboot the app.
