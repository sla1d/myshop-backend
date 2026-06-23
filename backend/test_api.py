#!/usr/bin/env python3
"""
Тестовый скрипт для проверки FastAPI сервера MyShop
"""

import requests
import json

def test_api():
    base_url = "http://localhost:8000"
    
    print("Тестирование API MyShop...")
    print("=" * 50)
    
    # Тест 1: Получение списка товаров
    print("\n1. Тест получения списка товаров:")
    try:
        response = requests.get(f"{base_url}/api/products")
        if response.status_code == 200:
            products = response.json()
            print(f"   ✓ Успешно получено {len(products)} товаров")
            print(f"   Пример товара: {products[0]['name']} - {products[0]['price']} ₽")
        else:
            print(f"   ✗ Ошибка: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Ошибка запроса: {e}")
    
    # Тест 2: Получение товара по ID
    print("\n2. Тест получения товара по ID:")
    try:
        response = requests.get(f"{base_url}/api/products/1")
        if response.status_code == 200:
            product = response.json()
            print(f"   ✓ Товар найден: {product['name']}")
        else:
            print(f"   ✗ Товар не найден: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Ошибка запроса: {e}")
    
    # Тест 3: Получение товаров по категории
    print("\n3. Тест получения товаров по категории:")
    try:
        response = requests.get(f"{base_url}/api/products/category/electronics")
        if response.status_code == 200:
            products = response.json()
            print(f"   ✓ Найдено {len(products)} товаров в категории 'electronics'")
        else:
            print(f"   ✗ Ошибка: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Ошибка запроса: {e}")
    
    # Тест 4: Проверка CORS
    print("\n4. Тест CORS middleware:")
    try:
        response = requests.options(f"{base_url}/api/products")
        if response.status_code == 200:
            print("   ✓ CORS middleware работает")
        else:
            print(f"   ✗ CORS middleware не работает: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Ошибка запроса: {e}")
    
    # Тест 5: Регистрация пользователя
    print("\n5. Тест регистрации пользователя:")
    try:
        user_data = {"username": "testuser", "password": "testpass123"}
        response = requests.post(f"{base_url}/api/register", json=user_data)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Пользователь зарегистрирован: {data}")
        else:
            print(f"   ✗ Ошибка регистрации: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ✗ Ошибка запроса: {e}")
    
    # Тест 6: Вход пользователя
    print("\n6. Тест входа пользователя:")
    try:
        user_data = {"username": "testuser", "password": "testpass123"}
        response = requests.post(f"{base_url}/api/login", json=user_data)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Успешный вход: {data}")
        else:
            print(f"   ✗ Ошибка входа: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ✗ Ошибка запроса: {e}")
    
    # Тест 7: Вход с неверными данными
    print("\n7. Тест входа с неверными данными:")
    try:
        user_data = {"username": "wronguser", "password": "wrongpass"}
        response = requests.post(f"{base_url}/api/login", json=user_data)
        if response.status_code == 401:
            print(f"   ✓ Правильно отклонен неверный запрос")
        else:
            print(f"   ✗ Ошибка: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ✗ Ошибка запроса: {e}")
    
    # Тест 8: Работа с корзиной
    print("\n8. Тест работы с корзиной:")
    try:
        # Сначала войдем в систему
        user_data = {"username": "testuser", "password": "testpass123"}
        login_response = requests.post(f"{base_url}/api/login", json=user_data)
        if login_response.status_code == 200:
            print(f"   ✓ Успешный вход")
            
            # Добавим товар в корзину
            add_response = requests.post(f"{base_url}/api/cart/add?username=testuser", json={"product_id": 1, "quantity": 2})
            if add_response.status_code == 200:
                print(f"   ✓ Товар добавлен в корзину")
                
                # Получим корзину
                cart_response = requests.get(f"{base_url}/api/cart?username=testuser")
                if cart_response.status_code == 200:
                    cart_data = cart_response.json()
                    print(f"   ✓ Корзина получена: {cart_data}")
                    
                    # Удалим товар из корзины
                    remove_response = requests.delete(f"{base_url}/api/cart/remove?username=testuser&product_id=1")
                    if remove_response.status_code == 200:
                        print(f"   ✓ Товар удален из корзины")
                    else:
                        print(f"   ✗ Ошибка удаления: {remove_response.status_code}")
                else:
                    print(f"   ✗ Ошибка получения корзины: {cart_response.status_code}")
            else:
                print(f"   ✗ Ошибка добавления товара: {add_response.status_code}")
        else:
            print(f"   ✗ Ошибка входа: {login_response.status_code}")
    except Exception as e:
        print(f"   ✗ Ошибка запроса: {e}")
    
    # Тест 9: Создание заказа
    print("\n9. Тест создания заказа:")
    try:
        # Сначала зарегистрируем нового пользователя
        reg_user_data = {"username": "testuser_order", "password": "testpass123"}
        reg_response = requests.post(f"{base_url}/api/register", json=reg_user_data)
        if reg_response.status_code == 200:
            print(f"   ✓ Пользователь зарегистрирован")
            
            # Войдем в систему
            login_response = requests.post(f"{base_url}/api/login", json=reg_user_data)
            if login_response.status_code == 200:
                print(f"   ✓ Успешный вход")
                
                # Добавим товар в корзину
                add_response = requests.post(f"{base_url}/api/cart/add?username=testuser_order", json={"product_id": 2, "quantity": 1})
                if add_response.status_code == 200:
                    print(f"   ✓ Товар добавлен в корзину")
                    
                    # Создадим заказ
                    order_data = {"address": "г. Москва, ул. Тестовая, д. 1"}
                    order_response = requests.post(f"{base_url}/api/order?username=testuser_order", json=order_data)
                    if order_response.status_code == 200:
                        order_data = order_response.json()
                        print(f"   ✓ Заказ создан: id={order_data['order_id']}, total={order_data['total']} ₽")
                    else:
                        print(f"   ✗ Ошибка создания заказа: {order_response.status_code}")
                else:
                    print(f"   ✗ Ошибка добавления товара: {add_response.status_code}")
            else:
                print(f"   ✗ Ошибка входа: {login_response.status_code}")
        else:
            print(f"   ✗ Ошибка регистрации: {reg_response.status_code}")
    except Exception as e:
        print(f"   ✗ Ошибка запроса: {e}")
    
    print("\n" + "=" * 50)
    print("Тестирование завершено!")

if __name__ == "__main__":
    test_api()
