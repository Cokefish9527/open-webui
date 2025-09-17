"""HSAI Extension: Add missing collaborators and shared_sessions columns to hsai_tasks table

Revision ID: hsai_005_add_collaborators_to_tasks
Revises: hsai_004_add_viral_videos_table
Create Date: 2025-09-17 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'hsai_005_add_collaborators_to_tasks'
down_revision = 'hsai_004_add_viral_videos_table'
branch_labels = None
depends_on = None


def upgrade():
    """Add collaborators and shared_sessions columns to hsai_tasks table"""
    # 添加collaborators字段到hsai_tasks表
    op.add_column('hsai_tasks', sa.Column('collaborators', sa.JSON(), nullable=True))
    
    # 添加shared_sessions字段到hsai_tasks表
    op.add_column('hsai_tasks', sa.Column('shared_sessions', sa.JSON(), nullable=True))


def downgrade():
    """Remove collaborators and shared_sessions columns from hsai_tasks table"""
    # 删除shared_sessions字段
    op.drop_column('hsai_tasks', 'shared_sessions')
    
    # 删除collaborators字段
    op.drop_column('hsai_tasks', 'collaborators')