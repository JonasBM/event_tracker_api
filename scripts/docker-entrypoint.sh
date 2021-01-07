#!/bin/sh
set -e

# until psql $DATABASE_URL -c '\l'; do
#     >&2 echo "Postgres is unavailable - sleeping"
#     sleep 1
# done

# >&2 echo "Postgres is up - continuing"
echo "Starting"
if [ ! -f /code/manage.py ]; then
    echo "manage.py not found, copying files from source"
    cp -R /src/. /code/
fi

if [ "x$DJANGO_MANAGEPY_MIGRATE" = 'xon' ]; then
    echo "Starting migration"
    python manage.py migrate --noinput
fi

echo "Starting collectstatic"
python manage.py collectstatic --noinput

echo "Starting uwsgi"
uwsgi --socket :8000 --master --enable-threads --processes 5 --module eventtracker.wsgi

exec "$@"