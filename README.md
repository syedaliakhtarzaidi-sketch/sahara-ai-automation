# Sahara AI Freight Intelligence

Streamlit starter dashboard for:
- UK domestic pallet movements
- UK to Northern Ireland pallets
- UK to Republic of Ireland pallets
- Full trailer loads (FTL)
- UK port-to-door container haulage (20ft / 40ft)

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Verification rules
- No invented rates are inserted.
- Only quotations marked **Verified** appear in the cheapest-three ranking.
- Verification requires a quote reference, evidence URL, confirmation notes, and verifier/contact.
- Ranking uses total payable cost: base + fuel + tolls + other charges + VAT.
- Expired quotes are excluded by default.

## Production requirements
The starter uses SQLite for initial testing. Streamlit hosting may not preserve local files across restarts/redeployments. Before operational use, migrate to persistent Supabase/Postgres storage and connect carrier APIs, email/EDI quote channels, or confirmed carrier portals. Until those connections are configured, the system must not claim live market rates.
