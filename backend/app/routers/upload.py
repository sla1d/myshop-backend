from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_current_user, get_tenant_id_from_request
from app.rbac.deps import RequirePermission
from app.core.storage import storage, ALLOWED_TYPES, MAX_FILE_SIZE
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["Загрузка"])


@router.post("")
async def upload_file(
    file: UploadFile,
    tenant_id: int | None = Depends(get_tenant_id_from_request),
    _perm: None = Depends(RequirePermission("product.update")),
):
    """Загрузить файл в S3/MinIO (только админ)."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Допустимые типы: {', '.join(ALLOWED_TYPES)}",
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Максимальный размер: {MAX_FILE_SIZE // (1024*1024)} МБ",
        )

    result = await storage.upload_file(
        file_data=data,
        filename=file.filename or "upload.jpg",
        content_type=file.content_type,
        tenant_id=tenant_id,
    )

    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Не удалось загрузить файл. Проверьте настройки хранилища.",
        )

    return {
        "url": result["url"],
        "key": result["key"],
        "filename": result["filename"],
    }


@router.delete("/{key:path}")
async def delete_file(
    key: str,
    _perm: None = Depends(RequirePermission("product.delete")),
):
    """Удалить файл из хранилища."""
    deleted = await storage.delete_file(key)
    if not deleted:
        raise HTTPException(status_code=500, detail="Не удалось удалить файл")
    return {"status": "ok", "deleted": key}
