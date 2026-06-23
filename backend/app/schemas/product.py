from pydantic import BaseModel, Field


class Product(BaseModel):
    """Схема товара."""
    id: int
    name: str = Field(..., examples=["Смартфон X"])
    price: int = Field(..., examples=[29999], description="Цена в рублях")
    image: str = Field(..., examples=["https://picsum.photos/seed/sp/300/300"])
    category: str = Field(..., examples=["electronics"])
    brand: str = Field(..., examples=["TechCo"])
    rating: float = Field(..., examples=[4.5], description="Рейтинг 0-5")

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    """Схема для создания товара."""
    name: str = Field(..., examples=["Новый товар"])
    price: int = Field(..., gt=0, examples=[19999])
    image: str = Field(..., examples=["https://example.com/image.jpg"])
    category: str = Field(..., examples=["electronics"])
    brand: str = Field(default="", examples=["BrandName"])
    rating: float = Field(default=0.0, ge=0, le=5, examples=[4.0])


class ProductUpdate(BaseModel):
    """Схема для обновления товара."""
    name: str | None = Field(None, examples=["Обновлённое название"])
    price: int | None = Field(None, gt=0, examples=[15999])
    image: str | None = None
    category: str | None = None
    brand: str | None = None
    rating: float | None = Field(None, ge=0, le=5)
