# CanePay MVP

CanePay is a role-based prototype for converting verified sugarcane deliveries into transparent, financeable receivables.

## What this prototype demonstrates

1. A mill registers a cane delivery.
2. The mill verifies weight, quality and payable amount.
3. The mill digitally acknowledges the payment obligation.
4. CanePay creates a verified receivable.
5. The farmer can request early financing and consent to data sharing.
6. A bank/SACCO can review the verified receivable and make an offer.
7. The farmer accepts one offer and the receivable is assigned to that financier.
8. The financier records disbursement.
9. The mill later records settlement and the transaction closes.
10. A regulator view shows aggregate payment and audit information.

## Demo users

After running `python manage.py seed_demo`:

- Farmer: `farmer` / `Demo123!`
- Mill: `mill` / `Demo123!`
- Financier: `sacco` / `Demo123!`
- Regulator: `ksb` / `Demo123!`

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Deploy to Render

The repository includes `render.yaml` and `Procfile`.

1. Push the whole folder to GitHub.
2. In Render choose **New > Blueprint**.
3. Select the GitHub repository.
4. Render creates the web service and PostgreSQL database.
5. After first deployment, open the Render Shell and run:
   `python manage.py seed_demo`

## Integration-ready endpoint

Authenticated users can verify a receivable at:

`/api/receivables/CP-000001/`

The JSON response contains validity, amount, mill, financing status and due date. This is a placeholder for future SugarVISTA/QBCPS/mill/bank integrations.

## Important prototype limitation

This is a demonstration system, not a production lending platform. A real rollout needs legal review for receivable assignment, KYC/AML, data protection, lending regulation, mill payment instructions, API security, audit controls and financial-partner agreements.
