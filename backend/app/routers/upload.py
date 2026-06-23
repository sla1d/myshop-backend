import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from starlette.responses import FileResponse

from app.api.deps import get_current_admin
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["Загрузка"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 5 * 1024 * 1024


@router.post("")
async def upload_file(
    file: UploadFile,
    admin: User = Depends(get_current_admin),
):
    """Загрузить изображение (только админ)."""
    if file.content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail="Допустимы: JPEG, PNG, WebP, GIF")
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Максимум 5 МБ")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    (UPLOAD_DIR / filename).write_bytes(data)

    return {"url": f"/uploads/{filename}", "filename": filename}
