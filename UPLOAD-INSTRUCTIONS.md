# Miwa360 Premium Authentication Upgrade

This package is designed to be copied over the existing `BasilOkoth/canepay` repository while preserving the current application and all four demo accounts.

## What changes

- Adds real self-registration at `/accounts/create/`.
- Farmers activate immediately and receive a real `Profile` + `Farmer` record.
- Miller and Bank/SACCO users can create credentials and sign in, but remain `Pending verification` until an administrator activates the institution.
- Oversight remains invitation/admin-created only.
- Login accepts **username or email**.
- Existing demo accounts remain valid: `farmer`, `mill`, `sacco`, `oversight` / `Demo123!`.
- Adds a premium competition-ready login/onboarding story focused on the miller liquidity gap.
- Adds account-status controls to Django admin.
- Adds auth tests for farmer signup, institutional gating, email login and activation.

## Files to replace

- `core/models.py`
- `core/decorators.py`
- `core/urls.py`
- `core/admin.py`
- `canepay/urls.py`
- `templates/registration/login.html`
- `static/css/login.css`

## Files to add

- `core/auth_forms.py`
- `core/auth_views.py`
- `core/migrations/0003_profile_account_status.py`
- `core/tests_auth.py`
- `templates/registration/signup.html`
- `templates/core/account_pending.html`

## Deployment

Your existing `start.sh` already runs:

```bash
python manage.py migrate --fake-initial --noinput
python manage.py collectstatic --noinput
```

So Render will apply the new `account_status` migration automatically on the next deploy.

If `SEED_DEMO=true`, the existing seed command continues to keep the four demo accounts available.

## Institution activation

Open Django admin → **Profiles** → change `account_status` from `Pending verification` to `Active` for an approved miller or bank/SACCO account.

For a miller, ensure the profile's `organisation` exactly matches the relevant verified `Mill.name` so the existing mill workspace resolves the correct records.

## Recommended smoke test after deploy

1. Open `/accounts/login/` and confirm all four demo accounts still enter their correct workspaces.
2. Click **Create account** and register a farmer; confirm immediate login and an empty farmer workspace.
3. Sign out and sign in again using the farmer's **email** instead of username.
4. Register a Bank/SACCO account; confirm it lands on **Institution verification** and cannot open financier records.
5. Activate that Profile in Django admin; sign in again and confirm the financier workspace opens.
