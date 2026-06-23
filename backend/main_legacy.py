import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import uvicorn
from datetime import datetime

app = FastAPI(title="MyShop API", description="API для интернет-магазина MyShop")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель товара
class Product(BaseModel):
    id: int
    name: str
    price: int
    image: str
    category: str

# Модель для регистрации и входа
class UserAuth(BaseModel):
    username: str
    password: str

# Модель для корзины
class CartItem(BaseModel):
    product_id: int
    quantity: int

# Модель для заказа
class OrderCreate(BaseModel):
    address: str

# Модель для позиции заказа
class OrderItem(BaseModel):
    id: int
    order_id: int
    product_id: int
    quantity: int
    price: int

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    # Создание таблиц
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            image TEXT NOT NULL,
            category TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total INTEGER NOT NULL,
            address TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    
    # Заполнение начальными данными
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        products_data = [
            ('Смартфон X', 29999, 'https://picsum.photos/seed/smartphone/300/300', 'electronics'),
            ('Ноутбук Pro', 89999, 'https://picsum.photos/seed/laptop/300/300', 'electronics'),
            ('Наушники Wireless', 15999, 'https://picsum.photos/seed/headphones/300/300', 'electronics'),
            ('Монитор 4K', 45999, 'https://picsum.photos/seed/monitor/300/300', 'electronics'),
            ('Клавиатура Mechanical', 12999, 'https://picsum.photos/seed/keyboard/300/300', 'electronics'),
            ('Мышь Gaming', 8999, 'https://picsum.photos/seed/mouse/300/300', 'electronics'),
            ('SSD 1TB', 9999, 'https://picsum.photos/seed/ssd/300/300', 'storage'),
            ('USB-C Hub', 4999, 'https://picsum.photos/seed/hub/300/300', 'accessories'),
            ('Power Bank 20000mAh', 7999, 'https://picsum.photos/seed/powerbank/300/300', 'accessories'),
            ('Bluetooth Speaker', 6999, 'https://picsum.photos/seed/speaker/300/300', 'electronics'),
            ('Apple Watch', 24999, 'https://picsum.photos/seed/watch/300/300', 'wearables'),
            ('AirPods Pro', 19999, 'https://picsum.photos/seed/airpods/300/300', 'electronics'),
            ('Smart Watch', 21999, 'https://picsum.photos/seed/smartwatch/300/300', 'wearables'),
            ('Gaming Console', 39999, 'https://picsum.photos/seed/console/300/300', 'gaming'),
            ('VR Headset', 49999, 'https://picsum.photos/seed/vr/300/300', 'gaming'),
            ('Drone', 59999, 'https://picsum.photos/seed/drone/300/300', 'electronics'),
            ('Action Camera', 34999, 'https://picsum.photos/seed/camera/300/300', 'electronics'),
            ('Fitness Tracker', 7999, 'https://picsum.photos/seed/fitness/300/300', 'wearables'),
            ('Smart Home Speaker', 8999, 'https://picsum.photos/seed/speaker/300/300', 'smart_home'),
            ('Smart Light Bulb', 1999, 'https://picsum.photos/seed/lightbulb/300/300', 'smart_home'),
        ]
        
        cursor.executemany('INSERT INTO products (name, price, image, category) VALUES (?, ?, ?, ?)', products_data)
    
    conn.commit()
    conn.close()

# Инициализация базы данных при запуске
init_db()

def get_db_connection():
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/products", response_model=List[Product])
async def get_products():
    """Получить список всех товаров"""
    conn = get_db_connection()
    products = conn.execute('SELECT id, name, price, image, category FROM products').fetchall()
    conn.close()
    return [dict(product) for product in products]

