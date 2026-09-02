# Reverse Proxy Configuration

The AI News Digest application is designed to run behind a reverse proxy that handles TLS termination, HTTP to HTTPS redirects, and external request routing.

## Supported Reverse Proxies

- **nginx** (recommended for simplicity)
- **Traefik** (recommended for dynamic environments)
- **Caddy** (automatic HTTPS)
- **AWS ALB / NLB** (cloud load balancers)

This document provides configuration examples for nginx and Traefik. The reverse proxy is **external to this repository** and is the operator's responsibility.

---

## nginx Configuration

### Requirements

- nginx 1.18+
- TLS certificate (e.g., Let's Encrypt)
- DNS record pointing to the host

### Example `ai-news-digest.conf`

```nginx
upstream ai_news_digest_frontend {
    server 127.0.0.1:3000;
}

upstream ai_news_digest_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name news.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name news.example.com;

    # TLS configuration
    ssl_certificate /etc/letsencrypt/live/news.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/news.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header X-Request-ID $request_id always;

    # Client IP forwarding
    real_ip_header X-Real-IP;
    real_ip_recursive on;
    set_real_ip_from 10.0.0.0/8;
    set_real_ip_from 172.16.0.0/12;
    set_real_ip_from 192.168.0.0/16;

    # Health checks (do not proxy to upstream)
    location = /health/live {
        access_log off;
        proxy_pass http://ai_news_digest_api/health/live;
    }

    location = /health/ready {
        access_log off;
        proxy_pass http://ai_news_digest_api/health/ready;
    }

    location = /metrics/health {
        access_log off;
        proxy_pass http://ai_news_digest_api/metrics/health;
    }

    # API routes
    location /api/ {
        proxy_pass http://ai_news_digest_api/api/;
    }

    # Docs (disable in production via app config)
    location /docs {
        return 404;
    }

    location /redoc {
        return 404;
    }

    # Metrics (admin-only, but restrict access further if needed)
    location /metrics/ {
        proxy_pass http://ai_news_digest_api/metrics/;
        # Optional: restrict to internal IPs
        # allow 10.0.0.0/8;
        # allow 172.16.0.0/12;
        # allow 192.168.0.0/16;
        # deny all;
    }

    # Frontend SPA
    location / {
        proxy_pass http://ai_news_digest_frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Traefik Configuration

### Static Configuration (`traefik.yml`)

```yaml
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https

  websecure:
    address: ":443"

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /etc/traefik/acme.json
      httpChallenge:
        entryPoint: web

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
```

### Dynamic Configuration (Docker labels)

Add these labels to `docker-compose.prod.yml` under the `web` and `frontend` services:

```yaml
services:
  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.ai-news-digest-frontend.entrypoints=websecure"
      - "traefik.http.routers.ai-news-digest-frontend.rule=Host(`news.example.com`)"
      - "traefik.http.routers.ai-news-digest-frontend.tls=true"
      - "traefik.http.routers.ai-news-digest-frontend.tls.certresolver=letsencrypt"
      - "traefik.http.services.ai-news-digest-frontend.loadbalancer.server.port=8080"
      - "traefik.http.routers.ai-news-digest-frontend.priority=1"

  web:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.ai-news-digest-api.entrypoints=websecure"
      - "traefik.http.routers.ai-news-digest-api.rule=Host(`news.example.com`) && PathPrefix(`/api/`)"
      - "traefik.http.routers.ai-news-digest-api.tls=true"
      - "traefik.http.routers.ai-news-digest-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.ai-news-digest-api.loadbalancer.server.port=8000"
      - "traefik.http.routers.ai-news-digest-api.priority=2"
```

---

## Health Endpoint Accessibility

The reverse proxy must allow unauthenticated access to:

- `GET /health/live`
- `GET /health/ready`
- `GET /metrics/health`

All other endpoints require appropriate authentication.

---

## Important Notes

- **Do not expose PostgreSQL or Redis** through the reverse proxy.
- **TLS termination** happens at the reverse proxy. The application itself does not handle TLS.
- **Client IP headers**: Ensure `X-Forwarded-For` and `X-Real-IP` are forwarded correctly for rate limiting and logging.
- **Request timeouts**: Set appropriate proxy timeouts (recommended: 30s read/send, 10s connect).
- **WebSocket**: Not currently used by the application, but if added in the future, ensure `proxy_http_version 1.1` and `proxy_set_header Upgrade $http_upgrade` are configured.
