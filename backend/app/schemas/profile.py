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
    avatar_url: str | None = None
    city: str | None = None
    country: str | None = None
    date_of_birth: str | None = None
    bio: str | None = None
    two_factor_enabled: bool = False
    referral_code: str | None = None
    referral_earnings: int = 0
    loyalty_points: int = 0
    loyalty_level: str = "bronze"

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    """Схема обновления профиля."""

    email: str | None = None
    full_name: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    date_of_birth: str | None = None
    bio: str | None = None


class PasswordChange(BaseModel):
    """Схема смены пароля."""

    old_password: str
    new_password: str
