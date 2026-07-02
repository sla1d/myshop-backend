"""add payment fields to orders

Revision ID: b1c2d3e4f5a6
Revises: 499d77c40998
Create Date: 2026-07-03 01:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "499d77c40998"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("payment_id", sa.String(100), nullable=True))
    op.add_column("orders", sa.Column("payment_status", sa.String(50), nullable=True))
    op.add_column("orders", sa.Column("payment_method", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "payment_method")
    op.drop_column("orders", "payment_status")
    op.drop_column("orders", "payment_id")
