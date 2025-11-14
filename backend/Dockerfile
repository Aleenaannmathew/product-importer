# ----------------------------------------
# Base Python Image
# ----------------------------------------
FROM python:3.12-slim

# Install system dependencies including supervisor
RUN apt-get update && apt-get install -y \
    supervisor \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Copy supervisor config
COPY supervisord.conf /app/supervisord.conf

# Expose port Render uses
EXPOSE 8000

# Start Supervisor: runs both Gunicorn + Celery worker
CMD ["supervisord", "-c", "/app/supervisord.conf"]
