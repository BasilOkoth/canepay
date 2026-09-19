#!/usr/bin/env bash
set -o errexit

echo "==> Miwa360 startup: applying database migrations..."
python manage.py migrate --fake-initial --noinput

echo "==> Miwa360 startup: collecting static files..."
python manage.py collectstatic --noinput

if [ "${SEED_DEMO:-false}" = "true" ]; then
  echo "==> Miwa360 startup: seeding demo accounts..."
  python manage.py seed_demo
fi

echo "==> Miwa360 startup: launching Gunicorn..."
exec gunicorn canepay.wsgi:application --bind "0.0.0.0:${PORT:-10000}"
