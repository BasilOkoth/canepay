# MIWA360 mill dashboard 500 fix

Upload these two files to the existing GitHub repository, preserving the paths:

1. `core/mill_views.py` — NEW file
2. `core/urls.py` — REPLACE the existing file

Commit the changes. Render should redeploy automatically.

No migration is required for this fix.

## Cause fixed

The old `mill_dashboard` sliced the delivery and receivable QuerySets with `[:100]` before using `.filter()` and `.exclude()` for dashboard metrics. Django raises `TypeError: Cannot filter a query once a slice has been taken.`

The corrected dashboard calculates metrics from unsliced querysets, then slices only the rows passed to the template.
