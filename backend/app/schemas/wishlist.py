from pydantic import BaseModel


class WishlistItem(BaseModel):
    """Схема добавления в избранное."""

    product_id: int


class WishlistResponse(BaseModel):
    """Схема товара в избранном."""

    id: int
    product_id: int
    name: str
    price: int
    image: str
    category: str
    brand: str
    rating: float

    model_config = {"from_attributes": True}
