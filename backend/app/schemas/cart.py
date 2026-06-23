from pydantic import BaseModel


class CartItem(BaseModel):
    """Схема для добавления товара в корзину."""

    product_id: int
    quantity: int


class CartItemResponse(BaseModel):
    """Схема товара в корзине."""

    id: int
    name: str
    price: int
    image: str
    quantity: int

    model_config = {"from_attributes": True}
