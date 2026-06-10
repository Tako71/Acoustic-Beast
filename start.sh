#!/bin/bash
# Скрипт запуска проекта

PGDATA="/Users/artempilecki/PycharmProjects/acoscticbeast/.pgdata"
PG_CTL="/Library/PostgreSQL/18/bin/pg_ctl"

# Запускаем PostgreSQL если не запущен
if ! "$PG_CTL" -D "$PGDATA" status > /dev/null 2>&1; then
    echo "Запуск PostgreSQL..."
    "$PG_CTL" -D "$PGDATA" -l "$PGDATA/pg.log" start
    sleep 2
else
    echo "PostgreSQL уже запущен."
fi

# Запускаем Django
source .venv/bin/activate
python manage.py runserver
