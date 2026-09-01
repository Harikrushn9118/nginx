# NGINX Load Balancer & Reverse Proxy Demo

This project is a production-ready web architecture setup. It uses NGINX as a reverse proxy and load balancer to route traffic to 4 different Python (FastAPI) microservices. Everything is backed by a real PostgreSQL database and secured with HTTPS/SSL.

## The Architecture

```text
User → NGINX (Port 443 / HTTPS)
          │
          ├── /auth/*     → Auth Service
          ├── /post/*     → Post Service
          ├── /user/*     → User Service
          └── /search/*   → Search Service
```

All 4 microservices connect to a single **PostgreSQL** database so that data is perfectly shared across the whole system.

## Key Features

1. **Automated CI/CD:** We have a GitHub Actions pipeline set up. Whenever code is pushed to `main`, a robot automatically builds the Docker images for all 4 services, tests them by running a health check, and then pushes them to GitHub Container Registry (`ghcr.io`).
2. **SSL / HTTPS Termination:** NGINX handles the SSL certificates. If someone tries to connect on regular HTTP (port 80), NGINX immediately redirects them to a secure HTTPS connection (port 443).
3. **PostgreSQL Database:** We are using a real database instead of saving files to the disk, which means the app can scale up without data issues.
4. **Rate Limiting:** NGINX limits how fast people can make requests. This stops hackers from trying to brute-force passwords.
5. **Security Headers & Blocking:** NGINX adds security headers to protect the frontend, and it completely blocks anyone trying to snoop on hidden folders like `.env` or `.git`.

## Tech Stack
- **Proxy:** NGINX
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **CI/CD:** GitHub Actions
- **Deployment:** Docker Compose

## Setup Instructions

If you want to run this yourself, make sure you have Docker and Docker Compose installed.

1. Start all the containers:
```bash
docker-compose up --build -d
```

2. Open your browser and go to:
```
http://localhost
```
*Notice how NGINX automatically redirects you to `https://localhost`!* 

*(Note: Because we are using local self-signed SSL certificates for testing, your browser will warn you that the connection isn't private. Just click "Advanced" → "Proceed to localhost" to see the app).*

## Viewing the Logs

If you want to see what is happening behind the scenes, you can easily check the logs for any service:
```bash
docker logs auth-service
docker logs nginx-proxy
```
