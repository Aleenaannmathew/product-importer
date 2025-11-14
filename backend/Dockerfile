# -----------------------------
# Base Image
# -----------------------------
FROM python:3.12-slim

# -----------------------------
# Environment
# -----------------------------
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -----------------------------
# System Dependencies
# -----------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && apt-get clean

# -----------------------------
# Install Python Dependencies
# -----------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Copy App Code
# -----------------------------
COPY . .

# -----------------------------
# Expose Port
# -----------------------------
EXPOSE 8000

# -----------------------------
# Default Command (Uvicorn/Gunicorn)
# -----------------------------
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "app.main:app", "--bind", "0.0.0.0:8000"]
