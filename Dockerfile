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

COPY gdocs-mcp/build/ ./gdocs-mcp/build/
COPY gdocs-mcp/package.json ./gdocs-mcp/package.json
COPY gdocs-mcp/package-lock.json ./gdocs-mcp/package-lock.json
COPY gdocs-mcp/credentials.json ./gdocs-mcp/credentials.json
RUN cd gdocs-mcp && npm install --omit=dev

RUN mkdir -p /app/gdocs-mcp-token && chmod 777 /app/gdocs-mcp-token

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV GDOCS_TOKEN_PATH=/app/gdocs-mcp-token/token.json
ENV GDOCS_CREDENTIALS_PATH=/app/gdocs-mcp/credentials.json

EXPOSE 8080

CMD ["sh", "-c", "\
    if [ -f /app/gdocs-mcp/token.json ]; then \
    cat /app/gdocs-mcp/token.json > /app/gdocs-mcp-token/token.json && \
    echo 'Token copied to writable location.'; \
    fi && \
    uvicorn app.api.server:app --host 0.0.0.0 --port $PORT --workers 1 --timeout-keep-alive 300"]