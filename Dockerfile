FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# La carpeta de archivos debe pertenecer al usuario sin privilegios que corre la API.
RUN useradd --create-home appuser && mkdir -p /app/storage && chown -R appuser:appuser /app/storage
USER appuser

EXPOSE 8000
# Aplica migraciones pendientes y levanta la API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
