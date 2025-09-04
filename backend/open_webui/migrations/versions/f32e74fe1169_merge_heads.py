"""merge heads

Revision ID: f32e74fe1169
Revises: 6f2cc730e7b9, hsai_002_add_assignee_to_tasks
Create Date: 2025-09-04 14:50:34.405682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'f32e74fe1169'
down_revision: Union[str, None] = ('6f2cc730e7b9', 'hsai_002_add_assignee_to_tasks')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
