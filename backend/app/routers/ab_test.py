import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.ab_test import ABTest, ABTestAssignment
from app.models.user import User

router = APIRouter(prefix="/ab-test", tags=["A/B тестирование"])
logger = logging.getLogger(__name__)


class ABTestCreate(BaseModel):
    name: str
    variant_a_label: str = "A"
    variant_b_label: str = "B"
    variant_a_weight: int = 50
    variant_b_weight: int = 50


class ABTestResponse(BaseModel):
    test_name: str
    variant: str
    variant_label: str


@router.post("/create")
async def create_ab_test(
    body: ABTestCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Создать A/B тест (admin)."""
    existing = await session.execute(select(ABTest).where(ABTest.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Тест уже существует")

    test = ABTest(
        name=body.name,
        variant_a_label=body.variant_a_label,
        variant_b_label=body.variant_b_label,
        variant_a_weight=body.variant_a_weight,
        variant_b_weight=body.variant_b_weight,
    )
    session.add(test)
    await session.commit()
    return {"status": "ok", "name": body.name}


@router.get("/{test_name}", response_model=ABTestResponse)
async def get_ab_variant(
    test_name: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить вариант A/B теста для текущего пользователя."""
    result = await session.execute(select(ABTest).where(ABTest.name == test_name))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")

    assign_result = await session.execute(
        select(ABTestAssignment).where(
            ABTestAssignment.test_name == test_name,
            ABTestAssignment.user_id == user.id,
        )
    )
    assignment = assign_result.scalar_one_or_none()
    if assignment:
        label = test.variant_a_label if assignment.variant == "A" else test.variant_b_label
        return ABTestResponse(test_name=test_name, variant=assignment.variant, variant_label=label)

    total = test.variant_a_weight + test.variant_b_weight
    roll = secrets.randbelow(total)
    variant = "A" if roll < test.variant_a_weight else "B"
    label = test.variant_a_label if variant == "A" else test.variant_b_label

    new_assignment = ABTestAssignment(
        test_name=test_name,
        user_id=user.id,
        variant=variant,
    )
    session.add(new_assignment)
    await session.commit()

    logger.info("AB test '%s': user %d → variant %s", test_name, user.id, variant)
    return ABTestResponse(test_name=test_name, variant=variant, variant_label=label)
