#!/bin/bash
# MyShop — Бэкап PostgreSQL
# Запуск: bash scripts/backup.sh
# Cron: 0 3 * * * /path/to/scripts/backup.sh

set -e

# Конфигурация
BACKUP_DIR="/backups/myshop"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30
S3_BUCKET="s3://myshop-backups"

# Docker compose
COMPOSE_FILE="docker-compose.prod.yml"
DB_CONTAINER="myshop-db-1"

# Создание директории
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# Бэкап PostgreSQL
docker exec "$DB_CONTAINER" pg_dump -U myshop myshop | gzip > "$BACKUP_DIR/myshop_$DATE.sql.gz"

# Проверка размера
SIZE=$(du -h "$BACKUP_DIR/myshop_$DATE.sql.gz" | cut -f1)
echo "[$(date)] Backup created: myshop_$DATE.sql.gz ($SIZE)"

# Загрузка в S3 (если настроен AWS CLI)
if command -v aws &> /dev/null; then
    aws s3 cp "$BACKUP_DIR/myshop_$DATE.sql.gz" "$S3_BUCKET/myshop_$DATE.sql.gz"
    echo "[$(date)] Uploaded to S3: $S3_BUCKET/myshop_$DATE.sql.gz"
fi

# Удаление старых бэкапов
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "[$(date)] Cleaned backups older than $RETENTION_DAYS days"

# Проверка последних бэкапов
echo "[$(date)] Recent backups:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -5

echo "[$(date)] Backup complete!"
