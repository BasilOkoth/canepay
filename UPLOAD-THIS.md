# Upload instructions

This ZIP is a complete Miwa360 replacement build.

1. Extract the ZIP.
2. Upload/replace the contents in the root of `BasilOkoth/canepay`.
3. Keep the repository name `canepay` for now; the visible product is Miwa360.
4. Render Start Command:
   `gunicorn canepay.wsgi:application`
5. Environment:
   - `DEBUG=False`
   - `ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1`
   - `DATABASE_URL=<Render PostgreSQL internal URL>`
   - optional `MIWA360_INGEST_KEY=<long random secret>`
6. Use **Clear build cache & deploy**.
7. After first deployment run:
   `python manage.py seed_demo`

If an old experimental database has incompatible core tables, use a clean PostgreSQL database for this MVP rather than faking schema compatibility.
