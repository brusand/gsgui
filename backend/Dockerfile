# Dockerfile pour GSGUI Backend
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY app/ ./app/

# Créer un utilisateur non-root
RUN useradd -m -u 1000 gsgui && chown -R gsgui:gsgui /app
USER gsgui

# Exposer le port
EXPOSE 8000

# Variables d'environnement par défaut
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=10)"

# Commande de démarrage
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]