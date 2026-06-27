"""i18n — translations for the platform."""
import logging

logger = logging.getLogger("myshop.i18n")

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ─── Navigation ─────────────────────────────────
    "nav.home": {"en": "Home", "ru": "Главная"},
    "nav.catalog": {"en": "Catalog", "ru": "Каталог"},
    "nav.cart": {"en": "Cart", "ru": "Корзина"},
    "nav.profile": {"en": "Profile", "ru": "Профиль"},
    "nav.orders": {"en": "My Orders", "ru": "Мои заказы"},
    "nav.wishlist": {"en": "Wishlist", "ru": "Избранное"},
    "nav.login": {"en": "Login", "ru": "Войти"},
    "nav.register": {"en": "Register", "ru": "Регистрация"},
    "nav.logout": {"en": "Logout", "ru": "Выйти"},
    "nav.admin": {"en": "Admin Panel", "ru": "Панель управления"},

    # ─── Products ───────────────────────────────────
    "product.price": {"en": "Price", "ru": "Цена"},
    "product.buy": {"en": "Buy", "ru": "Купить"},
    "product.in_stock": {"en": "In Stock", "ru": "В наличии"},
    "product.out_of_stock": {"en": "Out of Stock", "ru": "Нет в наличии"},
    "product.reviews": {"en": "Reviews", "ru": "Отзывы"},
    "product.rating": {"en": "Rating", "ru": "Рейтинг"},
    "product.category": {"en": "Category", "ru": "Категория"},
    "product.brand": {"en": "Brand", "ru": "Бренд"},
    "product.search": {"en": "Search products...", "ru": "Поиск товаров..."},
    "product.recommendations": {"en": "Recommended", "ru": "Рекомендуем"},
    "product.add_to_cart": {"en": "Add to Cart", "ru": "В корзину"},
    "product.add_to_wishlist": {"en": "Add to Wishlist", "ru": "В избранное"},

    # ─── Cart ───────────────────────────────────────
    "cart.title": {"en": "Shopping Cart", "ru": "Корзина"},
    "cart.empty": {"en": "Your cart is empty", "ru": "Корзина пуста"},
    "cart.total": {"en": "Total", "ru": "Итого"},
    "cart.checkout": {"en": "Checkout", "ru": "Оформить заказ"},
    "cart.quantity": {"en": "Quantity", "ru": "Количество"},
    "cart.remove": {"en": "Remove", "ru": "Удалить"},
    "cart.clear": {"en": "Clear Cart", "ru": "Очистить корзину"},
    "cart.promo_code": {"en": "Promo Code", "ru": "Промокод"},
    "cart.apply": {"en": "Apply", "ru": "Применить"},

    # ─── Orders ─────────────────────────────────────
    "order.title": {"en": "Order", "ru": "Заказ"},
    "order.history": {"en": "Order History", "ru": "История заказов"},
    "order.status": {"en": "Status", "ru": "Статус"},
    "order.pending": {"en": "Pending", "ru": "Ожидает"},
    "order.processing": {"en": "Processing", "ru": "Обрабатывается"},
    "order.shipped": {"en": "Shipped", "ru": "Отправлен"},
    "order.delivered": {"en": "Delivered", "ru": "Доставлен"},
    "order.cancelled": {"en": "Cancelled", "ru": "Отменён"},
    "order.address": {"en": "Delivery Address", "ru": "Адрес доставки"},
    "order.tracking": {"en": "Track Order", "ru": "Отследить заказ"},

    # ─── Checkout ───────────────────────────────────
    "checkout.title": {"en": "Checkout", "ru": "Оформление заказа"},
    "checkout.name": {"en": "Full Name", "ru": "ФИО"},
    "checkout.phone": {"en": "Phone", "ru": "Телефон"},
    "checkout.email": {"en": "Email", "ru": "Email"},
    "checkout.address": {"en": "Address", "ru": "Адрес"},
    "checkout.city": {"en": "City", "ru": "Город"},
    "checkout.delivery": {"en": "Delivery Method", "ru": "Способ доставки"},
    "checkout.payment": {"en": "Payment Method", "ru": "Способ оплаты"},
    "checkout.confirm": {"en": "Confirm Order", "ru": "Подтвердить заказ"},

    # ─── Auth ───────────────────────────────────────
    "auth.login": {"en": "Login", "ru": "Вход"},
    "auth.register": {"en": "Register", "ru": "Регистрация"},
    "auth.username": {"en": "Username", "ru": "Имя пользователя"},
    "auth.password": {"en": "Password", "ru": "Пароль"},
    "auth.forgot_password": {"en": "Forgot Password?", "ru": "Забыли пароль?"},
    "auth.no_account": {"en": "Don't have an account?", "ru": "Нет аккаунта?"},
    "auth.has_account": {"en": "Already have an account?", "ru": "Уже есть аккаунт?"},

    # ─── Common ─────────────────────────────────────
    "common.save": {"en": "Save", "ru": "Сохранить"},
    "common.cancel": {"en": "Cancel", "ru": "Отмена"},
    "common.delete": {"en": "Delete", "ru": "Удалить"},
    "common.edit": {"en": "Edit", "ru": "Редактировать"},
    "common.add": {"en": "Add", "ru": "Добавить"},
    "common.search": {"en": "Search", "ru": "Поиск"},
    "common.loading": {"en": "Loading...", "ru": "Загрузка..."},
    "common.error": {"en": "Error", "ru": "Ошибка"},
    "common.success": {"en": "Success", "ru": "Успешно"},
    "common.back": {"en": "Back", "ru": "Назад"},
    "common.next": {"en": "Next", "ru": "Далее"},
    "common.submit": {"en": "Submit", "ru": "Отправить"},
    "common.close": {"en": "Close", "ru": "Закрыть"},
    "common.view_all": {"en": "View All", "ru": "Смотреть все"},

    # ─── Footer ─────────────────────────────────────
    "footer.about": {"en": "About Us", "ru": "О нас"},
    "footer.contacts": {"en": "Contacts", "ru": "Контакты"},
    "footer.shipping": {"en": "Shipping", "ru": "Доставка"},
    "footer.returns": {"en": "Returns", "ru": "Возврат"},
    "footer.privacy": {"en": "Privacy Policy", "ru": "Политика конфиденциальности"},
    "footer.terms": {"en": "Terms of Service", "ru": "Условия использования"},
    "footer.rights": {"en": "All Rights Reserved", "ru": "Все права защищены"},
}


def translate(key: str, lang: str = "ru") -> str:
    """Get translation for a key."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get("ru", key))


def get_translations(lang: str = "ru") -> dict[str, str]:
    """Get all translations for a language."""
    return {key: entry.get(lang, entry.get("ru", key)) for key, entry in TRANSLATIONS.items()}


def get_supported_languages() -> list[dict]:
    """Get list of supported languages."""
    return [
        {"code": "ru", "name": "Русский", "native": "Русский"},
        {"code": "en", "name": "English", "native": "English"},
    ]
