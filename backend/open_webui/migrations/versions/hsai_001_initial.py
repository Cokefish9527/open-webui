"""HSAI Extension: Add materials, tasks, and matrix management tables

Revision ID: hsai_001_initial
Revises: 
Create Date: 2025-08-28 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'hsai_001_initial'
down_revision = None  # 根据实际情况设置为当前最新的revision
branch_labels = None
depends_on = None


def upgrade():
    """Create HSAI extension tables"""
    
    # 创建HSAI素材文件夹表
    op.create_table(
        'hsai_material_folders',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('sort_order', sa.BigInteger(), nullable=True, default=0),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parent_id'], ['hsai_material_folders.id'], ),
        sa.Index('ix_hsai_material_folders_user_id', 'user_id'),
        sa.Index('ix_hsai_material_folders_parent_id', 'parent_id')
    )

    # 创建HSAI素材文件表
    op.create_table(
        'hsai_materials',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('material_type', sa.String(), nullable=False),
        sa.Column('folder_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('file_hash', sa.String(), nullable=True),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('ai_analysis', sa.JSON(), nullable=True),
        sa.Column('usage_count', sa.BigInteger(), nullable=True, default=0),
        sa.Column('last_used_at', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='active'),
        sa.Column('access_control', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['folder_id'], ['hsai_material_folders.id'], ),
        sa.Index('ix_hsai_materials_user_id', 'user_id'),
        sa.Index('ix_hsai_materials_folder_id', 'folder_id'),
        sa.Index('ix_hsai_materials_type', 'material_type'),
        sa.Index('ix_hsai_materials_status', 'status')
    )

    # 创建HSAI素材标签表
    op.create_table(
        'hsai_material_tags',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('usage_count', sa.BigInteger(), nullable=True, default=0),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_hsai_material_tags_user_id', 'user_id'),
        sa.Index('ix_hsai_material_tags_name', 'name')
    )

    # 创建HSAI工作流表
    op.create_table(
        'hsai_workflows',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('definition', sa.JSON(), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='active'),
        sa.Column('version', sa.String(), nullable=True, default='1.0'),
        sa.Column('execution_count', sa.BigInteger(), nullable=True, default=0),
        sa.Column('last_executed_at', sa.BigInteger(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_hsai_workflows_user_id', 'user_id'),
        sa.Index('ix_hsai_workflows_status', 'status'),
        sa.Index('ix_hsai_workflows_category', 'category')
    )

    # 创建HSAI任务表
    op.create_table(
        'hsai_tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, default='pending'),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('chat_id', sa.String(), nullable=True),
        sa.Column('collaborators', sa.JSON(), nullable=True),  # 协作者列表
        sa.Column('shared_sessions', sa.JSON(), nullable=True),  # 共享的会话ID列表
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('inputs', sa.JSON(), nullable=True),
        sa.Column('outputs', sa.JSON(), nullable=True),
        sa.Column('workflow_id', sa.String(), nullable=True),
        sa.Column('parent_task_id', sa.String(), nullable=True),
        sa.Column('progress', sa.BigInteger(), nullable=True, default=0),
        sa.Column('started_at', sa.BigInteger(), nullable=True),
        sa.Column('completed_at', sa.BigInteger(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.BigInteger(), nullable=True, default=0),
        sa.Column('priority', sa.BigInteger(), nullable=True, default=0),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['hsai_workflows.id'], ),
        sa.ForeignKeyConstraint(['parent_task_id'], ['hsai_tasks.id'], ),
        sa.Index('ix_hsai_tasks_user_id', 'user_id'),
        sa.Index('ix_hsai_tasks_status', 'status'),
        sa.Index('ix_hsai_tasks_type', 'task_type'),
        sa.Index('ix_hsai_tasks_chat_id', 'chat_id'),
        sa.Index('ix_hsai_tasks_priority', 'priority')
    )

    # 创建HSAI卡片表
    op.create_table(
        'hsai_cards',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('card_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True, default='active'),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('chat_id', sa.String(), nullable=True),
        sa.Column('task_id', sa.String(), nullable=True),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('actions', sa.JSON(), nullable=True),
        sa.Column('position', sa.JSON(), nullable=True),
        sa.Column('style', sa.JSON(), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_collapsed', sa.Boolean(), nullable=True, default=False),
        sa.Column('sort_order', sa.BigInteger(), nullable=True, default=0),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['task_id'], ['hsai_tasks.id'], ),
        sa.Index('ix_hsai_cards_user_id', 'user_id'),
        sa.Index('ix_hsai_cards_chat_id', 'chat_id'),
        sa.Index('ix_hsai_cards_type', 'card_type'),
        sa.Index('ix_hsai_cards_status', 'status')
    )

    # 创建HSAI工作流执行记录表
    op.create_table(
        'hsai_workflow_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('trigger_task_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='pending'),
        sa.Column('progress', sa.BigInteger(), nullable=True, default=0),
        sa.Column('inputs', sa.JSON(), nullable=True),
        sa.Column('outputs', sa.JSON(), nullable=True),
        sa.Column('execution_log', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.BigInteger(), nullable=True),
        sa.Column('completed_at', sa.BigInteger(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['hsai_workflows.id'], ),
        sa.ForeignKeyConstraint(['trigger_task_id'], ['hsai_tasks.id'], ),
        sa.Index('ix_hsai_workflow_executions_workflow_id', 'workflow_id'),
        sa.Index('ix_hsai_workflow_executions_user_id', 'user_id'),
        sa.Index('ix_hsai_workflow_executions_status', 'status')
    )

    # 创建HSAI账号分组表
    op.create_table(
        'hsai_account_groups',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('sort_order', sa.BigInteger(), nullable=True, default=0),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_hsai_account_groups_user_id', 'user_id')
    )

    # 创建HSAI平台账号表
    op.create_table(
        'hsai_platform_accounts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('platform_type', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('platform_account_id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.BigInteger(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='active'),
        sa.Column('last_sync_at', sa.BigInteger(), nullable=True),
        sa.Column('follower_count', sa.BigInteger(), nullable=True, default=0),
        sa.Column('following_count', sa.BigInteger(), nullable=True, default=0),
        sa.Column('posts_count', sa.BigInteger(), nullable=True, default=0),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('group_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['group_id'], ['hsai_account_groups.id'], ),
        sa.Index('ix_hsai_platform_accounts_user_id', 'user_id'),
        sa.Index('ix_hsai_platform_accounts_platform_type', 'platform_type'),
        sa.Index('ix_hsai_platform_accounts_status', 'status'),
        sa.Index('ix_hsai_platform_accounts_group_id', 'group_id')
    )

    # 创建HSAI发布任务表
    op.create_table(
        'hsai_publish_tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('hsai_task_id', sa.String(), nullable=True),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('platforms', sa.JSON(), nullable=False),
        sa.Column('publish_config', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='draft'),
        sa.Column('progress', sa.BigInteger(), nullable=True, default=0),
        sa.Column('scheduled_at', sa.BigInteger(), nullable=True),
        sa.Column('published_at', sa.BigInteger(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.BigInteger(), nullable=True, default=0),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('priority', sa.BigInteger(), nullable=True, default=0),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_hsai_publish_tasks_user_id', 'user_id'),
        sa.Index('ix_hsai_publish_tasks_status', 'status'),
        sa.Index('ix_hsai_publish_tasks_scheduled_at', 'scheduled_at'),
        sa.Index('ix_hsai_publish_tasks_priority', 'priority')
    )

    # 创建HSAI发布记录表
    op.create_table(
        'hsai_publish_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('publish_task_id', sa.String(), nullable=False),
        sa.Column('platform_account_id', sa.String(), nullable=False),
        sa.Column('platform_post_id', sa.String(), nullable=True),
        sa.Column('platform_url', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('publish_data', sa.JSON(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('views', sa.BigInteger(), nullable=True, default=0),
        sa.Column('likes', sa.BigInteger(), nullable=True, default=0),
        sa.Column('comments', sa.BigInteger(), nullable=True, default=0),
        sa.Column('shares', sa.BigInteger(), nullable=True, default=0),
        sa.Column('published_at', sa.BigInteger(), nullable=True),
        sa.Column('last_stats_update_at', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['publish_task_id'], ['hsai_publish_tasks.id'], ),
        sa.ForeignKeyConstraint(['platform_account_id'], ['hsai_platform_accounts.id'], ),
        sa.Index('ix_hsai_publish_records_task_id', 'publish_task_id'),
        sa.Index('ix_hsai_publish_records_account_id', 'platform_account_id'),
        sa.Index('ix_hsai_publish_records_status', 'status'),
        sa.Index('ix_hsai_publish_records_published_at', 'published_at')
    )

    # 创建HSAI数据分析表
    op.create_table(
        'hsai_analytics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('dimension_type', sa.String(), nullable=False),
        sa.Column('dimension_value', sa.String(), nullable=False),
        sa.Column('date', sa.String(), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('previous_metrics', sa.JSON(), nullable=True),
        sa.Column('growth_rate', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_hsai_analytics_user_id', 'user_id'),
        sa.Index('ix_hsai_analytics_dimension', 'dimension_type', 'dimension_value'),
        sa.Index('ix_hsai_analytics_date', 'date'),
        sa.Index('ix_hsai_analytics_period', 'period_type')
    )

    print("HSAI Extension tables created successfully!")


def downgrade():
    """Drop HSAI extension tables"""
    
    # 按照依赖关系逆序删除表
    op.drop_table('hsai_analytics')
    op.drop_table('hsai_publish_records')
    op.drop_table('hsai_publish_tasks')
    op.drop_table('hsai_platform_accounts')
    op.drop_table('hsai_account_groups')
    op.drop_table('hsai_workflow_executions')
    op.drop_table('hsai_cards')
    op.drop_table('hsai_tasks')
    op.drop_table('hsai_workflows')
    op.drop_table('hsai_material_tags')
    op.drop_table('hsai_materials')
    op.drop_table('hsai_material_folders')
    
    print("HSAI Extension tables dropped successfully!")