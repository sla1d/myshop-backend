#!/bin/bash
# MyShop — Первичная настройка сервера
# Запуск: bash scripts/setup-server.sh yourdomain.com

set -e

DOMAIN=${1:-yourdomain.com}
EMAIL=${2:-admin@${DOMAIN}}

echo "=== MyShop Server Setup ==="
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"

# 1. Обновление системы
echo "--- Updating system ---"
sudo apt update && sudo apt upgrade -y

# 2. Установка Docker
echo "--- Installing Docker ---"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
fi

# 3. Установка Docker Compose
echo "--- Installing Docker Compose ---"
if ! command -v docker compose &> /dev/null; then
    sudo apt install docker-compose-plugin -y
fi

# 4. Установка Certbot
echo "--- Installing Certbot ---"
sudo apt install certbot -y

# 5. Настройка SSL
echo "--- Setting up SSL ---"
sudo certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m $EMAIL

# 6. Создание .env
echo "--- Creating .env ---"
if [ ! -f .env ]; then
    SECRET_KEY=$(openssl rand -base64 64)
    cat > .env << EOF
SECRET_KEY=$SECRET_KEY
DATABASE_URL=postgresql+asyncpg://myshop:$(openssl rand -hex 16)@db:5432/myshop
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
HOST=0.0.0.0
PORT=8000
DEBUG=false
CORS_ORIGINS=["https://$DOMAIN"]
EOF
    echo ".env created with random SECRET_KEY"
fi

# 7. Настройка Nginx
echo "--- Configuring Nginx ---"
sed -i "s/yourdomain.com/$DOMAIN/g" deploy/nginx/default.conf

# 8. Запуск
echo "--- Starting services ---"
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "=== Setup Complete ==="
echo "Site: https://$DOMAIN"
echo "Admin: https://$DOMAIN/docs"
echo "Login: admin / admin123 (CHANGE THIS!)"
