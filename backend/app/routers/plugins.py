"""Plugins API — install, configure, enable/disable plugins per tenant."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_id_from_request
from app.database.connection import get_async_session
from app.models.user import User
from app.plugins.registry import get_plugin, list_plugins
from app.rbac.deps import RequirePermission
from app.saas.models import Plugin

router = APIRouter(prefix="/plugins", tags=["Плагины"])
logger = logging.getLogger("myshop.plugins")


class PluginInstall(BaseModel):
    plugin_key: str


class PluginConfigUpdate(BaseModel):
    config: dict


class PluginResponse(BaseModel):
    id: int | None = None
    plugin_key: str
    name: str
    version: str
    enabled: bool
    installed: bool
    config: dict = {}


# ─── List available plugins ─────────────────────────
@router.get("/available")
async def get_available_plugins(
    category: str | None = None,
):
    """List all available plugins in the marketplace."""
    return list_plugins(category=category)


# ─── List installed plugins for current tenant ──────
@router.get("", response_model=list[PluginResponse])
async def list_installed_plugins(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant не определён")

    result = await session.execute(
        select(Plugin).where(Plugin.tenant_id == tenant_id)
    )
    plugins = result.scalars().all()

    # Merge with registry info
    responses = []
    installed_keys = {p.plugin_key: p for p in plugins}

    for key, defn in _get_registry().items():
        if key in installed_keys:
            p = installed_keys[key]
            config = json.loads(p.config_json) if p.config_json else {}
            responses.append(PluginResponse(
                id=p.id,
                plugin_key=p.plugin_key,
                name=p.name,
                version=p.version,
                enabled=p.enabled,
                installed=True,
                config=config,
            ))
        else:
            responses.append(PluginResponse(
                plugin_key=defn.key,
                name=defn.name,
                version=defn.version,
                enabled=False,
                installed=False,
            ))

    return responses


# ─── Install plugin ─────────────────────────────────
@router.post("/install", response_model=PluginResponse)
async def install_plugin(
    body: PluginInstall,
    request: Request,
    user: User = Depends(RequirePermission("tenant.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant не определён")

    defn = get_plugin(body.plugin_key)
    if not defn:
        raise HTTPException(status_code=404, detail=f"Плагин '{body.plugin_key}' не найден")

    # Check if already installed
    existing = await session.execute(
        select(Plugin).where(
            Plugin.tenant_id == tenant_id,
            Plugin.plugin_key == body.plugin_key,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Плагин уже установлен")

    plugin = Plugin(
        tenant_id=tenant_id,
        plugin_key=defn.key,
        name=defn.name,
        version=defn.version,
        enabled=True,
    )
    session.add(plugin)
    await session.commit()
    await session.refresh(plugin)

    logger.info("Plugin installed: %s for tenant %d", defn.key, tenant_id)

    return PluginResponse(
        id=plugin.id,
        plugin_key=plugin.plugin_key,
        name=plugin.name,
        version=plugin.version,
        enabled=plugin.enabled,
        installed=True,
    )


# ─── Uninstall plugin ───────────────────────────────
@router.delete("/{plugin_key}")
async def uninstall_plugin(
    plugin_key: str,
    request: Request,
    user: User = Depends(RequirePermission("tenant.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    result = await session.execute(
        select(Plugin).where(
            Plugin.tenant_id == tenant_id,
            Plugin.plugin_key == plugin_key,
        )
    )
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="Плагин не установлен")

    await session.delete(plugin)
    await session.commit()

    logger.info("Plugin uninstalled: %s for tenant %d", plugin_key, tenant_id)
    return {"status": "ok"}


# ─── Toggle plugin (enable/disable) ────────────────
@router.patch("/{plugin_key}/toggle")
async def toggle_plugin(
    plugin_key: str,
    request: Request,
    user: User = Depends(RequirePermission("tenant.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    result = await session.execute(
        select(Plugin).where(
            Plugin.tenant_id == tenant_id,
            Plugin.plugin_key == plugin_key,
        )
    )
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="Плагин не установлен")

    plugin.enabled = not plugin.enabled
    await session.commit()
    await session.refresh(plugin)

    return {"enabled": plugin.enabled}


# ─── Update plugin config ───────────────────────────
@router.patch("/{plugin_key}/config")
async def update_plugin_config(
    plugin_key: str,
    body: PluginConfigUpdate,
    request: Request,
    user: User = Depends(RequirePermission("tenant.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    result = await session.execute(
        select(Plugin).where(
            Plugin.tenant_id == tenant_id,
            Plugin.plugin_key == plugin_key,
        )
    )
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="Плагин не установлен")

    plugin.config_json = json.dumps(body.config)
    await session.commit()

    return {"status": "ok", "config": body.config}


def _get_registry():
    from app.plugins.registry import AVAILABLE_PLUGINS
    return AVAILABLE_PLUGINS
