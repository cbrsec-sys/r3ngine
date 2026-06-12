#!/bin/bash
# Install/update frontend dependencies only when package.json is updated or node_modules doesn't exist
echo "Checking frontend dependencies..."
cd /usr/src/app/frontend
if [ ! -d "node_modules" ] || [ package.json -nt node_modules ]; then
    echo "Installing/updating frontend dependencies (changes detected)..."
    npm install
else
    echo "Frontend dependencies are up to date."
fi

if [ "$DEBUG" = "1" ]; then
    echo "Development mode: Starting Vite dev server..."
    npm run dev -- --host 0.0.0.0 &
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
python3 manage.py loaddata fixtures/external_tools.yaml
python3 manage.py loaddata fixtures/default_keywords.yaml
# Load default fixtures
for f in fixtures/scan_engines/*.yaml; do
  python3 manage.py loaddata "$f" --app scanEngine.EngineType
done
for f in fixtures/hardware_profiles/*.yaml; do
  python3 manage.py loaddata "$f" --app scanEngine.HardwareProfile
done

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
