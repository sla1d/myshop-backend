from pydantic import BaseModel


class OrderCreate(BaseModel):
    """Схема для создания заказа."""

    address: str


class OrderResponse(BaseModel):
    """Схема ответа после создания заказа."""

    status: str
    order_id: int
    total: int


class OrderItemAdmin(BaseModel):
    """Позиция заказа в админке."""

    product_name: str
    quantity: int
    price: int

    model_config = {"from_attributes": True}


class OrderAdmin(BaseModel):
    """Заказ в админке."""

    id: int
    user_id: int
    username: str
    total: int
    address: str
    status: str
    created_at: str
    items: list[OrderItemAdmin]

    model_config = {"from_attributes": True}
