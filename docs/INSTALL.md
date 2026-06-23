# Установка MyShop — Пошаговая инструкция

## Требования

- Linux сервер (Ubuntu 22.04+)
- Docker и Docker Compose
- Доменное имя, направленное на сервер
- 2GB RAM, 20GB SSD

## Быстрая установка (5 минут)

### 1. Подключитесь к серверу

```bash
ssh root@your-server-ip
```

### 2. Скачайте проект

```bash
git clone https://github.com/sla1d/myshop-backend.git
cd myshop-backend
```

### 3. Настройте окружение

```bash
# Создайте .env файл
cp .env.example .env

# Сгенерируйте SECRET_KEY
SECRET_KEY=$(openssl rand -base64 64)
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env

# Укажите ваш домен
sed -i "s/yourdomain.com/your-domain.com/" .env
```

### 4. Запустите

```bash
# Продакшен
docker compose -f docker-compose.prod.yml up -d

# Или локально
docker compose up -d
```

### 5. Настройте SSL

```bash
# Установите Certbot
sudo apt install certbot -y

# Получите сертификат
sudo certbot certonly --standalone -d your-domain.com

# Запустите автообновление
sudo systemctl enable certbot.timer
```

### 6. Проверьте

Откройте в браузере:
- Магазин: `https://your-domain.com`
- API Docs: `https://your-domain.com/docs`
- Admin: `https://your-domain.com` (войдите как admin)

## Логин по умолчанию

| Пользователь | Пароль | Роль |
|---|---|---|
| `admin` | `admin123` | admin |

**ВАЖНО:** Сразу смените пароль администратора!

## Настройка бэкапов

```bash
# Добавьте в crontab
crontab -e

# Бэкап каждый день в 3:00
0 3 * * * /path/to/myshop-backend/scripts/backup.sh >> /var/log/myshop-backup.log 2>&1
```

## Настройка мониторинга

### UptimeRobot (бесплатно)

1. Зарегистрируйтесь на [uptimerobot.com](https://uptimerobot.com)
2. Добавьте мониторинг:
   - URL: `https://your-domain.com/health`
   - Интервал: 5 минут
3. Настройте оповещения в Telegram/Email

## Обновление

```bash
cd myshop-backend
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Решение проблем

### Сервер не отвечает

```bash
# Проверьте статус
docker compose -f docker-compose.prod.yml ps

# Посмотрите логи
docker compose -f docker-compose.prod.yml logs backend
```

### Ошибка SSL

```bash
# Переустановите сертификат
sudo certbot renew --force-renewal
sudo systemctl restart nginx
```

### База данных

```bash
# Восстановление из бэкапа
bash scripts/restore.sh /backups/myshop/myshop_20260101_030000.sql.gz
```

## Поддержка

- Email: support@myshop.com
- Telegram: @myshop_support
