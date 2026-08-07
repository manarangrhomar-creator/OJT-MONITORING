#!/bin/bash
# ============================================
# OJT Monitoring - Oracle Cloud Always Free Setup
# ============================================
# Run this ONCE on your Oracle Cloud VM as root:
#   sudo bash setup.sh
#
# Prerequisites:
#   - Ubuntu 22.04 LTS on Oracle Cloud Always Free
#   - SSH access as ubuntu user
#   - Your GitHub repo URL ready
# ============================================
set -e

echo "=========================================="
echo " OJT Monitoring - Oracle Cloud Setup"
echo "=========================================="

# --- Configuration (edit these) ---
APP_NAME="ojt-monitoring"
APP_DIR="/opt/ojt-monitoring"
APP_USER="ojt"
DB_NAME="ojt_monitoring"
DB_USER="ojt_user"
DB_PASS="ojt_secure_$(openssl rand -hex 8)"
REPO_URL="https://github.com/YOUR_USERNAME/OJT-MONITORING.git"

# --- Step 1: System packages ---
echo ""
echo "[1/8] Installing system packages..."
apt update && apt upgrade -y
apt install -y \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    git curl wget \
    libpq-dev \
    ufw

# --- Step 2: Firewall ---
echo ""
echo "[2/8] Configuring firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# --- Step 3: PostgreSQL ---
echo ""
echo "[3/8] Setting up PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

su - postgres -c "psql -c \"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';\"" || true
su - postgres -c "psql -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};\"" || true
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};\""

# --- Step 4: Redis ---
echo ""
echo "[4/8] Configuring Redis..."
systemctl enable redis-server
systemctl start redis-server

# Test Redis
redis-cli ping | grep -q PONG && echo "Redis: OK" || echo "Redis: WARNING - not responding"

# --- Step 5: App user and directory ---
echo ""
echo "[5/8] Creating app user and directory..."
id -u "$APP_USER" &>/dev/null || useradd -m -s /bin/bash "$APP_USER"
mkdir -p "$APP_DIR"
chown "$APP_USER":"$APP_USER" "$APP_DIR"

# --- Step 6: Clone and setup ---
echo ""
echo "[6/8] Cloning repository and setting up Python..."
su - "$APP_USER" -c "
cd $APP_DIR
git clone $REPO_URL . 2>/dev/null || echo 'Repository already cloned, pulling latest...'
git pull origin main 2>/dev/null || true
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
"

# --- Step 7: Environment file ---
echo ""
echo "[7/8] Creating environment file..."

# Get VM public IP
VM_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "YOUR_VM_IP")

# Generate Django secret key
SECRET_KEY=$(su - "$APP_USER" -c "
cd $APP_DIR
source venv/bin/activate
python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"
")

cat > "${APP_DIR}/.env" << EOF
# Django
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${VM_IP}

# Database
DATABASE_URL=postgres://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Email (configure if needed)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=OJT Monitoring <noreply@example.com>
EOF

chown "$APP_USER":"$APP_USER" "${APP_DIR}/.env"
chmod 600 "${APP_DIR}/.env"

echo "  Database password saved to ${APP_DIR}/.env"
echo "  VM IP detected: ${VM_IP}"

# --- Step 8: Django setup ---
echo ""
echo "[8/8] Running Django setup..."
su - "$APP_USER" -c "
cd $APP_DIR
source venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
"

# Create superuser prompt
echo ""
echo "Creating admin superuser..."
su - "$APP_USER" -c "
cd $APP_DIR
source venv/bin/activate
python manage.py createsuperuser
"

# --- Systemd services ---
echo ""
echo "Setting up systemd services..."

cat > /etc/systemd/system/ojt-gunicorn.service << EOF
[Unit]
Description=OJT Monitoring Gunicorn
After=network.target postgresql.service redis.service

[Service]
User=${APP_USER}
Group=www-data
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/gunicorn ojt_monitoring.wsgi:application \\
    --bind 127.0.0.1:8000 \\
    --workers 2 \\
    --threads 4 \\
    --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/ojt-celery.service << EOF
[Unit]
Description=OJT Monitoring Celery Worker
After=network.target redis.service

[Service]
User=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/celery -A ojt_monitoring worker -l info --pool=solo
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# --- Nginx config ---
echo ""
echo "Configuring Nginx..."

cat > /etc/nginx/sites-available/ojt-monitoring << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Static files
    location /static/ {
        alias /opt/ojt-monitoring/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /opt/ojt-monitoring/media/;
        expires 30d;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # Django app
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
EOF

ln -sf /etc/nginx/sites-available/ojt-monitoring /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# --- Start services ---
echo ""
echo "Starting all services..."
systemctl daemon-reload
systemctl enable ojt-gunicorn ojt-celery nginx
systemctl restart ojt-gunicorn
systemctl restart ojt-celery
systemctl restart nginx

# --- Done ---
echo ""
echo "=========================================="
echo " Setup Complete!"
echo "=========================================="
echo ""
echo " Your app is running at: http://${VM_IP}"
echo ""
echo " Admin panel: http://${VM_IP}/admin/"
echo " API docs:    http://${VM_IP}/api/docs/"
echo ""
echo " Service management:"
echo "   sudo systemctl restart ojt-gunicorn   # Restart Django"
echo "   sudo systemctl restart ojt-celery     # Restart Celery"
echo "   sudo systemctl restart nginx          # Restart Nginx"
echo "   sudo journalctl -u ojt-gunicorn -f    # View Django logs"
echo ""
echo " Database credentials:"
echo "   DB Name: ${DB_NAME}"
echo "   DB User: ${DB_USER}"
echo "   DB Pass: ${DB_PASS}"
echo "   (Also saved in ${APP_DIR}/.env)"
echo ""
echo " Next steps:"
echo "   1. Update ALLOWED_HOSTS in ${APP_DIR}/.env if needed"
echo "   2. Set up GitHub Actions secrets for auto-deploy"
echo "   3. (Optional) Set up SSL with certbot"
echo "=========================================="
