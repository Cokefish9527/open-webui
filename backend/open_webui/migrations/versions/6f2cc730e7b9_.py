"""empty message

Revision ID: 6f2cc730e7b9
Revises: 9f0c9cd09105, hsai_001_initial
Create Date: 2025-08-28 22:49:58.625554

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '6f2cc730e7b9'
down_revision: Union[str, None] = ('9f0c9cd09105', 'hsai_001_initial')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
