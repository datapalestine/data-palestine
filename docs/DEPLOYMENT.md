# Deployment Guide

Data Palestine runs on a DigitalOcean Droplet with Docker, Caddy (HTTPS), and Cloudflare DNS.

## Server

- DigitalOcean Droplet: 2GB RAM, 1 vCPU, Ubuntu 24.04
- IP: 64.225.65.231
- Domain: datapalestine.org (Cloudflare DNS)

## First-time Setup

### 1. Server preparation

```bash
ssh root@64.225.65.231

# Run server setup (swap, Docker, firewall)
bash scripts/setup_server.sh
```

### 2. Clone the repo

```bash
git clone https://github.com/datapalestine/data-palestine.git /root/data-palestine
```

### 3. Upload data files

From your local machine:

```bash
scp -r data/raw/ root@64.225.65.231:/root/data/raw/
```

The server expects data at `/root/data/raw/pcbs_csv/`, `/root/data/raw/pcbs_xlsx/`, etc.

### 4. Configure environment

```bash
cd /root/data-palestine
cp .env.production.example .env.production

# Generate strong passwords
PASS=$(openssl rand -hex 24)
SECRET=$(openssl rand -hex 32)

# Edit .env.production - replace CHANGE_ME values
sed -i "s/CHANGE_ME_STRONG_PASSWORD/$PASS/g" .env.production
sed -i "s/CHANGE_ME_STRONG_SECRET/$SECRET/g" .env.production
```

### 5. Build and start

```bash
docker compose -f docker/docker-compose.prod.yml --env-file .env.production up -d --build
```

This starts: PostgreSQL, API, frontend, and Caddy. Caddy handles HTTPS certificates automatically.

### 6. Initialize the database

```bash
docker exec datapalestine-api bash scripts/init_production.sh
```

This runs all pipelines (World Bank, PCBS CSVs, Tech for Palestine, XLSX files) and cleanup scripts. Takes 10-20 minutes. Safe to run multiple times.

### 7. Verify

```bash
curl https://datapalestine.org/api/v1/datasets?per_page=1
curl https://datapalestine.org/health
```

## DNS Setup (Cloudflare)

1. Add A record: `datapalestine.org` -> `64.225.65.231` (proxied)
2. Add A record: `www` -> `64.225.65.231` (proxied)
3. SSL/TLS mode: Full (Strict)
4. Enable "Always Use HTTPS"

## Updating

On push to `main`, GitHub Actions deploys automatically via SSH. Manual deploy:

```bash
ssh root@64.225.65.231
cd /root/data-palestine
git pull origin main
docker compose -f docker/docker-compose.prod.yml --env-file .env.production up --build -d
```

## Database Backups

```bash
# Manual backup
docker exec datapalestine-db pg_dump -U datapalestine datapalestine | gzip > backup_$(date +%Y%m%d).sql.gz

# Automated daily backup (add to crontab)
0 3 * * * docker exec datapalestine-db pg_dump -U datapalestine datapalestine | gzip > /root/backups/db_$(date +\%Y\%m\%d).sql.gz
```

## Logs

```bash
# All services
docker compose -f docker/docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker/docker-compose.prod.yml logs -f api
docker compose -f docker/docker-compose.prod.yml logs -f web
docker compose -f docker/docker-compose.prod.yml logs -f caddy
```

## Memory notes (2GB server)

- PostgreSQL: shared_buffers=256MB, max_connections=20
- Uvicorn: 1 worker
- Next.js: standalone mode (minimal footprint)
- 2GB swap file for safety
- No Redis, Meilisearch, or MinIO in production (not needed yet)

## Scaling

If traffic grows beyond what 2GB handles:

1. Upgrade to 4GB Droplet (vertical scaling)
2. Add Redis for API response caching
3. Add Meilisearch for full-text search
4. Move PostgreSQL to DigitalOcean Managed Database
