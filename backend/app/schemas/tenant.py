from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class TenantCreate(BaseModel):
    name: str
    slug: str
    domain: str
    plan: str = "starter"
    admin_username: str = "admin"
    admin_password: str = "admin123"
    admin_email: str = ""
    theme: str = "midnight"


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    domain: str
    plan: str
    subscription_status: str
    active: bool
    theme: str
    store_name: Optional[str] = None
    logo_url: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class TenantSettingsUpdate(BaseModel):
    theme: Optional[str] = None
    logo_url: Optional[str] = None
    store_name: Optional[str] = None


class TenantSettingsResponse(BaseModel):
    theme: str
    logo_url: Optional[str] = None
    store_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PlanLimitsResponse(BaseModel):
    plan: str
    products_used: int
    products_limit: int
    orders_used: int
    orders_limit: int
