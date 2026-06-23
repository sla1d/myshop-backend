"""add user profile fields

Revision ID: 44cc78a1265e
Revises: 048363d72968
Create Date: 2026-06-23 20:20:23.410202

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44cc78a1265e'
down_revision: Union[str, Sequence[str], None] = '048363d72968'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('full_name', sa.String(length=200), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('address', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'address')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'full_name')
    op.drop_column('users', 'email')
