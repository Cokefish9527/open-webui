"""Add company table and user-company relationship

Revision ID: hsai_006
Revises: hsai_005_add_collaborators_to_tasks
Create Date: 2025-09-18 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "hsai_006"
down_revision = "hsai_005_add_collaborators_to_tasks"
branch_labels = None
depends_on = None


def upgrade():
    # Create company table
    op.create_table(
        "company",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("business_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )
    
    # Add company_id column to user table
    op.add_column("user", sa.Column("company_id", sa.Text(), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        "fk_user_company_id", 
        "user", 
        "company", 
        ["company_id"], 
        ["id"]
    )


def downgrade():
    # Remove foreign key constraint
    op.drop_constraint("fk_user_company_id", "user", type_="foreignkey")
    
    # Remove company_id column from user table
    op.drop_column("user", "company_id")
    
    # Drop company table
    op.drop_table("company")