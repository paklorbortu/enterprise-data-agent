# syntax=docker/dockerfile:1
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY frontend/ ./frontend/

# gdocs-mcp is at the project root — copy it to /app/gdocs-mcp
# BASE_DIR in settings.py resolves to /app, so /app/gdocs-mcp is correct
COPY gdocs-mcp/build/ ./gdocs-mcp/build/
COPY gdocs-mcp/package.json ./gdocs-mcp/package.json
COPY gdocs-mcp/package-lock.json ./gdocs-mcp/package-lock.json
COPY gdocs-mcp/credentials.json ./gdocs-mcp/credentials.json
RUN cd gdocs-mcp && npm install --omit=dev

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV GDOCS_CREDENTIALS_PATH=/app/gdocs-mcp/credentials.json

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.api.server:app --host 0.0.0.0 --port $PORT --workers 1 --timeout-keep-alive 300"]