from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database.connection import get_async_session
from app.models.product import Product
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse

router = APIRouter(prefix="/reviews", tags=["Отзывы"])


class AvgRating(BaseModel):
    avg_rating: float
    review_count: int


@router.get("/product/{product_id}", response_model=list[ReviewResponse])
async def get_product_reviews(
    product_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Получить отзывы товара."""
    result = await session.execute(
        select(Review).where(Review.product_id == product_id).order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()
    out = []
    for r in reviews:
        user = await session.get(User, r.user_id)
        out.append(ReviewResponse(
            id=r.id,
            user_id=r.user_id,
            username=user.username if user else "unknown",
            product_id=r.product_id,
            rating=r.rating,
            text=r.text,
            created_at=r.created_at.isoformat(),
        ))
    return out


@router.get("/product/{product_id}/avg", response_model=AvgRating)
async def get_avg_rating(
    product_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Средний рейтинг и количество отзывов товара."""
    result = await session.execute(
        select(
            func.coalesce(func.avg(Review.rating), 0),
            func.count(Review.id),
        ).where(Review.product_id == product_id)
    )
    row = result.one()
    return AvgRating(avg_rating=round(float(row[0]), 1), review_count=row[1])


@router.post("", response_model=ReviewResponse, status_code=201)
async def create_review(
    body: ReviewCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создать отзыв (только авторизованные)."""
    product = await session.get(Product, body.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    existing = await session.execute(
        select(Review).where(Review.user_id == user.id, Review.product_id == body.product_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Вы уже оставляли отзыв на этот товар")

    review = Review(user_id=user.id, product_id=body.product_id, rating=body.rating, text=body.text)
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return ReviewResponse(
        id=review.id,
        user_id=user.id,
        username=user.username,
        product_id=review.product_id,
        rating=review.rating,
        text=review.text,
        created_at=review.created_at.isoformat(),
    )
