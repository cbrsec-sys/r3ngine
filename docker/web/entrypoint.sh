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
# Ensure searchsploit RC file is copied to root home directory if available
if [ -f "/usr/src/exploitdb/.searchsploit_rc" ]; then
  cp /usr/src/exploitdb/.searchsploit_rc /root/.searchsploit_rc
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

# Check if fixtures are already loaded
echo "Checking if default fixtures are already loaded..."
if ! python3 manage.py shell -c "from scanEngine.models import EngineType; import sys; sys.exit(0 if EngineType.objects.exists() else 1)"; then
    echo "Loading default fixtures..."
    python3 manage.py loaddata fixtures/external_tools.yaml
    python3 manage.py loaddata fixtures/default_keywords.yaml
    
    for f in fixtures/scan_engines/*.yaml; do
        python3 manage.py loaddata "$f" --app scanEngine.EngineType
    done
    
    for f in fixtures/hardware_profiles/*.yaml; do
        python3 manage.py loaddata "$f" --app scanEngine.HardwareProfile
    done
else
    echo "Default fixtures already exist. Skipping..."
fi

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
