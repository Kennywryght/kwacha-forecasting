FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y gcc g++ curl && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Copy data if available
COPY ../data/ ./data/ 2>/dev/null || echo "No data directory to copy"

# Create directories and set permissions
RUN mkdir -p /tmp/data /app/data /app/ml/artifacts && chmod 777 /tmp/data

# Copy prestart script
COPY prestart.sh /app/prestart.sh
RUN chmod +x /app/prestart.sh

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:////tmp/data/mwk_forecasting.db
ENV PORT=8000

EXPOSE 8000

# Run prestart then start
CMD ["/bin/bash", "-c", "/app/prestart.sh && uvicorn main:app --host 0.0.0.0 --port "]
