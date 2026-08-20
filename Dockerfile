FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    DASHBOARD_PASSCODE=90038

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure data directory exists
RUN mkdir -p /app/data /app/data/digests

EXPOSE 8080

# Run uvicorn server binding to dynamic Cloud Run $PORT
CMD ["sh", "-c", "uvicorn src.dashboard.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
