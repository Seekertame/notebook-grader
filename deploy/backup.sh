#!/usr/bin/env bash
# Дамп PostgreSQL, хранение 7 дней. Запуск от notebook-grader через cron.
# Установка: crontab -e -> 0 3 * * * /opt/notebook-grader/deploy/backup.sh

set -euo pipefail

APP_DIR="/opt/notebook-grader"
BACKUP_DIR="${APP_DIR}/backups"
LOG_FILE="${BACKUP_DIR}/backup.log"
RETENTION_DAYS=7

cd "${APP_DIR}"

# shellcheck disable=SC1091
set -a
source .env
set +a

mkdir -p "${BACKUP_DIR}"

TS="$(date +%Y-%m-%d_%H%M%S)"
OUT="${BACKUP_DIR}/grader_${TS}.dump"

{
    echo "[$(date -Iseconds)] dump ${OUT}"
    # pg_dump внутри контейнера — клиент postgres на хосте не нужен.
    docker compose exec -T db \
        pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc \
        > "${OUT}"

    SIZE="$(du -h "${OUT}" | cut -f1)"
    echo "[$(date -Iseconds)] size ${SIZE}"

    DELETED=$(find "${BACKUP_DIR}" -maxdepth 1 -name 'grader_*.dump' -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)
    echo "[$(date -Iseconds)] purged ${DELETED}"
} 2>&1 | tee -a "${LOG_FILE}"
