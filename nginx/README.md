# nginx reverse proxy for contract_review_tool (prod profile)

This directory is mounted by the `nginx` service in docker-compose.yml (prod profile only).

## Files
- `nginx.conf` — the main server config with proxy rules.
- `certs/` — place your TLS material here (see below).

## TLS / HTTPS (required for Polar production webhooks)

Polar requires a publicly reachable **HTTPS** URL for webhooks when `POLAR_SERVER=production`.

1. On the VPS obtain a cert (while the nginx container is not yet using port 80, or use DNS challenge):
   ```bash
   # stop nginx temporarily if it is holding port 80
   docker compose --profile prod stop nginx

   certbot certonly --standalone -d yourdomain.com --agree-tos -m you@example.com
   # or for DNS:
   # certbot certonly --manual --preferred-challenges dns -d yourdomain.com
   ```

2. Copy the certs into this directory:
   ```bash
   mkdir -p certs
   cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem certs/
   cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   certs/
   chmod 600 certs/*
   ```

3. Edit `nginx/nginx.conf` and enable the 443 ssl server block (uncomment it and make sure the paths match `/etc/nginx/certs/...` — the volume mount makes the host certs/ visible at that path inside the container).

4. Restart:
   ```bash
   docker compose --profile prod restart nginx
   ```

5. Test:
   ```bash
   curl -I https://yourdomain.com
   curl -I https://yourdomain.com/health
   ```

6. In the Polar dashboard (production org) register / update the webhook to exactly:
   ```
   https://yourdomain.com/api/webhook/polar
   ```
   Copy the new secret into your server's `.env` as `POLAR_WEBHOOK_SECRET`, then:
   ```bash
   docker compose --profile prod up -d --build frontend
   ```

For quick http-only testing (before you have certs) you can leave the port-80 server block active and use a prod-like domain with a tunnel or just test the Polar sandbox flow.

## Other notes
- The config forwards `Host`, `X-Real-IP`, `X-Forwarded-*` so the Next.js and FastAPI apps see the real client IP and scheme.
- You can increase `client_max_body_size` in the http {} or server {} block if you need to support very large PDF uploads.
- Add security headers, rate limiting, etc. as needed.
- If you later prefer Caddy (auto TLS via Let's Encrypt with almost zero config), replace the nginx service in docker-compose.yml with a caddy one + a root `Caddyfile`; only compose + one new file change.

After certs + webhook registration your public URL (`https://yourdomain.com`) is ready for real €2 Polar one-time purchases.