FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN uv sync --frozen --no-cache


ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
