#!/usr/bin/env bash
# Kemele CPMS — Production Deployment Script
# Run as: sudo -u www-data bash deploy/deploy.sh
set -euo pipefail

APP_DIR="/home/kemelecpms/kemelecpms"
VENV_PYTHON="/home/kemelecpms/.local/share/virtualenvs/kemelecpms/bin/python"
VENV_PIP="/home/kemelecpms/.local/share/virtualenvs/kemelecpms/bin/pip"

echo "==> Kemele CPMS Deployment — $(date)"

echo "--- Pulling latest code ---"
cd "$APP_DIR"
git pull origin main

echo "--- Installing/updating Python dependencies ---"
cd "$APP_DIR"
PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy --ignore-pipfile

echo "--- Applying database migrations ---"
DJANGO_SETTINGS_MODULE=config.settings.production "$VENV_PYTHON" manage.py migrate --no-input

echo "--- Collecting static files ---"
DJANGO_SETTINGS_MODULE=config.settings.production "$VENV_PYTHON" manage.py collectstatic --no-input --clear

echo "--- Restarting Gunicorn ---"
sudo systemctl reload kemelecpms || sudo systemctl restart kemelecpms

echo "--- Restarting Celery ---"
sudo systemctl restart kemelecpms-celery || true
sudo systemctl restart kemelecpms-celerybeat || true

echo "--- Checking service status ---"
sudo systemctl is-active kemelecpms && echo "Gunicorn: RUNNING" || echo "Gunicorn: FAILED"
sudo systemctl is-active kemelecpms-celery && echo "Celery Worker: RUNNING" || echo "Celery Worker: not running"
sudo systemctl is-active kemelecpms-celerybeat && echo "Celery Beat: RUNNING" || echo "Celery Beat: not running"

echo "==> Deployment complete"
