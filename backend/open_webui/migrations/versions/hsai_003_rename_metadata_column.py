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
    # Check if the metadata column exists
    from sqlalchemy import text
    connection = op.get_bind()
    
    # Check if metadata column exists
    metadata_exists = False
    material_metadata_exists = False
    
    try:
        result = connection.execute(text("PRAGMA table_info(hsai_materials)"))
        columns = [row[1] for row in result]
        metadata_exists = 'metadata' in columns
        material_metadata_exists = 'material_metadata' in columns
    except Exception as e:
        print(f"Error checking columns: {e}")
    
    # If material_metadata already exists and metadata doesn't, nothing to do
    if material_metadata_exists and not metadata_exists:
        print("Column material_metadata already exists and metadata doesn't exist. Nothing to do.")
        return
    
    # If neither column exists, something is wrong
    if not metadata_exists and not material_metadata_exists:
        print("Neither metadata nor material_metadata column exists. Nothing to do.")
        return
    
    # If only material_metadata exists, something is wrong
    if not metadata_exists and material_metadata_exists:
        print("material_metadata column exists but metadata doesn't. Nothing to do.")
        return
    
    # SQLite requires a more complex approach for column renaming
    # We need to create a new column, copy data, and drop the old one
    try:
        # For databases that support simple column renaming (PostgreSQL, MySQL)
        op.alter_column('hsai_materials', 'metadata', new_column_name='material_metadata')
    except Exception as e:
        # For SQLite, we need a different approach
        print(f"Direct column rename failed: {e}")
        print("Using SQLite-compatible approach...")
        
        # Only add the new column if it doesn't already exist
        if not material_metadata_exists:
            # Add the new column
            op.add_column('hsai_materials', sa.Column('material_metadata', sa.JSON(), nullable=True))
        
        # Copy data from old column to new column (if both exist)
        if metadata_exists and material_metadata_exists:
            connection.execute(
                sa.text("UPDATE hsai_materials SET material_metadata = metadata")
            )
        
        # Drop the old column if it exists
        if metadata_exists:
            op.drop_column('hsai_materials', 'metadata')


def downgrade():
    """Rename material_metadata column back to metadata in hsai_materials table"""
    # Check if the columns exist
    from sqlalchemy import text
    connection = op.get_bind()
    
    # Check if metadata column exists
    metadata_exists = False
    material_metadata_exists = False
    
    try:
        result = connection.execute(text("PRAGMA table_info(hsai_materials)"))
        columns = [row[1] for row in result]
        metadata_exists = 'metadata' in columns
        material_metadata_exists = 'material_metadata' in columns
    except Exception as e:
        print(f"Error checking columns: {e}")
    
    # If metadata already exists and material_metadata doesn't, nothing to do
    if metadata_exists and not material_metadata_exists:
        print("Column metadata already exists and material_metadata doesn't exist. Nothing to do.")
        return
    
    # If neither column exists, something is wrong
    if not metadata_exists and not material_metadata_exists:
        print("Neither metadata nor material_metadata column exists. Nothing to do.")
        return
    
    # If only metadata exists, something is wrong
    if metadata_exists and not material_metadata_exists:
        print("metadata column exists but material_metadata doesn't. Nothing to do.")
        return
    
    try:
        # For databases that support simple column renaming (PostgreSQL, MySQL)
        op.alter_column('hsai_materials', 'material_metadata', new_column_name='metadata')
    except Exception as e:
        # For SQLite, we need a different approach
        print(f"Direct column rename failed: {e}")
        print("Using SQLite-compatible approach...")
        
        # Only add the old column back if it doesn't already exist
        if not metadata_exists:
            # Add the old column back
            op.add_column('hsai_materials', sa.Column('metadata', sa.JSON(), nullable=True))
        
        # Copy data from new column to old column (if both exist)
        if material_metadata_exists and metadata_exists:
            connection.execute(
                sa.text("UPDATE hsai_materials SET metadata = material_metadata")
            )
        
        # Drop the new column if it exists
        if material_metadata_exists:
            op.drop_column('hsai_materials', 'material_metadata')