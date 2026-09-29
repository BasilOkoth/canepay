CANEPAY — ONE-UPLOAD UPDATE
===========================

This package contains every file required for the interoperability + farmer dashboard upgrade, already arranged in the correct repository paths.

HOW TO USE WITH GITHUB WEB
1. Extract this ZIP on your computer.
2. Open your BasilOkoth/canepay repository on GitHub.
3. Choose Add file > Upload files.
4. Drag ALL CONTENTS inside the extracted `canepay-one-upload` folder into the upload area in ONE upload/commit.
5. Commit the upload.

The upload will replace these existing files:
- core/models.py
- core/forms.py
- core/admin.py
- core/urls.py
- templates/base.html
- templates/core/farmer_dashboard.html

It will add these new files:
- core/farmer_views.py
- core/migrations/0004_interoperability_profitability.py

No existing migration is replaced.

After Render redeploys, ensure the build/start process runs:
python manage.py migrate
python manage.py collectstatic --noinput

IMPORTANT: Upload the CONTENTS of this folder to the repository root, not the outer `canepay-one-upload` folder itself.
