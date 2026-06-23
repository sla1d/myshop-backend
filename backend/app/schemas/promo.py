from pydantic import BaseModel


class PromoApply(BaseModel):
    """Схема применения промокода."""

    code: str


class PromoResponse(BaseModel):
    """Ответ после применения промокода."""

    code: str
    discount_percent: int
    message: str
