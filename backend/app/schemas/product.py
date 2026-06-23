from pydantic import BaseModel


class Product(BaseModel):
    """Схема товара."""

    id: int
    name: str
    price: int
    image: str
    category: str
    brand: str
    rating: float

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    """Схема для создания товара."""

    name: str
    price: int
    image: str
    category: str
    brand: str = ""
    rating: float = 0.0


class ProductUpdate(BaseModel):
    """Схема для обновления товара."""

    name: str | None = None
    price: int | None = None
    image: str | None = None
    category: str | None = None
    brand: str | None = None
    rating: float | None = None
