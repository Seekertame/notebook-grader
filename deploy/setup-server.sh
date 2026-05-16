#!/usr/bin/env bash
# Первичная настройка VPS под notebook-grader. Запуск один раз от root.
# Идемпотентен. Поддерживается Ubuntu 24.04 (основная), 22.04 (fallback).

set -euo pipefail

trap 'echo "error on line $LINENO"; exit 1' ERR

APP_USER="notebook-grader"
APP_DIR="/opt/notebook-grader"

if [[ $EUID -ne 0 ]]; then
    echo "must run as root"
    exit 1
fi

if ! grep -q "Ubuntu 24" /etc/os-release && ! grep -q "Ubuntu 22" /etc/os-release; then
    echo "tested on Ubuntu 22.04 and 24.04. current OS:"
    grep PRETTY_NAME /etc/os-release || true
    read -r -p "continue? (y/N): " confirm
    [[ "$confirm" != "y" ]] && exit 1
fi

OS_VERSION_ID="$(grep -oP '(?<=^VERSION_ID=")[^"]+' /etc/os-release || true)"
echo "detected Ubuntu ${OS_VERSION_ID}"

# шаг 1: apt update/upgrade
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y

# шаг 2: base packages
apt-get install -y \
    git \
    ufw \
    fail2ban \
    curl \
    ca-certificates \
    gnupg \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https

# шаг 3: Python 3.12
if grep -q "Ubuntu 24" /etc/os-release; then
    apt-get install -y python3.12 python3.12-venv python3-pip
elif grep -q "Ubuntu 22" /etc/os-release; then
    # 22.04: Python 3.12 нет в основных репах, ставим через deadsnakes.
    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -y
    apt-get install -y python3.12 python3.12-venv python3.12-dev
    python3.12 -m ensurepip --upgrade || true
else
    echo "unsupported OS"
    exit 1
fi

if ! python3.12 --version >/dev/null 2>&1; then
    echo "python3.12 not installed"
    exit 1
fi
python3.12 --version

# шаг 4: Docker (официальный скрипт)
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh
fi
systemctl enable --now docker
docker --version

# шаг 5: Caddy (официальный apt-репозиторий caddyserver.com/docs/install)
if ! command -v caddy >/dev/null 2>&1; then
    install -d -m 0755 /usr/share/keyrings
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
        | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
        | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    apt-get update -y
    apt-get install -y caddy
fi
caddy version | head -n1

if [[ -f /etc/caddy/Caddyfile ]]; then
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
fi

# шаг 6: системный пользователь
if ! id "${APP_USER}" >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash "${APP_USER}"
fi
usermod -aG docker "${APP_USER}"

# шаг 7: рабочая директория
mkdir -p "${APP_DIR}" "${APP_DIR}/logs" "${APP_DIR}/backups"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

# шаг 8: UFW
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp comment 'HTTP (Caddy)'
ufw allow 443/tcp comment 'HTTPS (Caddy)'
ufw --force enable

# шаг 9: fail2ban (sshd jail из коробки)
systemctl enable --now fail2ban

# шаг 10: каталог логов Caddy
mkdir -p /var/log/caddy
chown -R caddy:caddy /var/log/caddy 2>/dev/null || true

# шаг 11: права на .env (если уже создан)
if [[ -f "${APP_DIR}/.env" ]]; then
    chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
    chmod 600 "${APP_DIR}/.env"
else
    echo "${APP_DIR}/.env not present yet; chmod 600 it after copy from .env.example.production"
fi

cat <<EOF

готово.

дальнейшие шаги:

  1. su - ${APP_USER}

  2. cd ${APP_DIR} && git clone <repo-url> .

  3. python3.12 -m venv .venv && source .venv/bin/activate
     pip install --upgrade pip && pip install -r requirements.txt

  4. cp .env.example.production .env && chmod 600 .env && \$EDITOR .env

  5. docker compose up -d db
     docker build -t notebook-grader-sandbox sandbox

  6. alembic upgrade head

  7. от имени root:
     cp deploy/notebook-grader.service /etc/systemd/system/
     systemctl daemon-reload
     systemctl enable --now notebook-grader

  8. от имени root:
     cp deploy/Caddyfile /etc/caddy/Caddyfile
     caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
     # см. README про override caddy.service
     systemctl daemon-reload && systemctl restart caddy

  9. crontab -e от имени ${APP_USER}:
     0 3 * * * /opt/notebook-grader/deploy/backup.sh

EOF
