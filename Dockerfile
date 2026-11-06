# Base ligera oficial de Python
FROM python:3.11-slim

# Evitar que Python escriba archivos .pyc y forzar salida inmediata por stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=web.app \
    FLASK_ENV=production

# Instalar dependencias de sistema mínimas si fueran necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar e instalar dependencias primero para aprovechar la caché de capas de Docker
COPY requirements-server.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . /app

# Crear directorio para persistencia de base de datos SQLite y datos
RUN mkdir -p /app/data

# Exponer el puerto por defecto de Flask
EXPOSE 5000

# Script de arranque: inicializa / migra la base de datos e inicia el servidor web
CMD ["sh", "-c", "python -c 'from database.connection import init_db; init_db()' && python -m flask run --host=0.0.0.0 --port=5000"]
