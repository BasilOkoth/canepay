# CanePay Premium UI Upgrade

This package replaces CanePay's prototype-looking interface with a polished, investor-ready visual system while preserving the existing Django backend and role workflows.

## Replace these folders/files

- `templates/base.html`
- `templates/registration/login.html`
- `templates/core/farmer_dashboard.html`
- `templates/core/mill_dashboard.html`
- `templates/core/financier_dashboard.html`
- `templates/core/regulator_dashboard.html`
- `templates/core/receivable_detail.html`
- `templates/core/form.html`
- `templates/core/no_role.html`
- `static/css/app.css`

## What changed

- Premium CanePay brand system using forest green, cane-lime and warm ivory.
- New split-screen sign-in experience with product positioning and a collapsible demo credentials section.
- Removed the toy-like "Prototype • v0.1" footer language.
- Premium role workspaces for farmer, mill, financier and regulator.
- Responsive cards, tables, transaction evidence, trust-chain visualisation and risk views.
- Improved forms with field-level errors and help text.
- POST-based sign-out compatible with modern Django.
- Mobile responsiveness.

## Backend

No model or database changes are required for this UI package. Existing Django views, forms, URLs and business logic remain intact.
