from pydantic import BaseModel


class PromoApply(BaseModel):
    code: str


class PromoResponse(BaseModel):
    code: str
    discount_percent: int = 0
    discount_amount: int = 0
    message: str
