from pydantic import BaseModel


class ProfileResponse(BaseModel):
    """Схема профиля пользователя."""

    id: int
    username: str
    role: str
    email: str | None = None
    full_name: str | None = None
    phone: str | None = None
    address: str | None = None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    """Схема обновления профиля."""

    email: str | None = None
    full_name: str | None = None
    phone: str | None = None
    address: str | None = None


class PasswordChange(BaseModel):
    """Схема смены пароля."""

    old_password: str
    new_password: str
