"""Merge multiple heads

Revision ID: merge_multiple_heads
Revises: f32e74fe1169, hsai_003_rename_metadata_column
Create Date: 2025-09-15 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_multiple_heads'
down_revision: Union[str, None] = ('f32e74fe1169', 'hsai_003_rename_metadata_column')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass