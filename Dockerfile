FROM python:3.12-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --default-timeout=100 --retries 5 --no-cache-dir -r requirements.txt

COPY . .

# Используем MongoDB - инициализация происходит через Beanie ODM при старте
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "4200"]