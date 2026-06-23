from pydantic import BaseModel, field_validator


class ReviewCreate(BaseModel):
    """Схема для создания отзыва."""

    product_id: int
    rating: int
    text: str = ""

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("rating: 1–5")
        return v


class ReviewResponse(BaseModel):
    """Схема ответа с отзывом."""

    id: int
    user_id: int
    username: str
    product_id: int
    rating: int
    text: str
    created_at: str

    model_config = {"from_attributes": True}