@app.get("/api/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    """Получить товар по ID"""
    conn = get_db_connection()
    product = conn.execute('SELECT id, name, price, image, category FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return dict(product)

@app.get("/api/products/category/{category}", response_model=List[Product])
async def get_products_by_category(category: str):
    """Получить товары по категории"""
    conn = get_db_connection()
    products = conn.execute('SELECT id, name, price, image, category FROM products WHERE category = ?', (category,)).fetchall()
    conn.close()
    return [dict(product) for product in products]

@app.post("/api/register")
async def register(user_data: UserAuth):
    """Регистрация нового пользователя"""
    username = user_data.username
    password = user_data.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        
        # Создаем пустую корзину для нового пользователя
        user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if user:
            # Создаем начальную корзину с product_id = 0 (заполнитель)
            conn.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)', 
                        (user['id'], 0, 0))
            conn.commit()
        
        return {"status": "ok"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()

@app.post("/api/login")
async def login(user_data: UserAuth):
    """Вход пользователя"""
    username = user_data.username
    password = user_data.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    conn.close()

    if user is None:
        raise HTTPException(status_code=401, detail="Неверные данные")

    return {"status": "ok", "username": username, "user_id": user['id']}

@app.get("/api/cart")
async def get_cart(username: str):
    """Получить корзину пользователя"""
    conn = get_db_connection()
    
    # Получаем user_id
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if user is None:
        conn.close()
        raise HTTPException(status_code=401, detail="Пользователь не авторизован")
    
    user_id = user['id']
    
    # Получаем товары в корзине
    cart_items = conn.execute('''
        SELECT p.id, p.name, p.price, p.image, c.quantity 
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ? AND c.product_id > 0
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return [dict(item) for item in cart_items]

@app.post("/api/cart/add")
async def add_to_cart(username: str, cart_item: CartItem):
    """Добавить товар в корзину пользователя"""
    conn = get_db_connection()
    
    # Получаем user_id
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if user is None:
        conn.close()
        raise HTTPException(status_code=401, detail="Пользователь не авторизован")
    
    user_id = user['id']
    product_id = cart_item.product_id
    quantity = cart_item.quantity

    # Проверяем, существует ли товар
    product = conn.execute('SELECT id FROM products WHERE id = ?', (product_id,)).fetchone()
    if product is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Проверяем, есть ли запись в корзине
    existing_item = conn.execute('SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?', 
                                (user_id, product_id)).fetchone()

    if existing_item:
        # Обновляем количество
        new_quantity = existing_item['quantity'] + quantity
        conn.execute('UPDATE cart SET quantity = ? WHERE id = ?', 
                    (new_quantity, existing_item['id']))
    else:
        # Добавляем новую запись
        conn.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)', 
                    (user_id, product_id, quantity))

    conn.commit()
    conn.close()
    
    return {"status": "ok"}

@app.delete("/api/cart/remove")
async def remove_from_cart(username: str, product_id: int):
    """Удалить товар из корзины пользователя"""
    conn = get_db_connection()
    
    # Получаем user_id
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if user is None:
        conn.close()
        raise HTTPException(status_code=401, detail="Пользователь не авторизован")
    
    user_id = user['id']

    # Удаляем товар из корзины
    conn.execute('DELETE FROM cart WHERE user_id = ? AND product_id = ?', (user_id, product_id))
    conn.commit()
    conn.close()
    
    return {"status": "ok"}

@app.post("/api/order")
async def create_order(username: str, order_data: OrderCreate):
    """Создать заказ"""
    conn = get_db_connection()
    
    # Получаем user_id
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if user is None:
        conn.close()
        raise HTTPException(status_code=401, detail="Пользователь не авторизован")
    
    user_id = user['id']

    # Получаем товары в корзине
    cart_items = conn.execute('''
        SELECT p.id, p.name, p.price, c.quantity 
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ? AND c.product_id > 0
    ''', (user_id,)).fetchall()

    if not cart_items:
        conn.close()
        raise HTTPException(status_code=400, detail="Корзина пуста")

    # Вычисляем общую сумму
    total = sum(item['price'] * item['quantity'] for item in cart_items)

    # Создаем заказ
    created_at = datetime.now().isoformat()
    order = conn.execute('''
        INSERT INTO orders (user_id, total, address, created_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, total, order_data.address, created_at))
    
    order_id = order.lastrowid

    # Добавляем товары в заказ
    for item in cart_items:
        conn.execute('''
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
        ''', (order_id, item['id'], item['quantity'], item['price']))

    # Очищаем корзину
    conn.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))

    conn.commit()
    conn.close()
    
    return {"status": "ok", "order_id": order_id, "total": total}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
