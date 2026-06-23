from pydantic import BaseModel, Field


class UserAuth(BaseModel):
    """Схема для регистрации и входа."""
    username: str = Field(..., examples=["testuser"], description="Имя пользователя")
    password: str = Field(..., examples=["pass123"], description="Пароль")


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя."""
    id: int
    username: str
    role: str

    model_config = {"from_attributes": True}
