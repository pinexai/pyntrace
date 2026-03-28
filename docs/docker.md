# Docker / Self-Hosting

pyntrace ships a production-ready Docker image for teams that want to self-host the dashboard without installing Python.

---

## Quick Start

```bash
git clone https://github.com/pinexai/pyntrace
cd pyntrace
docker compose up
```

The dashboard is now running at **http://localhost:7234**.

---

## docker-compose.yml

```yaml
services:
  pyntrace:
    build: .
    ports:
      - "7234:7234"
    volumes:
      - pyntrace_data:/data
    environment:
      PYNTRACE_DB_PATH: /data/pyntrace.db
      # Optional — enable API key authentication:
      # PYNTRACE_API_KEY: your-secret-key
      # Optional — LLM provider keys for running scans from the dashboard:
      # OPENAI_API_KEY: sk-...
      # ANTHROPIC_API_KEY: sk-ant-...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7234/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  pyntrace_data:
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYNTRACE_DB_PATH` | `~/.pyntrace/data.db` | SQLite database path |
| `PYNTRACE_API_KEY` | — | Enable token-based API authentication |
| `PYNTRACE_HOST` | `127.0.0.1` | Bind address (`0.0.0.0` for Docker) |
| `PYNTRACE_HTPASSWD_FILE` | — | Path to htpasswd file for HTTP Basic Auth |
| `PYNTRACE_STRICT_SECRETS` | — | Set to `1` to raise `RuntimeError` instead of warning when plaintext secret storage is attempted (requires `PYNTRACE_SECRETS_KEY` to be configured) |
| `OPENAI_API_KEY` | — | For scanning from the dashboard |
| `ANTHROPIC_API_KEY` | — | For Anthropic models |
| `AZURE_OPENAI_ENDPOINT` | — | For Azure OpenAI |
| `AZURE_OPENAI_API_KEY` | — | For Azure OpenAI |
| `GROQ_API_KEY` | — | For Groq |
| `MISTRAL_API_KEY` | — | For Mistral |
| `COHERE_API_KEY` | — | For Cohere |
| `TOGETHER_API_KEY` | — | For Together AI |

---

## Using a Pre-built Image

Once published to Docker Hub:

```bash
docker run -d \
  -p 7234:7234 \
  -v pyntrace_data:/data \
  -e PYNTRACE_DB_PATH=/data/pyntrace.db \
  -e OPENAI_API_KEY=sk-... \
  pinexai/pyntrace:0.6.0
```

---

## Health Check

The container exposes `GET /health`:

```bash
curl http://localhost:7234/health
# {"status":"ok","version":"0.6.0","db":"ok"}
```

Use this as your load-balancer or Kubernetes readiness probe:

```yaml
# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health
    port: 7234
  initialDelaySeconds: 5
  periodSeconds: 10
```

---

## Securing the Dashboard

### API Key Authentication

```bash
docker run ... -e PYNTRACE_API_KEY=my-secret-token pinexai/pyntrace:0.6.0
```

All API requests must then include:
```
Authorization: Bearer my-secret-token
```
Or pass `?token=my-secret-token` for WebSocket connections.

### Reverse Proxy (recommended for production)

Put nginx or Caddy in front to handle TLS:

```nginx
server {
    listen 443 ssl;
    server_name pyntrace.example.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://localhost:7234;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";  # for WebSocket
    }
}
```

---

## Persisting Data

The database is stored at `PYNTRACE_DB_PATH` (default `/data/pyntrace.db` in the container). Mount a named volume or bind-mount a host directory to persist data across container restarts:

```bash
# Named volume (recommended)
docker run -v pyntrace_data:/data ...

# Bind mount (for easy backup)
docker run -v /opt/pyntrace-data:/data ...
```

---

## Building from Source

```bash
git clone https://github.com/pinexai/pyntrace
cd pyntrace

# Build
docker build -t pyntrace:local .

# Run
docker run -p 7234:7234 -v pyntrace_data:/data pyntrace:local
```

---

## CLI without Docker

If you prefer running the server directly:

```bash
pip install "pyntrace[server]"
pyntrace serve --port 7234 --host 0.0.0.0
```

Or with SSL:

```bash
pyntrace serve --ssl-certfile cert.pem --ssl-keyfile key.pem
```
