#!/bin/bash
# MyShop — Восстановление PostgreSQL из бэкапа
# Запуск: bash scripts/restore.sh /backups/myshop/myshop_20260101_030000.sql.gz

set -e

BACKUP_FILE=${1:-""}
DB_CONTAINER="myshop-db-1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /backups/myshop/*.sql.gz 2>/dev/null | tail -10
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: File not found: $BACKUP_FILE"
    exit 1
fi

echo "=== MyShop Database Restore ==="
echo "Backup: $BACKUP_FILE"
echo ""

read -p "This will OVERWRITE the current database. Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "[$(date)] Stopping backend..."
docker compose -f docker-compose.prod.yml stop backend celery-worker celery-beat

echo "[$(date)] Dropping and recreating database..."
docker exec "$DB_CONTAINER" psql -U myshop -d postgres -c "DROP DATABASE myshop;"
docker exec "$DB_CONTAINER" psql -U myshop -d postgres -c "CREATE DATABASE myshop;"

echo "[$(date)] Restoring from backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U myshop -d myshop

echo "[$(date)] Starting backend..."
docker compose -f docker-compose.prod.yml up -d backend celery-worker celery-beat

echo "[$(date)] Restore complete!"
