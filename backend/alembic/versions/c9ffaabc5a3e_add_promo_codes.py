"""add promo codes

Revision ID: c9ffaabc5a3e
Revises: b35b7aff06e8
Create Date: 2026-06-23 20:54:31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c9ffaabc5a3e'
down_revision: Union[str, Sequence[str], None] = 'b35b7aff06e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'promo_codes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('discount_percent', sa.Integer(), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('used_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )


def downgrade() -> None:
    op.drop_table('promo_codes')
