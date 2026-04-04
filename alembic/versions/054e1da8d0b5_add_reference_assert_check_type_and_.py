"""add reference_assert check type and reference_code column

Revision ID: 054e1da8d0b5
Revises: ea1a137b6532
Create Date: 2026-04-04 22:06:46.236849

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '054e1da8d0b5'
down_revision: Union[str, Sequence[str], None] = 'ea1a137b6532'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE check_type_enum ADD VALUE IF NOT EXISTS 'reference_assert'")
    op.add_column('tasks', sa.Column('reference_code', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tasks', 'reference_code')
