# Решение проблем MyShop

## Проблемы с запуском

### Docker не запускается

```bash
# Проверьте статус Docker
sudo systemctl status docker

# Запустите Docker
sudo systemctl start docker

# Если не помогло, перезагрузите
sudo reboot
```

### Порт уже занят

```bash
# Найдите процесс на порту 80
sudo lsof -i :80

# Остановите его
sudo kill <PID>
```

### Ошибка "No space left on device"

```bash
# Проверьте место на диске
df -h

# Очистите Docker
docker system prune -a

# Удалите старые логи
sudo journalctl --vacuum-size=100M
```

## Проблемы с базой данных

### Ошибка подключения

```bash
# Проверьте статус PostgreSQL
docker compose -f docker-compose.prod.yml ps db

# Посмотрите логи
docker compose -f docker-compose.prod.yml logs db

# Перезапустите
docker compose -f docker-compose.prod.yml restart db
```

### База повреждена

```bash
# Восстановите из бэкапа
bash scripts/restore.sh /backups/myshop/myshop_LATEST.sql.gz
```

## Проблемы с SSL

### Сертификат не работает

```bash
# Проверьте сертификат
sudo certbot certificates

# Переустановите
sudo certbot renew --force-renewal

# Перезапустите Nginx
sudo systemctl restart nginx
```

### Mixed Content ошибка

Убедитесь, что все ссылки используют HTTPS:
- В админке
- В изображениях товаров
- В CORS настройках

## Проблемы с авторизацией

### "Invalid token"

1. Токен мог истечь (30 минут для access token)
2. Обновите токен через `/refresh`
3. Если не помогло, войдите заново

### "User not found"

Пользователь был удалён из базы. Зарегистрируйтесь заново.

## Проблемы с производительностью

### Медленная загрузка

```bash
# Проверьте использование ресурсов
docker stats

# Увеличьте лимиты в docker-compose.prod.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

### Медленные запросы к БД

```bash
# Включите логирование SQL
# В .env добавьте:
DEBUG=true

# Посмотрите логи
docker compose -f docker-compose.prod.yml logs backend | grep "SELECT"
```

## Проблемы с файлами

### Изображения не загружаются

```bash
# Проверьте права на папку uploads
ls -la uploads/

# Исправьте права
sudo chown -R 1000:1000 uploads/
sudo chmod -R 755 uploads/
```

### Файл слишком большой

Максимальный размер загрузки: 5 МБ.

## Сброс к начальному состоянию

```bash
# Остановите всё
docker compose -f docker-compose.prod.yml down

# Удалите данные
docker volume rm myshop-backend_pgdata

# Запустите заново
docker compose -f docker-compose.prod.yml up -d
```

## Получение帮助ы

Если проблема не решена:

1. Проверьте логи: `docker compose -f docker-compose.prod.yml logs`
2. Проверьте статус: `docker compose -f docker-compose.prod.yml ps`
3. Напишите в поддержку с выводом команд выше
