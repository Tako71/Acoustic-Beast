#!/bin/bash
set -e

echo "Ожидание PostgreSQL на $DB_HOST:$DB_PORT..."
until python -c "
import psycopg2, sys
try:
    psycopg2.connect(host='$DB_HOST', port='$DB_PORT', dbname='$DB_NAME', user='$DB_USER', password='$DB_PASSWORD')
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL готов."

echo "Применяю миграции..."
python manage.py migrate --noinput

echo "Запуск Gunicorn..."
exec gunicorn acoustic_beast.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
