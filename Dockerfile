FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source et des fichiers CSV
COPY . .

# Exposition du port par défaut
EXPOSE 8000

# Lancement du serveur uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]