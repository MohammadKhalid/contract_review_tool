# nginx reverse proxy (Contract Hero + VoiceAgents on one VPS)

## Routing

| Request | Target |
|---------|--------|
| `https://contract-hero.com/` … | Contract Hero frontend / backend (unchanged) |
| `https://contract-hero.com/docs` | Contract Hero Swagger |
| `https://contract-hero.com/v1-docs` | **VoiceAgents** Swagger |
| `https://contract-hero.com/v1/...` | **VoiceAgents** API |
| `http://SERVER_IP/v1-docs` | **VoiceAgents** Swagger |
| `http://SERVER_IP/v1/...` | **VoiceAgents** API |
| `http://SERVER_IP/va-health` | **VoiceAgents** health |

Frontend for ChatEcho is expected on **Vercel** (not this VPS).

## Files

- `nginx.conf` — server blocks (IP default + contract-hero.com)
- `proxy-locations.conf` — Contract Hero routes (original)
- `proxy-locations-voiceagents.conf` — `/v1`, `/v1-docs`, `/va-health`
- `certs/` — TLS for contract-hero.com (`fullchain.pem`, `privkey.pem`)

## Prerequisites

```bash
# Once on the VPS
docker network create edge
```

VoiceAgents must run with container name `voiceagents-api` on network `edge`
(see chatecho `VoiceAgents/docker-compose.yml`).

### “host not found in upstream voiceagents-api”

Fixed in config by using Docker DNS (`resolver 127.0.0.11`) + a variable
`proxy_pass` so nginx **starts even if VoiceAgents is down**. Those paths
return **502** until the API is healthy.

Still required for requests to work:

```bash
docker network create edge || true
cd /path/to/chatecho/VoiceAgents && docker compose up -d
# voiceagents-api must be on network edge:
docker network connect edge voiceagents-api  # only if not already via compose
docker network inspect edge
```

## TLS (Contract Hero — unchanged)

```bash
docker compose --profile prod stop nginx

certbot certonly --standalone -d contract-hero.com -d www.contract-hero.com \
  --agree-tos -m you@example.com

mkdir -p certs
cp /etc/letsencrypt/live/contract-hero.com/fullchain.pem certs/
cp /etc/letsencrypt/live/contract-hero.com/privkey.pem   certs/
chmod 600 certs/*

docker compose --profile prod up -d nginx
```

## Start order

```bash
docker network create edge || true

# VoiceAgents only (API + DB)
cd /path/to/chatecho/VoiceAgents
docker compose up -d --build

# Contract Hero + nginx
cd /path/to/contract_review_tool
docker compose --profile prod up -d --build
```

## Smoke tests

```bash
# Contract Hero
curl -I https://contract-hero.com
curl -I https://contract-hero.com/health
curl -I https://contract-hero.com/docs

# VoiceAgents via IP
curl -I http://SERVER_IP/v1-docs
curl -I http://SERVER_IP/va-health
curl -I http://SERVER_IP/v1/auth/signin   # expect 405 GET → method not allowed is fine

# VoiceAgents via domain (HTTPS — use this for Vercel)
curl -I https://contract-hero.com/v1-docs
curl -s https://contract-hero.com/va-health
```

## Vercel frontend env

```env
NEXT_PUBLIC_API_URL=https://contract-hero.com/v1
NEXTAUTH_URL=https://your-app.vercel.app
```

Use HTTPS + domain for the API from Vercel (browsers block mixed content if the site is HTTPS and API is bare `http://IP`).

## Polar webhook (Contract Hero)

```
https://contract-hero.com/api/webhook/polar
```
