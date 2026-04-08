FROM python:3.11-slim
WORKDIR /app
# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*
# Dependencias Python
COPY runtime/python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Código
COPY . .
# Directorio de datos
RUN mkdir -p data
EXPOSE 8787 8765
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8787/health || exit 1
CMD ["python", "runtime/python/main.py"]
