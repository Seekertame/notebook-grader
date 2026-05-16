# Деплой notebook-grader на одиночный VPS

Приложение и Caddy работают на хосте как systemd-сервисы. PostgreSQL — в Docker
через docker compose. Sandbox-контейнеры приложение запускает само через Docker
SDK по unix-сокету `/var/run/docker.sock`.

## Требования к VPS

| Параметр       | Значение                                                                                                                 |
|----------------|--------------------------------------------------------------------------------------------------------------------------|
| Виртуализация  | KVM (не OpenVZ — Docker и cgroup-лимиты иначе не работают).                                                              |
| ОС             | Ubuntu 24.04 LTS (Python 3.12 — системный пакет, без сторонних PPA). Допустима 22.04 LTS — `setup-server.sh` подтянет Python 3.12 через PPA `deadsnakes`. |
| CPU            | 2 vCPU x86_64                                                                                                            |
| RAM            | 4 GB                                                                                                                     |
| Диск           | >= 20 GB SSD (ТЗ п. 4.4.2).                                                                                              |
| Локация        | В России                                                                                                                 |
| SSH            | Возможность загрузить свой SSH-ключ при заказе.                                                                          |

Дистрибутивы не-Ubuntu (Debian, AlmaLinux и т. п.) скриптом не поддерживаются.

## Состав файлов

| Файл                          | Назначение                              |
|-------------------------------|-----------------------------------------|
| `deploy/setup-server.sh`      | Первичная настройка VPS (один раз)      |
| `deploy/deploy.sh`            | Регулярное обновление сервиса           |
| `deploy/backup.sh`            | Дамп PostgreSQL для cron                |
| `deploy/notebook-grader.service` | systemd-юнит для uvicorn             |
| `deploy/Caddyfile`            | Caddy: reverse-proxy + HTTPS            |
| `docker-compose.yml`          | Только `db` (PostgreSQL)                |
| `.env.example.production`     | Шаблон `.env` для прод-окружения        |
| `sandbox/Dockerfile`          | Образ песочницы                         |

## Пошаговая инструкция

Ниже `HOST` — IP сервера, `mydomain.example` — ваше доменное имя.

### 1. Купить VPS, получить root SSH

При заказе загрузите публичный SSH-ключ. Запишите выданный IP.

### 2. Подключиться, отключить парольную авторизацию

```bash
ssh-copy-id root@HOST
ssh root@HOST

# на сервере:
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl reload ssh
```

### 3. Залить и запустить setup-server.sh

```bash
scp deploy/setup-server.sh root@HOST:/tmp/
ssh root@HOST 'bash /tmp/setup-server.sh'
```

Скрипт идемпотентен — можно запускать повторно.

### 4. Клонировать репозиторий

```bash
su - notebook-grader
cd /opt/notebook-grader
git clone <repo-url> .
```

### 5. venv и зависимости

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Заполнить .env

```bash
cp .env.example.production .env
chmod 600 .env
$EDITOR .env
```

Сгенерировать секреты:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # NBGRADER_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # POSTGRES_PASSWORD
```

Тот же пароль подставить в `NBGRADER_DATABASE_URL`. В `NBGRADER_ALLOWED_HOSTS`
указать домен и публичный IP (loopback не нужен — `/healthz` и `/readyz`
обходят TrustedHostMiddleware в коде). `DOMAIN` — без `https://`.

### 7. Поднять БД и применить миграции

```bash
docker compose up -d db
docker compose ps        # дождаться healthy
alembic upgrade head
```

### 8. Собрать образ sandbox

```bash
docker build -t notebook-grader-sandbox sandbox
```

### 9. Установить systemd-юнит приложения

```bash
# от root:
cp /opt/notebook-grader/deploy/notebook-grader.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now notebook-grader
systemctl status notebook-grader
```

Логи: `journalctl -u notebook-grader -f`.

### 10. DNS

A-запись `mydomain.example → HOST`. Проверка: `dig +short mydomain.example`.

### 11. Установить и сконфигурировать Caddy

```bash
# от root:
cp /opt/notebook-grader/deploy/Caddyfile /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Caddyfile ожидает переменную `DOMAIN`. Прокинуть её через override юнита Caddy,
чтобы не править `/lib/systemd/system/caddy.service` (он перезатрётся при
`apt upgrade`):

```bash
systemctl edit caddy
```

Содержимое `/etc/systemd/system/caddy.service.d/override.conf`:

```ini
[Service]
EnvironmentFile=/opt/notebook-grader/.env
```

Override дополняет, а не заменяет основной юнит — `ExecStart` не трогать.

```bash
systemctl daemon-reload
systemctl restart caddy
journalctl -u caddy -n 50
```

Caddy получит Let's Encrypt-сертификат по http-01 (80/443 уже открыты UFW).

### 12. Проверить

`https://mydomain.example` — валидный сертификат, страница приложения.

### 13. Прогнать интеграционные тесты sandbox

```bash
su - notebook-grader
cd /opt/notebook-grader
source .venv/bin/activate
pytest -m integration
```

### 14. Создать первого преподавателя

Через UI на `https://mydomain.example`: регистрация, логин, загрузка тестового
задания, прогон.

### 15. Cron на бэкапы

Под `notebook-grader`:

```bash
crontab -e
```

```
0 3 * * * /opt/notebook-grader/deploy/backup.sh
```

Каждый день в 03:00, хранение 7 дней, лог в `backups/backup.log`.

## sudo NOPASSWD для deploy.sh

`deploy.sh` дёргает `sudo systemctl restart notebook-grader`. От root:

```bash
visudo -f /etc/sudoers.d/notebook-grader
```

```
notebook-grader ALL=(root) NOPASSWD: /usr/bin/systemctl restart notebook-grader
notebook-grader ALL=(root) NOPASSWD: /usr/bin/systemctl status notebook-grader
```

Полный путь обязателен — без него sudo разрешит любой `systemctl`, найденный
через `$PATH` вызывающего пользователя (риск PATH-shadowing).

Проверка:

```bash
sudo -u notebook-grader sudo -n /usr/bin/systemctl status notebook-grader
```

## Регулярные обновления

```bash
cd /opt/notebook-grader
./deploy/deploy.sh
```

`git pull` → `pip install` → `compose up -d db` → ждёт `pg_isready` →
`alembic upgrade head` → `systemctl restart` → health-check на `/healthz`.

## Восстановление из дампа

```bash
ls -lh /opt/notebook-grader/backups/

sudo systemctl stop notebook-grader

cat backups/grader_2026-05-15_030000.dump | \
    docker compose exec -T db \
        pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists

sudo systemctl start notebook-grader
```

## Полезные команды

| Что                              | Команда                                       |
|----------------------------------|-----------------------------------------------|
| Лог приложения                   | `journalctl -u notebook-grader -f`            |
| Лог Caddy                        | `journalctl -u caddy -f`                      |
| Access-лог Caddy                 | `tail -f /var/log/caddy/access.log`           |
| Лог БД                           | `docker compose logs -f db`                   |
| Статус UFW                       | `sudo ufw status verbose`                     |
| Статус fail2ban                  | `sudo fail2ban-client status sshd`            |
| Перечитать Caddy                 | `sudo systemctl reload caddy`                 |
| Активные sandbox-контейнеры      | `docker ps --filter ancestor=notebook-grader-sandbox` |
| Liveness                         | `curl http://127.0.0.1:8000/healthz`          |
| Readiness (вкл. БД)              | `curl http://127.0.0.1:8000/readyz`           |
