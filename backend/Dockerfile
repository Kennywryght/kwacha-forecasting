# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Prophet and statsmodels
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire backend code
COPY backend/ .

# Copy data directory if it exists
COPY data/ ./data/

# Create necessary directories
RUN mkdir -p /app/data /app/ml/artifacts /tmp/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:////tmp/data/mwk_forecasting.db
ENV ENVIRONMENT=production
ENV PORT=8000

# Expose port
EXPOSE 8000

# Create startup script
RUN echo '#!/bin/bash\n\
echo "🚀 Starting KwachaCast API..."\n\
echo "📊 Initializing database..."\n\
python -c "from db.database import init_db; init_db()"\n\
echo "📈 Checking for data..."\n\
python -c "\n\
from db.database import SessionLocal\n\
from db.models import ExchangeRate\n\
from sqlalchemy import func\n\
import pandas as pd\n\
import os\n\
\n\
db = SessionLocal()\n\
count = db.query(func.count(ExchangeRate.id)).scalar()\n\
print(f\"Database has {count} rows\")\n\
\n\
if count == 0:\n\
    print(\"Seeding initial data...\")\n\
    csv_paths = [\n\
        \"data/raw/mwk_usd_final_dataset.csv\",\n\
        \"data/processed/mwk_usd_clean.csv\",\n\
    ]\n\
    for path in csv_paths:\n\
        if os.path.exists(path):\n\
            print(f\"Loading {path}...\")\n\
            df = pd.read_csv(path)\n\
            if \"date\" in df.columns and \"rate\" in df.columns:\n\
                df[\"date\"] = pd.to_datetime(df[\"date\"])\n\
                for _, row in df.iterrows():\n\
                    try:\n\
                        r = ExchangeRate(\n\
                            date=row[\"date\"].date(),\n\
                            rate=float(row[\"rate\"]),\n\
                            source=\"seed_data\"\n\
                        )\n\
                        db.add(r)\n\
                    except:\n\
                        pass\n\
                db.commit()\n\
                print(f\"Seeded {len(df)} rows\")\n\
                break\n\
    else:\n\
        print(\"No CSV found, starting empty\")\n\
db.close()\n\
"\n\
echo "✅ Startup complete, launching API..."\n\
uvicorn main:app --host 0.0.0.0 --port \\n\
' > /app/start.sh && chmod +x /app/start.sh

# Use the startup script
CMD ["/bin/bash", "/app/start.sh"]
