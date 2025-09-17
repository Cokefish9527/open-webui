"""HSAI Extension: Add hsai_viral_videos table

Revision ID: hsai_004_add_viral_videos_table
Revises: hsai_003_rename_metadata_column
Create Date: 2025-09-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'hsai_004_add_viral_videos_table'
down_revision = 'hsai_003_rename_metadata_column'
branch_labels = None
depends_on = None


def upgrade():
    """Create hsai_viral_videos table"""
    # Create the hsai_viral_videos table
    op.create_table(
        'hsai_viral_videos',
        sa.Column('id', sa.String(), nullable=False, primary_key=True),
        sa.Column('video_url', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.String(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, default='pending'),
        sa.Column('is_learned', sa.Boolean(), nullable=False, default=False),
        sa.Column('material_id', sa.String(), nullable=True),
        sa.Column('task_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.Column('processed_at', sa.BigInteger(), nullable=True),
        sa.Column('learned_at', sa.BigInteger(), nullable=True)
    )


def downgrade():
    """Drop hsai_viral_videos table"""
    op.drop_table('hsai_viral_videos')