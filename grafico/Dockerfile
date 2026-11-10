# Grafico AI UltraPixel — servizio web su Render (Docker).
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund --silent
COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD gunicorn --chdir server app:app --workers 1 --threads 8 --timeout 600 --bind 0.0.0.0:${PORT:-8080}
