#!/bin/sh
set -e

# until psql $DATABASE_URL -c '\l'; do
#     >&2 echo "Postgres is unavailable - sleeping"
#     sleep 1
# done

# >&2 echo "Postgres is up - continuing"

if [ ! -d /code ]; then
    mkdir -p /code;
fi
if [ -z "$(ls -A /code/)" ]; then
    cp -R /src/. /code/
fi

if [ ! -d /code/static ]; then
    mkdir -p /code/static;
fi
if [ -z "$(ls -A /code/static/)" ]; then
    cp -R /src/static/. /code/static/
fi

if [ "x$DJANGO_MANAGEPY_MIGRATE" = 'xon' ]; then
    python manage.py migrate --noinput
fi

python manage.py collectstatic --noinput

uwsgi
    --socket=:8000 \
    --master \
    --enable-threads
    --module=eventtracker.wsgi:application \
    --env DJANGO_SETTINGS_MODULE=eventtracker.settings \
    --processes=5 \
    --uid=1000 --gid=2000 \
    --max-requests=5000 \
    --vacuum \
    --daemonize=/code/log/uwsgi/eventtracker.log

exec "$@"