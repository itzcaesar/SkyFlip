FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace/apps/api

WORKDIR /workspace
COPY apps/api/pyproject.toml /workspace/apps/api/pyproject.toml
RUN pip install --upgrade pip && pip install "/workspace/apps/api[dev]"

COPY apps/api /workspace/apps/api
COPY apps/worker /workspace/apps/worker
