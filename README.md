# Notebook Grader

Веб-сервис для автоматической проверки студенческих работ в формате Jupyter Notebook (`.ipynb`).

Преподаватель создаёт задание, загружает шаблон notebook и список проверяемых задач, после чего может массово загружать работы студентов. Каждое решение запускается в изолированном Docker-контейнере, результат сравнивается с эталоном, итог — сводная таблица с баллами и статусами и экспорт в CSV.

> Курсовой проект: Т. З. Бюрчиев, группа БПИ 248.

---

## Содержание

- [Возможности](#возможности)
- [Технологический стек](#технологический-стек)
- [Требования](#требования)
- [Запуск локально (пошагово)](#запуск-локально-пошагово)
- [Проверка, что всё работает](#проверка-что-всё-работает)
- [Формат notebook-файлов](#формат-notebook-файлов)
- [Типы проверки](#типы-проверки)
- [Sandbox](#sandbox)
- [Миграции базы данных](#миграции-базы-данных)
- [Тесты](#тесты)
- [Структура проекта](#структура-проекта)
- [Основные страницы и API](#основные-страницы-и-api)
- [Возможные проблемы (troubleshooting)](#возможные-проблемы-troubleshooting)
- [Безопасность и публикация](#безопасность-и-публикация)

---

## Возможности

- регистрация и авторизация преподавателя по email (JWT);
- создание, редактирование и удаление заданий;
- загрузка шаблона `.ipynb` и автоматическое создание задач по тегам ячеек;
- массовая загрузка студенческих notebooks (до 10 за операцию);
- запуск решений в Docker-sandbox с ограничениями по памяти, CPU, времени и сети;
- три типа проверки:
  - сравнение `stdout` с эталонным ответом,
  - проверка по набору тестов через `stdin`/`stdout`,
  - выполнение преподавательского кода-ассерта (`reference_assert`);
- общая `setup`-ячейка, исполняемая перед каждой задачей;
- сводная таблица результатов и выгрузка отчёта в CSV.

---

## Технологический стек

- Python 3.12, FastAPI, Uvicorn
- SQLAlchemy 2 + Alembic
- PostgreSQL 15 (через Docker Compose)
- Docker SDK for Python (`docker==7.1.0`)
- `nbformat` — парсинг notebook
- Pytest — тесты
- Frontend: HTML + Bootstrap + ванильный JavaScript

---

## Требования

Перед запуском должны быть установлены:

| Компонент       | Версия              | Зачем                                |
| --------------- | ------------------- | ------------------------------------ |
| Python          | 3.12 (или 3.11+)    | основной runtime                     |
| Docker Engine   | свежий              | sandbox для студенческого кода       |
| Docker Compose  | v2 (`docker compose`) | локальный PostgreSQL               |
| git             | любой               | клонирование репозитория             |

Под Windows проект разрабатывается в WSL2 (Ubuntu). Docker Desktop должен быть запущен и интегрирован с используемым WSL-дистрибутивом (`Settings → Resources → WSL Integration`).

---

## Запуск локально (пошагово)

> Все команды выполняются из корня проекта в Linux / WSL-shell. Подразумевается, что Docker запущен.

### 1. Клонировать репозиторий

```bash
git clone <repository-url> notebook-grader
cd notebook-grader
```

### 2. Создать и активировать виртуальное окружение

Рекомендуется хранить venv **вне** папки проекта:

```bash
python3 -m venv "$HOME/.virtualenvs/notebook-grader"
source "$HOME/.virtualenvs/notebook-grader/bin/activate"
```

После активации в приглашении должен появиться префикс `(notebook-grader)`. В дальнейших шагах подразумевается, что venv активирован.

### 3. Установить Python-зависимости

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Создать файл окружения `.env`

```bash
cp .env.example .env
```

Откройте `.env` и заполните два значения:

```env
NBGRADER_SECRET_KEY=<секрет для подписи JWT>
NBGRADER_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/grader_db
```

Сгенерировать секретный ключ:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

> Логин/пароль БД в строке подключения должны совпадать с `docker-compose.yml`. По умолчанию там `postgres / postgres`.

Загрузить переменные в текущий shell (нужно для `alembic` и `uvicorn`):

```bash
set -a && source .env && set +a
```

### 5. Поднять PostgreSQL

```bash
docker compose up -d db
```

Проверить, что контейнер жив:

```bash
docker compose ps
```

Контейнер `db` должен быть в состоянии `Up` (healthy/running) и слушать порт `5432`.

### 6. Применить миграции

```bash
alembic upgrade head
```

Команда создаст таблицы в `grader_db`. Если получаете `connection refused`, БД ещё не успела стартовать — подождите 5–10 секунд и повторите.

### 7. Собрать Docker-образ sandbox

Без этого образа sandbox-проверка работ упадёт.

```bash
docker build -t notebook-grader-sandbox sandbox
```

Образ собирается один раз. Пересобирать нужно только при изменениях в `sandbox/Dockerfile`.

### 8. Запустить веб-сервер

```bash
uvicorn app.main:app --reload
```

Готово. Откройте в браузере:

- интерфейс: <http://127.0.0.1:8000>
- Swagger UI: <http://127.0.0.1:8000/docs>

### Запуск в следующий раз (короткая шпаргалка)

```bash
cd notebook-grader
source "$HOME/.virtualenvs/notebook-grader/bin/activate"
set -a && source .env && set +a
docker compose up -d db
uvicorn app.main:app --reload
```

---

## Проверка, что всё работает

1. На `/` зарегистрируйте преподавателя.
2. На `/dashboard` создайте задание.
3. Загрузите шаблон `.ipynb` — задачи должны автоматически распознаться по тегам.
4. Загрузите тестовое решение студента.
5. На странице задания должна появиться строка с баллами и статусами.

Если есть пустой шаблон для пробы, можно использовать готовые файлы из папки `ipynb files/`.

---

## Формат notebook-файлов

### Идентификация студента

В notebook должна быть markdown-ячейка со служебным маркером `<!-- STUDENT_INFO -->`:

```markdown
<!-- STUDENT_INFO -->
**ФИО:** Иванов Иван Иванович
**Группа:** БПИ241
```

### Задачи

Решения задач распознаются по тегам code-ячеек в формате `task:<код>`:

```
task:A1
task:1
task:sum
```

### Общий setup

Опциональная code-ячейка с тегом `setup` исполняется перед каждой задачей — удобно для импортов и общих функций.

> Если в работе студента нет ячейки с нужным `task:<код>`, задача получает 0 баллов со статусом «структура notebook не соответствует заданию».

---

## Типы проверки

### По эталонному ответу

Код студента запускается, `stdout` сравнивается с ожидаемым значением.

- завершающие пробелы и переносы строк игнорируются;
- числа с плавающей точкой сравниваются с округлением до 4 знаков.

### По набору тестов

Для каждого тест-кейса код запускается заново: вход подаётся через `stdin`, результат проверяется по `stdout`.

### Через `reference_assert`

К решению студента добавляется проверочный код преподавателя. Если итоговый запуск проходит без исключений — задача засчитана. Любое исключение (включая `AssertionError`) → 0 баллов.

Балл всегда выставляется по принципу «всё или ничего»: либо максимум, либо 0.

---

## Sandbox

Студенческий код выполняется в Docker-контейнере с образом `notebook-grader-sandbox`. Текущие ограничения:

- сеть отключена (`network=none`);
- корневая ФС read-only, `/tmp` смонтирован как tmpfs;
- лимит памяти: **1 GiB**;
- лимит CPU: **1 ядро**;
- тайм-аут выполнения: **30 секунд**.

Пересобрать образ:

```bash
docker build -t notebook-grader-sandbox sandbox
```

---

## Миграции базы данных

Файлы миграций — `alembic/versions/`.

```bash
# применить все миграции
alembic upgrade head

# создать новую миграцию из изменений в моделях
alembic revision --autogenerate -m "описание изменения"

# откатить на одну ревизию назад
alembic downgrade -1
```

---

## Тесты

```bash
# все тесты
pytest

# только парсер
pytest tests/test_parser.py -v
```

---

## Структура проекта

```text
notebook-grader/
├── alembic/                 # миграции БД
│   └── versions/
├── app/
│   ├── api/endpoints/       # FastAPI endpoints (auth, assignments, submissions, template)
│   ├── assets/              # эталонные notebook-шаблоны
│   ├── core/                # настройки, БД, авторизация
│   ├── grader/              # parser, executor (sandbox), checker, reporter
│   ├── models/              # SQLAlchemy и Pydantic-модели
│   ├── utils/               # вспомогательные функции
│   └── main.py              # точка входа FastAPI
├── sandbox/
│   └── Dockerfile           # образ для безопасного выполнения кода
├── static/                  # JS и статика фронтенда
├── templates/               # HTML-страницы (Jinja)
├── tests/                   # pytest-тесты
├── ipynb files/             # примеры notebook-ов
├── docker-compose.yml       # локальный PostgreSQL
├── alembic.ini
├── requirements.txt
├── .env.example
└── README.md
```

---

## Основные страницы и API

| Маршрут                          | Назначение                                          |
| -------------------------------- | --------------------------------------------------- |
| `/`                              | вход и регистрация преподавателя                    |
| `/dashboard`                     | список заданий преподавателя                        |
| `/assignment/{assignment_id}`    | задачи, шаблон, загрузка работ и сводный отчёт      |
| `/docs`                          | автогенерируемая документация API (Swagger UI)      |
| `/redoc`                         | альтернативный просмотр API (ReDoc)                 |

---

## Возможные проблемы (troubleshooting)

**`alembic` падает с `connection refused`**
Контейнер PostgreSQL ещё не успел стартовать. Подождите 5–10 секунд после `docker compose up -d db` и повторите.

**`docker: permission denied while trying to connect to the Docker daemon socket`**
Текущий пользователь не в группе `docker`. На Linux: `sudo usermod -aG docker $USER`, затем перелогиниться. В WSL — включить интеграцию с дистрибутивом в Docker Desktop.

**`Cannot connect to the Docker daemon`** при проверке работ
Не запущен Docker (Docker Desktop в Windows или `dockerd` в Linux). Запустите его и повторите.

**`docker: Error response from daemon: ... notebook-grader-sandbox not found`**
Забыли собрать sandbox-образ. Выполните `docker build -t notebook-grader-sandbox sandbox`.

**`NBGRADER_SECRET_KEY` / `NBGRADER_DATABASE_URL` не подхватываются**
Переменные не загружены в shell. Перед `alembic`/`uvicorn` выполните `set -a && source .env && set +a` в том же терминале.

**Порт 5432 уже занят**
Локально уже запущен PostgreSQL. Остановите его или замените в `docker-compose.yml` маппинг `"5432:5432"` на `"5433:5432"` и обновите `NBGRADER_DATABASE_URL` в `.env`.


