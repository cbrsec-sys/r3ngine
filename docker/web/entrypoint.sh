#!/bin/bash
# Ensure OpenSSL compatibility before running any management commands
pip3 install --upgrade --no-cache-dir pyOpenSSL==24.0.0

# Install/update frontend dependencies (ensures packages match package.json in both modes)
echo "Installing frontend dependencies..."
cd /usr/src/app/frontend && npm install

if [ "$DEBUG" = "1" ]; then
    echo "Development mode: Starting Vite dev server..."
    npm run dev -- --host 0.0.0.0 &
# else
    # echo "Production mode: Building frontend..."
    # npm run build
fi

cd /usr/src/app

# Collect static files (includes built frontend assets)
echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

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

# Start the server
echo "Starting reNgine server..."
if [ "$DEBUG" = "1" ]; then
    echo "  Mode: development (Django runserver via Channels)"
    python3 manage.py runserver 0.0.0.0:8000
else
    echo "  Mode: production (Gunicorn + UvicornWorker ASGI)"
    exec gunicorn reNgine.routing:application \
        -c /usr/src/app/gunicorn.conf.py
fi
