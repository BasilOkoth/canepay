# CanePay interoperability + farmer dashboard upgrade

Upload these files to the matching paths in your GitHub repository:

- `core/models.py` — replace existing file
- `core/forms.py` — replace existing file
- `core/admin.py` — replace existing file
- `core/urls.py` — replace existing file
- `core/farmer_views.py` — NEW file
- `core/migrations/0004_interoperability_profitability.py` — NEW migration
- `templates/core/farmer_dashboard.html` — replace existing file
- `templates/base.html` — replace existing file (farmer sidebar navigation)

## What this upgrade adds

1. Farmer delivery records with source-system traceability.
2. Farmer payment/settlement history.
3. Farm cost capture and profitability calculations.
4. External identity mapping for KSB/SIMIS, mills and other systems.
5. Structured cane quality/QBCPS-ready records.
6. Pricing assessment/reconciliation records.
7. Existing receivable-financing-settlement workflow remains intact.

## Deploy

After pushing to GitHub, your Render build/start process must run Django migrations. If your current Render build command already runs `python manage.py migrate`, no extra action is needed.

Otherwise run:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## Important

The profitability numbers are only as complete as the expense records entered. Cane delivery revenue comes from the existing Delivery records. This release does not invent a KSB/QBCPS price; it creates structured places to receive and reconcile authoritative quality/pricing data later.
