# MyShop — SaaS платформа интернет-магазинов

Готовая платформа для запуска интернет-магазинов по подписке. Multi-tenant архитектура, оплата ЮKassa, доставка СДЭК, аналитика, RBAC.

## Стек

| Компонент | Технология |
|---|---|
| Framework | FastAPI 0.104+ |
| ORM | SQLAlchemy 2.0 (async) |
| БД | PostgreSQL 18 |
| Авторизация | JWT (access + refresh), bcrypt, 2FA TOTP |
| RBAC | 28 разрешений, 8 системных ролей |
| Оплата | ЮKassa (IP фильтрация, идемпотентность) |
| Кэширование | Redis |
| Очереди | RabbitMQ |
| Фоновые задачи | Celery |
| WebSocket | Уведомления в реальном времени |
| Тестирование | pytest + pytest-asyncio (51 тест) |
| CI/CD | GitHub Actions |
| Контейнеризация | Docker Compose |

## Быстрый старт

```bash
# 1. Клонировать
git clone https://github.com/sla1d/myshop-backend.git
cd myshop-backend

# 2. Виртуальное окружение
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. PostgreSQL
# Создать БД myshop, настроить DATABASE_URL в backend/.env

# 4. Запуск
cd backend
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Приложение: http://localhost:8000
- Landing: http://localhost:8000/landing/
- Swagger: http://localhost:8000/docs
- Здоровье: http://localhost:8000/health

## Docker (продакшен)

```bash
# Настройка .env
cp .env.example .env
# Заполнить SECRET_KEY, POSTGRES_PASSWORD, YOOKASSA ключи

# Запуск
docker compose -f docker-compose.prod.yml up -d
```

Сервисы: nginx, backend, PostgreSQL, Redis, RabbitMQ, MinIO, Celery worker + beat, Certbot.

## SaaS модель

| Тариф | Цена | Товары | Заказы | Фичи |
|---|---|---|---|---|
| Starter | 990₽/мес | 100 | 1,000 | Каталог, корзина, аналитика |
| Business | 2,990₽/мес | 1,000 | 10,000 | + Промокоды, отзывы, рассылки |
| Pro | 9,990₽/мес | ∞ | ∞ | + API, кастомный домен, белый-label |

## Клиентский flow

```
Landing → "Создать магазин" → Регистрация → Onboarding → Dashboard
```

- `/landing/` — лендинг с тарифами и формой регистрации
- `/register-store` — авто-создание tenant + user + подписка
- `/onboarding.html` — мастер настройки (тема, описание, фичи)
- `/dashboard.html` — личный кабинет продавца

## API Endpoints

### Авторизация
| Метод | Путь | Описание |
|---|---|---|
| POST | `/register` | Регистрация пользователя |
| POST | `/register-store` | Регистрация + создание магазина |
| POST | `/login` | Вход → access + refresh токены |
| POST | `/login/2fa` | Вход с 2FA |
| POST | `/refresh` | Обновление токена |
| POST | `/logout` | Выход |

### Товары
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/products` | Каталог (search, category, brand, price, rating, sort) |
| GET | `/api/products/{id}` | Товар по ID |
| GET | `/api/products/categories` | Категории |
| GET | `/api/products/brands` | Бренды |
| GET | `/api/products/recommendations` | Рекомендации |

### Корзина (🔒)
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/cart` | Корзина |
| POST | `/api/cart/add` | Добавить товар |
| PUT | `/api/cart/item/{id}` | Изменить количество |
| DELETE | `/api/cart/remove` | Удалить товар |

### Заказы (🔒)
| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/order` | Создать заказ |
| GET | `/api/profile/orders` | История заказов |
| GET | `/api/tracking/{id}` | Трекинг заказа |

