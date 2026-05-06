#!/bin/bash

# Collect static files
echo "Collecting static files..."
python3 manage.py collectstatic --noinput

# Run migrations
echo "Running migrations..."
python3 manage.py migrate --noinput

# Sync roles and permissions
echo "Syncing roles..."
python3 manage.py sync_roles

# Load default fixtures (Scan Engines, Tools, Keywords)
echo "Loading default fixtures..."
python3 manage.py loaddata fixtures/default_scan_engines.yaml
python3 manage.py loaddata fixtures/external_tools.yaml
python3 manage.py loaddata fixtures/default_keywords.yaml

# Load custom engines if any
#echo "Loading custom engines..."
#mkdir -p /usr/src/app/custom_engines
#python3 manage.py loadcustomengines

# Start Vite development server if DEBUG is enabled
if [ "$DEBUG" = "1" ]; then
    echo "Starting Vite development server..."
    cd /usr/src/app/frontend && npm run dev -- --host 0.0.0.0 &
    cd /usr/src/app
fi

# Start the server
echo "Starting reNgine server..."
python3 manage.py runserver 0.0.0.0:8000

exec "$@"
