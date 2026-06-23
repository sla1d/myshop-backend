"""add product brand and rating

Revision ID: 9a9c1235e139
Revises: 44cc78a1265e
Create Date: 2026-06-23 20:27:40.048282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a9c1235e139'
down_revision: Union[str, Sequence[str], None] = '44cc78a1265e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('products', sa.Column('brand', sa.String(length=100), nullable=False, server_default=''))
    op.add_column('products', sa.Column('rating', sa.Float(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('products', 'rating')
    op.drop_column('products', 'brand')
