FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=development \
    DEMO_AUTOSEED=true \
    DATABASE_URL=sqlite:////app/data/drishti.db \
    REPORT_STORAGE_PATH=/app/reports

WORKDIR /app

# Install curl for container health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Ensure storage directories exist
RUN mkdir -p /app/data /app/reports

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=5 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
