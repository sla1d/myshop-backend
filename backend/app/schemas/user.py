from pydantic import BaseModel


class UserAuth(BaseModel):
    """Схема для регистрации и входа."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя."""

    id: int
    username: str
    role: str

    model_config = {"from_attributes": True}
