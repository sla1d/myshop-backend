from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ABTest(Base):
    """A/B тестирование — варианты и назначения."""

    __tablename__ = "ab_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    variant_a_label: Mapped[str] = mapped_column(String(200), nullable=False, default="A")
    variant_b_label: Mapped[str] = mapped_column(String(200), nullable=False, default="B")
    variant_a_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    variant_b_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<ABTest(name='{self.name}')>"


class ABTestAssignment(Base):
    """Назначение пользователя к варианту A/B теста."""

    __tablename__ = "ab_test_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    variant: Mapped[str] = mapped_column(String(1), nullable=False)

    def __repr__(self) -> str:
        return f"<ABTestAssignment(test='{self.test_name}', user={self.user_id}, variant='{self.variant}')>"
