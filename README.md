# MyShop API

Backend для интернет-магазина электроники. FastAPI + PostgreSQL + Redis + RabbitMQ + Celery.

## Стек

| Компонент | Технология |
|---|---|
| Framework | FastAPI 0.104+ |
| ORM | SQLAlchemy 2.0 (async) |
| БД | PostgreSQL 16 (prod) / SQLite (dev) |
| Миграции | Alembic |
| Авторизация | JWT (access + refresh), bcrypt |
| Кэширование | Redis |
| Очереди | RabbitMQ (pika) |
| Фоновые задачи | Celery |
| Тестирование | pytest + pytest-asyncio |
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

# 3. Миграции
cd backend
alembic upgrade head

# 4. Запуск
python run.py
```

Приложение: http://localhost:8000
Swagger: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

## Docker

```bash
docker-compose up -d
```

Сервисы: backend (8000), PostgreSQL (5432), Redis (6379), RabbitMQ (5672/15672), Celery worker + beat.

## API Endpoints

### Авторизация
| Метод | Путь | Описание |
|---|---|---|
| POST | `/register` | Регистрация |
| POST | `/login` | Вход → access + refresh токены |
| POST | `/refresh` | Обновление токена |

### Товары
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/products` | Список товаров (search, category, brand, min_price, max_price, min_rating, sort) |
| GET | `/api/products/{id}` | Товар по ID |
| GET | `/api/products/categories` | Список категорий |
| GET | `/api/products/brands` | Список брендов |

### Корзина (🔒)
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/cart` | Получить корзину |
| POST | `/api/cart/add` | Добавить товар |
| PUT | `/api/cart/item/{id}` | Изменить количество |
| DELETE | `/api/cart/remove` | Удалить товар |
| DELETE | `/api/cart/clear` | Очистить корзину |

### Заказы (🔒)
| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/order` | Создать заказ (промокод опционален) |

### Избранное (🔒)
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/wishlist` | Список избранного |
| POST | `/api/wishlist` | Добавить |
| DELETE | `/api/wishlist/{id}` | Удалить |
| GET | `/api/wishlist/check/{id}` | Проверить |

### Отзывы
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/reviews/product/{id}` | Отзывы товара |
| GET | `/api/reviews/product/{id}/avg` | Средний рейтинг |
| POST | `/api/reviews` | Создать отзыв (🔒) |

### Промокоды
| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/promos/validate` | Проверить промокод |

### Профиль (🔒)
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/profile` | Данные профиля |
| PATCH | `/api/profile` | Обновить профиль |
| POST | `/api/profile/change-password` | Сменить пароль |
| GET | `/api/profile/orders` | История заказов |

### Админ (🔒 admin)
| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/admin/stats` | Статистика |
| GET | `/api/admin/users` | Список пользователей |
| PATCH | `/api/admin/users/{id}/role` | Изменить роль |
| GET | `/api/admin/products` | Товары |
| POST | `/api/admin/products` | Создать товар |
| PUT | `/api/admin/products/{id}` | Обновить товар |
| DELETE | `/api/admin/products/{id}` | Удалить товар |
| GET | `/api/admin/orders` | Заказы |
| PATCH | `/api/admin/orders/{id}/status` | Статус заказа |
| GET | `/api/admin/promos` | Промокоды |
| POST | `/api/admin/promos` | Создать промокод |
| POST | `/api/upload` | Загрузить изображение |

## Тестовые данные

| Пользователь | Пароль | Роль |
|---|---|---|
| `admin` | `admin123` | admin |

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
│   ├── core/           # config, security, cache, rabbitmq, celery, logging, middleware
│   ├── database/       # engine, session, base
│   ├── models/         # SQLAlchemy ORM
│   ├── schemas/        # Pydantic
│   ├── routers/        # API endpoints
│   ├── services/       # Business logic
│   ├── tasks/          # Celery tasks
│   ├── exceptions.py   # Custom exceptions
│   └── main.py         # App factory
├── tests/              # pytest tests
├── alembic/            # Migrations
├── Dockerfile
└── requirements.txt
frontend/
├── index.html
├── css/style.css
└── js/app.js
```

## Лицензия

MIT
