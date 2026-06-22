#!/bin/bash
# Pre-start script for Render

echo "?? Setting up KwachaCast..."

# Create all necessary directories
mkdir -p /tmp/data
mkdir -p /app/data
mkdir -p /app/ml/artifacts

# Set permissions
chmod 777 /tmp/data

echo "?? Initializing database..."
cd /app

# Initialize database tables
python -c "
import os
import sys
sys.path.insert(0, '/app')

# Force database to use /tmp
os.environ['DATABASE_URL'] = 'sqlite:////tmp/data/mwk_forecasting.db'
os.makedirs('/tmp/data', exist_ok=True)

from db.database import init_db
init_db()
print('? Database ready at /tmp/data/mwk_forecasting.db')
"

echo "? Setup complete!"
