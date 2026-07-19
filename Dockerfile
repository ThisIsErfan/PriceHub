FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (only the app package; see .dockerignore).
COPY app ./app

EXPOSE 8100

# --no-access-log: uvicorn's per-request line is redundant here — every request is
# already recorded in partner_usage_daily, and nginx keeps its own access log.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100", "--no-access-log", "--log-level", "warning"]
