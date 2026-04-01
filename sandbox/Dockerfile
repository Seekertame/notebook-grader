FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash student

RUN pip install --no-cache-dir nbclient ipykernel

WORKDIR /app
RUN chown student:student /app

USER student
