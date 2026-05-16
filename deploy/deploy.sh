#!/usr/bin/env bash
# Обновление сервиса. Запуск от notebook-grader в /opt/notebook-grader.
# Предусловие: sudo NOPASSWD на /usr/bin/systemctl restart notebook-grader.

set -euo pipefail

APP_DIR="/opt/notebook-grader"
VENV="${APP_DIR}/.venv"
HEALTH_URL="http://127.0.0.1:8000/healthz"

cd "${APP_DIR}"

echo "[1/7] git pull"
git pull --ff-only origin main

echo "[2/7] pip install"
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/7] docker compose up -d db"
docker compose up -d db

echo "[4/7] wait for db (up to 30s)"
DEADLINE=$(( $(date +%s) + 30 ))
until docker compose exec -T db pg_isready -U "${POSTGRES_USER:-grader}" >/dev/null 2>&1; do
    if (( $(date +%s) >= DEADLINE )); then
        echo "db not ready in 30s"
        docker compose logs --tail=30 db
        exit 1
    fi
    sleep 1
done

echo "[5/7] alembic upgrade head"
alembic upgrade head

echo "[6/7] systemctl restart notebook-grader"
sudo /usr/bin/systemctl restart notebook-grader

echo "[7/7] health-check"
for i in $(seq 1 15); do
    if curl -fsS "${HEALTH_URL}" -o /dev/null; then
        echo "ok (${i}s)"
        exit 0
    fi
    sleep 1
done

echo "health-check failed after 15s"
sudo /usr/bin/systemctl status notebook-grader --no-pager | tail -n 30
exit 1
