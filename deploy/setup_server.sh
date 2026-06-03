#!/usr/bin/env bash
# Kemele CPMS — Fresh Server Setup Script
# Run as root on a clean Ubuntu 22.04 LTS server
set -euo pipefail

APP_USER="kemelecpms"
APP_DIR="/home/$APP_USER/kemelecpms"

echo "==> Setting up Kemele CPMS Server"

echo "--- System packages ---"
apt-get update -y
apt-get install -y \
    python3.11 python3.11-dev python3.11-venv python3-pip \
    build-essential libpq-dev \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    git curl wget \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev \
    libjpeg-dev libpng-dev

echo "--- Create app user ---"
id -u $APP_USER &>/dev/null || useradd -m -s /bin/bash $APP_USER
usermod -aG www-data $APP_USER

echo "--- Install Pipenv ---"
pip3 install pipenv

echo "--- Set up PostgreSQL ---"
sudo -u postgres psql -c "CREATE USER cpms_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE kemelecpms_db OWNER cpms_user;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE kemelecpms_db TO cpms_user;" 2>/dev/null || true

echo "--- Configure Redis ---"
systemctl enable redis-server
systemctl start redis-server

echo "--- Runtime directories ---"
mkdir -p /run/gunicorn /run/celery /var/log/gunicorn /var/log/celery
chown www-data:www-data /run/gunicorn /run/celery /var/log/gunicorn /var/log/celery

echo "--- Clone/setup application ---"
sudo -u $APP_USER git clone https://github.com/zyakap/kemelecpms.git $APP_DIR 2>/dev/null || true
cd $APP_DIR
sudo -u $APP_USER cp .env.example .env
echo "*** IMPORTANT: Edit $APP_DIR/.env with production values ***"

echo "--- Install systemd services ---"
cp $APP_DIR/deploy/systemd/kemelecpms.socket /etc/systemd/system/
cp $APP_DIR/deploy/systemd/kemelecpms.service /etc/systemd/system/
cp $APP_DIR/deploy/systemd/kemelecpms-celery.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable kemelecpms.socket kemelecpms kemelecpms-celery

echo "--- Configure Nginx ---"
cp $APP_DIR/nginx/kemelecpms.conf /etc/nginx/sites-available/kemelecpms
ln -sf /etc/nginx/sites-available/kemelecpms /etc/nginx/sites-enabled/kemelecpms
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo ""
echo "==> Server setup complete. Next steps:"
echo "  1. Edit $APP_DIR/.env with your production settings"
echo "  2. Run: cd $APP_DIR && pipenv install --deploy"
echo "  3. Run: DJANGO_SETTINGS_MODULE=config.settings.production pipenv run python manage.py migrate"
echo "  4. Run: DJANGO_SETTINGS_MODULE=config.settings.production pipenv run python manage.py createsuperuser"
echo "  5. Run: DJANGO_SETTINGS_MODULE=config.settings.production pipenv run python manage.py collectstatic"
echo "  6. Obtain SSL: certbot --nginx -d cpms.kemeleconstruction.com.pg"
echo "  7. Start services: systemctl start kemelecpms.socket kemelecpms"
echo "  8. Reload nginx: systemctl reload nginx"
