#!/usr/bin/env bash
# Kemele CPMS — Nightly Backup Script
#
# Dumps the PostgreSQL database (pg_dump custom format) and tars the media
# directory. Keeps 30 days of backups. Reads DATABASE_URL (and MEDIA_ROOT)
# from the application .env file.
#
# Crontab example (run nightly at 02:00 as root, or any user that can read
# the .env file and connect to the database):
#   0 2 * * * /home/kemelecpms/kemelecpms/deploy/backup.sh >> /var/log/kemelecpms_backup.log 2>&1
#
set -euo pipefail

APP_DIR="${APP_DIR:-/home/kemelecpms/kemelecpms}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/kemelecpms}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: env file not found: $ENV_FILE" >&2
    exit 1
fi

# Read a single VAR=value entry from the .env file (ignores comments,
# strips optional surrounding quotes).
read_env_var() {
    local name="$1"
    grep -E "^${name}=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

DATABASE_URL="$(read_env_var DATABASE_URL)"
MEDIA_ROOT="$(read_env_var MEDIA_ROOT)"
MEDIA_ROOT="${MEDIA_ROOT:-/home/kemelecpms/media}"

if [[ -z "$DATABASE_URL" ]]; then
    echo "ERROR: DATABASE_URL not set in $ENV_FILE" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR/db" "$BACKUP_DIR/media"
chmod 700 "$BACKUP_DIR"

echo "==> Kemele CPMS backup — $TIMESTAMP"

# --- Database backup (pg_dump custom format, compressed) ---
DB_BACKUP_FILE="$BACKUP_DIR/db/kemelecpms_db_${TIMESTAMP}.dump"
echo "--- Dumping database to $DB_BACKUP_FILE ---"
# pg_dump accepts a connection URL directly; custom format (-Fc) is
# compressed and restorable with pg_restore.
pg_dump --format=custom --no-owner --dbname="$DATABASE_URL" --file="$DB_BACKUP_FILE"
echo "Database dump: $(du -h "$DB_BACKUP_FILE" | cut -f1)"

# --- Media backup ---
if [[ -d "$MEDIA_ROOT" ]]; then
    MEDIA_BACKUP_FILE="$BACKUP_DIR/media/kemelecpms_media_${TIMESTAMP}.tar.gz"
    echo "--- Archiving media dir $MEDIA_ROOT to $MEDIA_BACKUP_FILE ---"
    tar -czf "$MEDIA_BACKUP_FILE" -C "$(dirname "$MEDIA_ROOT")" "$(basename "$MEDIA_ROOT")"
    echo "Media archive: $(du -h "$MEDIA_BACKUP_FILE" | cut -f1)"
else
    echo "WARNING: media directory $MEDIA_ROOT does not exist, skipping media backup" >&2
fi

# --- Retention: delete backups older than RETENTION_DAYS ---
echo "--- Pruning backups older than $RETENTION_DAYS days ---"
find "$BACKUP_DIR/db" -name "kemelecpms_db_*.dump" -type f -mtime +"$RETENTION_DAYS" -print -delete
find "$BACKUP_DIR/media" -name "kemelecpms_media_*.tar.gz" -type f -mtime +"$RETENTION_DAYS" -print -delete

echo "==> Backup complete: $BACKUP_DIR"
