FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash student

# Версии пакетов зафиксированы для воспроизводимой сборки sandbox-образа.
# Обновлять синхронно с requirements.txt основного приложения.
RUN pip install --no-cache-dir \
        nbclient==0.10.2 \
        ipykernel==6.30.0 \
        numpy==2.1.3 \
        pandas==2.2.3 \
        scipy==1.14.1 \
        sympy==1.13.3

WORKDIR /app
RUN chown student:student /app

USER student
