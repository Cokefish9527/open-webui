"""HSAI Extension: Rename metadata column to material_metadata in hsai_materials table

Revision ID: hsai_003_rename_metadata_column
Revises: hsai_002_add_assignee_to_tasks
Create Date: 2025-09-12 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'hsai_003_rename_metadata_column'
down_revision = 'hsai_002_add_assignee_to_tasks'
branch_labels = None
depends_on = None


def upgrade():
    """Rename metadata column to material_metadata in hsai_materials table"""
    # SQLite requires a more complex approach for column renaming
    # We need to create a new column, copy data, and drop the old one
    try:
        # For databases that support simple column renaming (PostgreSQL, MySQL)
        op.alter_column('hsai_materials', 'metadata', new_column_name='material_metadata')
    except Exception as e:
        # For SQLite, we need a different approach
        print(f"Direct column rename failed: {e}")
        print("Using SQLite-compatible approach...")
        
        # Add the new column
        op.add_column('hsai_materials', sa.Column('material_metadata', sa.JSON(), nullable=True))
        
        # Copy data from old column to new column
        connection = op.get_bind()
        connection.execute(
            sa.text("UPDATE hsai_materials SET material_metadata = metadata")
        )
        
        # Drop the old column
        op.drop_column('hsai_materials', 'metadata')


def downgrade():
    """Rename material_metadata column back to metadata in hsai_materials table"""
    try:
        # For databases that support simple column renaming (PostgreSQL, MySQL)
        op.alter_column('hsai_materials', 'material_metadata', new_column_name='metadata')
    except Exception as e:
        # For SQLite, we need a different approach
        print(f"Direct column rename failed: {e}")
        print("Using SQLite-compatible approach...")
        
        # Add the old column back
        op.add_column('hsai_materials', sa.Column('metadata', sa.JSON(), nullable=True))
        
        # Copy data from new column to old column
        connection = op.get_bind()
        connection.execute(
            sa.text("UPDATE hsai_materials SET metadata = material_metadata")
        )
        
        # Drop the new column
        op.drop_column('hsai_materials', 'material_metadata')