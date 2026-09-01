# NGINX Load Balancer & Reverse Proxy Demo

This project demonstrates a production-ready web architecture using NGINX as a reverse proxy, load balancer, and rate limiter. It routes traffic to 9 Python (FastAPI) microservices, all backed by a real PostgreSQL database, and secures traffic with HTTPS/SSL.

## The Architecture

```text
User → NGINX (Port 443 / HTTPS)
          │
          ├── /auth/*     → Auth Service (3 instances)
          │                 (Uses ip_hash — sticky sessions)
          │
          └── /api/*      → Backend Service (6 instances)
                            (Uses least_conn — sends to least busy server)
```

All 9 Python containers connect to a single **PostgreSQL** database container to ensure state is shared perfectly across the cluster.

## Key Features Configured

1. **SSL / HTTPS Termination:** NGINX handles the SSL certificates on port 443. All HTTP traffic on port 80 is automatically redirected to HTTPS (301 redirect).
2. **PostgreSQL Database:** Replaced file-based storage with a robust database for scalable, concurrent reads and writes.
3. **Rate Limiting:** 
   - `/auth/` is strictly limited (5 requests/sec) to prevent brute force attacks.
   - `/api/` is more relaxed (10 requests/sec).
4. **Load Balancing:** NGINX distributes traffic across 9 containers using two different algorithms (`least_conn` and `ip_hash`).
5. **Security Headers:** Adds `X-Frame-Options`, `X-XSS-Protection`, and `X-Content-Type-Options` to protect the frontend.
6. **Hidden File Blocking:** NGINX immediately blocks requests to `.env` or `.git` folders.

## Tech Stack
- **Proxy:** NGINX
- **Backend:** FastAPI (Python) + asyncpg
- **Frontend:** Vanilla HTML/JS/CSS
- **Database:** PostgreSQL
- **Security:** OpenSSL (Self-signed certs for local testing)
- **Deployment:** Docker Compose

## Setup Instructions

If you want to run this yourself, make sure you have Docker and Docker Compose installed.

1. Start all 11 containers (NGINX + 9 Backends + PostgreSQL):
```bash
docker-compose up --build -d
```

2. Open your browser and go to:
```
http://localhost
```
*Notice how NGINX automatically redirects you to `https://localhost`!* 

*(Note: Because we generated a local self-signed SSL certificate, your browser will show a security warning. Click "Advanced" → "Proceed to localhost" to view the app).*

## Viewing the Load Balancer in Action
If you want to see which specific container handled your request, you can check the logs for that container:
```bash
docker logs auth-1
docker logs backend-3
```
You can also watch the NGINX logs to see the exact response times and upstream servers:
```bash
docker logs nginx-proxy
```
