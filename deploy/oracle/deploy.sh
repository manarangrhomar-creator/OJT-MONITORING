#!/bin/bash
# ============================================
# OJT Monitoring - Deploy/Update Script
# ============================================
# Called by GitHub Actions on push to main,
# or run manually: sudo -u ojt bash deploy.sh
# ============================================
set -e

APP_DIR="/opt/ojt-monitoring"
APP_USER="ojt"

echo "=== OJT Monitoring - Deploy ==="
echo "Time: $(date)"

cd "$APP_DIR"

# Pull latest code
echo ""
echo "[1/5] Pulling latest code..."
git pull origin main

# Activate venv and install deps
echo ""
echo "[2/5] Installing dependencies..."
su - "$APP_USER" -c "
cd $APP_DIR
source venv/bin/activate
pip install -r requirements.txt --quiet
"

# Run migrations
echo ""
echo "[3/5] Running migrations..."
su - "$APP_USER" -c "
cd $APP_DIR
source venv/bin/activate
python manage.py migrate --noinput
"

# Collect static files
echo ""
echo "[4/5] Collecting static files..."
su - "$APP_USER" -c "
cd $APP_DIR
source venv/bin/activate
python manage.py collectstatic --noinput
"

# Restart services
echo ""
echo "[5/5] Restarting services..."
systemctl restart ojt-gunicorn
systemctl restart ojt-celery

echo ""
echo "=== Deploy complete at $(date) ==="
echo "App should be live at: http://$(curl -s ifconfig.me)"
