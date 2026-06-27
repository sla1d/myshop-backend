"""i18n API — language switching."""
from fastapi import APIRouter, Query

from app.core.i18n import get_supported_languages, get_translations, translate

router = APIRouter(prefix="/i18n", tags=["Мультиязычность"])


@router.get("/languages")
async def list_languages():
    """Get supported languages."""
    return get_supported_languages()


@router.get("/translations")
async def get_all_translations(lang: str = Query("ru", pattern="^(ru|en)$")):
    """Get all translations for a language."""
    return get_translations(lang)


@router.get("/translate/{key}")
async def translate_key(key: str, lang: str = Query("ru", pattern="^(ru|en)$")):
    """Translate a single key."""
    return {"key": key, "lang": lang, "translation": translate(key, lang)}
