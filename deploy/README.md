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

Если `setup-server.sh` уже создал в `/opt/notebook-grader` папки `logs` и
`backups`, `git clone` упадёт с `destination path is not an empty directory`.
В этом случае:

```bash
rmdir logs backups
git clone <repo-url> .
mkdir -p logs backups
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

После `chmod 600` проверить итоговые права:

```bash
ls -la .env
```

Должно отобразиться `-rw------- notebook-grader notebook-grader`.

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

Команды ниже требуют root. Под `notebook-grader` они упадут с
`Permission denied` — открыть отдельный SSH-сеанс как root либо выйти из
`su - notebook-grader` (`exit`) обратно в root-сессию.

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
ExecStart=
ExecStart=/usr/bin/caddy run --config /etc/caddy/Caddyfile
```

`ExecStart` обязательно переопределить, чтобы убрать флаг `--environ` из
дефолтного юнита — иначе Caddy при каждом старте печатает все переменные
окружения (включая `NBGRADER_SECRET_KEY` и `POSTGRES_PASSWORD`) в journal.
Пустая строка `ExecStart=` обнуляет старое значение и обязательна — без
неё systemd ругнётся на конфликт. Подробнее — раздел
«Известные особенности и подводные камни», пункты про Caddy.

```bash
systemctl daemon-reload
systemctl restart caddy
journalctl -u caddy -n 50
```

Caddy получит Let's Encrypt-сертификат по http-01 (80/443 уже открыты UFW).
Если валидация Caddyfile (`caddy validate`) выдаёт ошибки про
`request_body` или про порядок глобального блока — см. соответствующие
пункты в «Известные особенности и подводные камни».

### 12. Проверить

`https://mydomain.example` — валидный сертификат, страница приложения.

### 13. Прогнать интеграционные тесты sandbox

```bash
su - notebook-grader
cd /opt/notebook-grader
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -m integration
```

Подробнее про `python -m pytest` и про возможные таймауты docker-py на
тестах fork-bomb/infinite loop — раздел «Известные особенности и
подводные камни», пункт про pytest.

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

## Известные особенности и подводные камни

Проблемы, с которыми столкнулись при первом деплое. Прочитать до
выполнения соответствующих шагов.

### Docker Hub pull rate limit

Свежий VPS может попасть в IP-диапазон с исчерпанным анонимным лимитом
Docker Hub. Симптом — `docker compose up -d db` падает с
`You have reached your unauthenticated pull rate limit`. Лечится зеркалом
Docker Hub. От root создать `/etc/docker/daemon.json`:

```json
{
  "registry-mirrors": [
    "https://dockerhub.timeweb.cloud",
    "https://mirror.gcr.io"
  ]
}
```

Затем:

```bash
systemctl restart docker
```

После этого `docker compose up -d db` качает образы через зеркало.

### Caddy: настройка override-юнита

При выполнении `systemctl edit caddy` нужно переопределить `ExecStart`,
чтобы убрать флаг `--environ` из дефолтного юнита. Иначе при каждом
старте Caddy печатает все переменные окружения (включая
`NBGRADER_SECRET_KEY` и `POSTGRES_PASSWORD`) в системный журнал, откуда
их можно прочитать. Содержимое override-файла:

```ini
[Service]
EnvironmentFile=/opt/notebook-grader/.env
ExecStart=
ExecStart=/usr/bin/caddy run --config /etc/caddy/Caddyfile
```

Пустой `ExecStart=` обязателен — он обнуляет старое значение, иначе
systemd выдаст конфликт.

Если до правки Caddy уже был запущен и секреты попали в журнал —
после фикса вычистить журнал:

```bash
journalctl --rotate && journalctl --vacuum-time=1s
```

Параллельно — сменить сами секреты.

### Caddy: права на `/var/log/caddy/access.log`

При первом запуске Caddy может упасть с `permission denied` на
`access.log`, если файл уже был создан root'ом. От root:

```bash
chown caddy:caddy /var/log/caddy/access.log
systemctl restart caddy
```

### Caddy: формат Caddyfile при использовании `{$DOMAIN}`

Если запускать `caddy validate` от root без переменной `DOMAIN` в
окружении, парсер видит пустую подстановку и выдаёт
`unrecognized global option: request_body`. Валидировать нужно с явной
передачей переменной:

```bash
DOMAIN=mydomain.example caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

### Caddyfile: глобальный блок должен идти первым

Если в начале файла стоит комментарий перед `{ ... }`, Caddy
интерпретирует пустой блок как не-первый и ошибается с
`server block without any key is global configuration, and if used, it must be first`.
Сначала глобальный блок без ключа, потом всё остальное.


### pytest и установка dev-зависимостей

Базовый `pip install -r requirements.txt` не ставит pytest — он в
`requirements-dev.txt`. Чтобы прогнать интеграционные тесты sandbox на
сервере:

```bash
pip install -r requirements-dev.txt
python -m pytest -m integration
```

Вызов `pytest -m integration` без `python -m` падает с
`ModuleNotFoundError: No module named 'app'`, потому что в проекте не
настроен `pyproject.toml`/`conftest.py` для автодобавления корня в
`sys.path`. Конструкция `python -m` это исправляет.

На VPS с 2 vCPU часть интеграционных тестов (fork-bomb, infinite loop)
может завершаться `requests.exceptions.ConnectionError: Read timed out` —
это таймаут HTTP-клиента docker-py, а не падение теста по существу:
контейнер всё равно убивается по `TIMEOUT_SECONDS=30` из `executor.py`.
В продакшене это безопасно — sandbox-контейнер не остаётся живым,
HTTP-клиент закрывает соединение раньше.

### Задержка первого запроса в Chromium-браузерах

В некоторых Chromium-браузерах из РФ-сетей первый запрос к домену может
показывать `Stalled ≈ 10s` в DevTools. При этом серверные замеры
(`curl` с VPS, `curl` к uvicorn, `tcpdump` на сервере) показывают, что
Caddy, приложение и TLS-handshake на стороне сервера отрабатывают быстро.

Наиболее вероятно, задержка возникает внутри клиентского сетевого стека
Chromium: proxy auto-detection, DNS/DoH, socket pool, certificate verifier,
cache/network service или другая клиентская проверка. Точная причина
подтверждается через `chrome://net-export/`.

Практический обход: использовать Firefox или дождаться первого открытия
страницы. Серверного исправления, подтверждённого замерами, пока не найдено.