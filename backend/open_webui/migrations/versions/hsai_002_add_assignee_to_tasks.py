"""HSAI Extension: Add assignee_id to tasks table

Revision ID: hsai_002_add_assignee_to_tasks
Revises: hsai_001_initial
Create Date: 2025-09-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'hsai_002_add_assignee_to_tasks'
down_revision = 'hsai_001_initial'
branch_labels = None
depends_on = None


def upgrade():
    """Add assignee_id column to hsai_tasks table"""
    # 添加assignee_id字段到hsai_tasks表
    op.add_column('hsai_tasks', sa.Column('assignee_id', sa.String(), nullable=True))
    
    # 为assignee_id字段创建索引
    op.create_index('ix_hsai_tasks_assignee_id', 'hsai_tasks', ['assignee_id'])


def downgrade():
    """Remove assignee_id column from hsai_tasks table"""
    # 删除assignee_id字段的索引
    op.drop_index('ix_hsai_tasks_assignee_id', table_name='hsai_tasks')
    
    # 删除assignee_id字段
    op.drop_column('hsai_tasks', 'assignee_id')