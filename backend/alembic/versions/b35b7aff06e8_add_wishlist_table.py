"""add wishlist table

Revision ID: b35b7aff06e8
Revises: 0feccc9b929c
Create Date: 2026-06-23 20:46:32

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b35b7aff06e8'
down_revision: Union[str, Sequence[str], None] = '0feccc9b929c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'wishlist',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'product_id'),
    )


def downgrade() -> None:
    op.drop_table('wishlist')
