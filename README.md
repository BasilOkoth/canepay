# Miwa360

**Miwa360 connects sugarcane farmers, millers and financial institutions so verified cane deliveries can unlock earlier payment.**

A farmer delivers cane. The mill verifies the delivery and acknowledges the amount payable. Miwa360 turns that verified obligation into a finance-ready receivable. With the farmer's consent, participating banks and SACCOs can review the evidence and offer an advance. When the mill later pays, Miwa360 records settlement to the financier and any residual due to the farmer.

## Roles
- Farmer — sees verified deliveries, amount owed, due date, requests early payment and compares offers.
- Miller — registers/imports deliveries, verifies cane, acknowledges obligations and records settlement.
- Bank / SACCO — reviews farmer-authorised receivables, makes offers and records disbursement.
- Oversight — sees obligations, financing, mill signals, audit events and integration status.

## Interoperability
Miwa360 is designed to sit between existing sugar-industry systems rather than replace them.

Included:
- shared-key JSON delivery ingestion endpoint
- source-system / external-reference fields
- integration registry and event log
- receivable verification API
- audit trail
- duplicate-financing lock through one active receivable assignment

### Delivery ingestion
POST `/api/v1/integrations/deliveries/`
Header: `X-MIWA360-KEY: <MIWA360_INGEST_KEY>`

Unknown farmers, farms or mills are rejected rather than silently created.

## Render
Build:
`pip install -r requirements.txt && python manage.py migrate --fake-initial && python manage.py collectstatic --noinput`

Start:
`gunicorn canepay.wsgi:application`

Environment:
- SECRET_KEY
- DEBUG=False
- ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1
- DATABASE_URL
- optional MIWA360_INGEST_KEY

After first deployment:
`python manage.py seed_demo`

Demo accounts (all explicitly demo):
- farmer / Demo123!
- mill / Demo123!
- sacco / Demo123!
- oversight / Demo123!
