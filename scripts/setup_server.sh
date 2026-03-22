#!/bin/bash
set -e

echo "Data Palestine - Server Setup"
echo "=============================="

# Swap (for 2GB RAM servers)
if [ ! -f /swapfile ]; then
    echo "Creating 2GB swap file..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "Swap enabled."
else
    echo "Swap already exists."
fi

# Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    echo "Docker installed."
else
    echo "Docker already installed."
fi

# Firewall
echo "Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo ""
echo "Server setup complete."
echo "Next steps:"
echo "  1. Clone repo: git clone https://github.com/datapalestine/data-palestine.git /root/data-palestine"
echo "  2. Upload data: scp -r data/ root@<server>:/root/data/"
echo "  3. Create .env: cp .env.production.example .env.production"
echo "  4. Edit .env.production with strong passwords"
echo "  5. Build: cd /root/data-palestine && docker compose -f docker/docker-compose.prod.yml --env-file .env.production up -d --build"
echo "  6. Init DB: docker exec datapalestine-api bash scripts/init_production.sh"