### Платежи (🔒)
| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/payments/create` | Создать платёж ЮKassa |
| GET | `/api/payments/status/{id}` | Статус оплаты |
| POST | `/api/payments/webhook` | Webhook ЮKassa (IP фильтрация) |

### Избранное (🔒)
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/wishlist` | Список |
| POST | `/api/wishlist` | Добавить |
| DELETE | `/api/wishlist/{id}` | Удалить |

### Отзывы
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/reviews/product/{id}` | Отзывы товара |
| POST | `/api/reviews` | Создать отзыв (🔒) |

### Промокоды
| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/promos/validate` | Проверить промокод |

### Профиль (🔒)
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/profile` | Данные |
| PATCH | `/api/profile` | Обновить |
| POST | `/api/profile/change-password` | Сменить пароль |

### Админ (🔒 RBAC)
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/admin/stats` | Статистика |
| GET | `/api/admin/users` | Пользователи |
| GET | `/api/admin/products` | Товары |
| POST | `/api/admin/products` | Создать товар |
| GET | `/api/admin/orders` | Заказы |
| PATCH | `/api/admin/orders/{id}/status` | Статус заказа |
| GET | `/api/admin/promos` | Промокоды |

### Настройки магазина
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/store/settings` | Настройки темы, названия |
| PUT | `/api/store/settings` | Обновить настройки |
| POST | `/api/store/generate-store` | Генерация магазина (admin) |

### Личный кабинет
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/billing/subscription` | Подписка |
| POST | `/api/billing/subscribe` | Оформить подписку |

## Безопасность

- JWT с ротацией refresh токенов
- 5 попыток входа → блокировка 15 мин
- RBAC: 28 разрешений, 8 ролей (owner, admin, manager, support, viewer, seller, content, custom)
- IP фильтрация webhook ЮKassa
- Идемпотентность платежей
- HTTPS + security headers
- Rate limiting

## Тестовые данные

| Пользователь | Пароль | Роль |
|---|---|---|
| `admin` | `admin123` | admin (owner) |

Промокоды: `SALE10` (10%), `WELCOME20` (20%), `SUMMER15` (15%).

## Тесты

```bash
cd backend
PYTHONPATH=. pytest tests/ -v
```

51 тест: auth, products, cart, orders, reviews, wishlist, promos, admin.

## Структура проекта

```
backend/
├── app/
│   ├── core/           # config, security, cache, rabbitmq, celery, logging
│   ├── database/       # engine, session, base
│   ├── models/         # SQLAlchemy ORM (30+ таблиц)
│   ├── schemas/        # Pydantic
│   ├── routers/        # API endpoints (30+ роутеров)
│   ├── services/       # Business logic
│   ├── repositories/   # Repository pattern
│   ├── rbac/           # RBAC models, deps, seed
│   ├── security/       # Refresh tokens, login attempts, audit
│   ├── billing/        # Subscriptions, invoices, payments
│   ├── integrations/   # YooKassa, Telegram
│   ├── middleware/      # Tenant, security, license
│   ├── templates/      # Email HTML шаблоны
│   ├── tasks/          # Celery tasks
│   └── main.py         # App factory
├── tests/              # 51 pytest tests
├── alembic/            # Migrations
├── Dockerfile
└── requirements.txt
frontend/
├── index.html          # SPA магазин + админка
├── css/style.css       # Стили + 6 тем
├── js/app.js           # Логика (2800+ строк)
├── js/i18n.js          # EN/RU переводы
├── manifest.json       # PWA
└── sw.js               # Service Worker
landing/
├── index.html          # SaaS лендинг (тарифы, регистрация)
├── onboarding.html     # Мастер настройки магазина
└── dashboard.html      # Личный кабинет продавца
deploy/
└── nginx/default.conf  # Nginx: SSL, WebSocket, security headers
scripts/
├── setup-server.sh     # Настройка VPS
├── install.sh          # CLI установщик
├── backup.sh           # Бэкап БД
└── restore.sh          # Восстановление БД
```

## Лицензия

MIT
