#!/usr/bin/env bash
# Kemele CPMS — Restore Script (counterpart to backup.sh)
#
# Restores a pg_dump custom-format database dump and/or a media tar archive
# produced by deploy/backup.sh. Reads DATABASE_URL (and MEDIA_ROOT) from the
# application .env file.
#
# Usage:
#   deploy/restore.sh --db /var/backups/kemelecpms/db/kemelecpms_db_20260611_020000.dump
#   deploy/restore.sh --media /var/backups/kemelecpms/media/kemelecpms_media_20260611_020000.tar.gz
#   deploy/restore.sh --db <dump> --media <tar.gz>
#
# WARNING: database restore drops and recreates objects (--clean). Stop the
# application services first:
#   systemctl stop kemelecpms kemelecpms-celery kemelecpms-celerybeat
#
set -euo pipefail

APP_DIR="${APP_DIR:-/home/kemelecpms/kemelecpms}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"

DB_DUMP=""
MEDIA_ARCHIVE=""

usage() {
    grep '^#' "$0" | sed 's/^# \{0,1\}//'
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --db)    DB_DUMP="${2:-}"; shift 2 ;;
        --media) MEDIA_ARCHIVE="${2:-}"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown argument: $1" >&2; usage ;;
    esac
done

if [[ -z "$DB_DUMP" && -z "$MEDIA_ARCHIVE" ]]; then
    echo "ERROR: specify --db <dump file> and/or --media <tar.gz archive>" >&2
    usage
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: env file not found: $ENV_FILE" >&2
    exit 1
fi

read_env_var() {
    local name="$1"
    grep -E "^${name}=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

DATABASE_URL="$(read_env_var DATABASE_URL)"
MEDIA_ROOT="$(read_env_var MEDIA_ROOT)"
MEDIA_ROOT="${MEDIA_ROOT:-/home/kemelecpms/media}"

# --- Database restore ---
if [[ -n "$DB_DUMP" ]]; then
    if [[ ! -f "$DB_DUMP" ]]; then
        echo "ERROR: dump file not found: $DB_DUMP" >&2
        exit 1
    fi
    if [[ -z "$DATABASE_URL" ]]; then
        echo "ERROR: DATABASE_URL not set in $ENV_FILE" >&2
        exit 1
    fi
    echo "--- Restoring database from $DB_DUMP ---"
    read -r -p "This will OVERWRITE the current database. Continue? [y/N] " confirm
    if [[ "${confirm,,}" != "y" ]]; then
        echo "Aborted."
        exit 1
    fi
    pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" "$DB_DUMP"
    echo "Database restore complete."
fi

# --- Media restore ---
if [[ -n "$MEDIA_ARCHIVE" ]]; then
    if [[ ! -f "$MEDIA_ARCHIVE" ]]; then
        echo "ERROR: media archive not found: $MEDIA_ARCHIVE" >&2
        exit 1
    fi
    echo "--- Restoring media into $(dirname "$MEDIA_ROOT") from $MEDIA_ARCHIVE ---"
    mkdir -p "$(dirname "$MEDIA_ROOT")"
    tar -xzf "$MEDIA_ARCHIVE" -C "$(dirname "$MEDIA_ROOT")"
    echo "Media restore complete. Verify ownership, e.g.:"
    echo "  chown -R www-data:www-data $MEDIA_ROOT"
fi

echo "==> Restore finished. Restart services:"
echo "  systemctl start kemelecpms kemelecpms-celery kemelecpms-celerybeat"
