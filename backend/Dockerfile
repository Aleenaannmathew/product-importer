FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "app.main:app", "--bind", "0.0.0.0:$PORT", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker"]
