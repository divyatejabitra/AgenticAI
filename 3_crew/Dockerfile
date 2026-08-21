FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY financial_researcher ./financial_researcher
COPY stock_picker ./stock_picker
COPY backend ./backend

WORKDIR /app/backend
RUN uv sync --frozen --no-dev

EXPOSE 7860

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
