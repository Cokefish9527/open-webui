#!/usr/bin/env python3
"""
重置指定用户的任务系统数据，兼容 PostgreSQL。

删除范围：
- hsai_tasks / hsai_task_state_logs / hsai_task_blueprint_links
- hsai_blueprint_progress / hsai_blueprint_progress_history
- hsai_projects（该用户创建）
- companies（该用户作为 owner）

同时会重置用户的 business_name / company_id / info_collection_completed 字段。
"""

from __future__ import annotations

import argparse
from typing import Any, Dict

from sqlalchemy import delete, select, update

from task_system_utils import (
    ConfigError,
    TaskSystemConfig,
    ensure_database_url,
    init_logger,
    load_config,
)


def _collect_ids(session, user_id: str) -> Dict[str, list[str]]:
    from open_webui.models.hsai_tasks import (
        HSAITask,
        HSAITaskStateLog,
    )
    from open_webui.models.hsai_blueprint_progress import (
        HSAIBlueprintProgress,
        HSAIBlueprintProgressHistory,
        HSAITaskBlueprintLink,
    )
    from open_webui.models.hsai_projects import HSAIProject

    task_ids = list(
        session.scalars(select(HSAITask.id).where(HSAITask.user_id == user_id))
    )
    project_ids = list(
        session.scalars(
            select(HSAIProject.id).where(HSAIProject.user_id == user_id)
        )
    )

    progress_ids: list[str] = []
    if project_ids:
        progress_ids = list(
            session.scalars(
                select(HSAIBlueprintProgress.id).where(
                    HSAIBlueprintProgress.project_id.in_(project_ids)
                )
            )
        )

    link_ids: list[str] = []
    if progress_ids:
        link_ids = list(
            session.scalars(
                select(HSAITaskBlueprintLink.id).where(
                    HSAITaskBlueprintLink.progress_id.in_(progress_ids)
                )
            )
        )

    log_ids: list[str] = []
    if task_ids:
        log_ids = list(
            session.scalars(
                select(HSAITaskStateLog.id).where(
                    HSAITaskStateLog.task_id.in_(task_ids)
                )
            )
        )

    history_ids: list[str] = []
    if progress_ids:
        history_ids = list(
            session.scalars(
                select(HSAIBlueprintProgressHistory.id).where(
                    HSAIBlueprintProgressHistory.progress_id.in_(progress_ids)
                )
            )
        )

    return {
        "task_ids": task_ids,
        "project_ids": project_ids,
        "progress_ids": progress_ids,
        "link_ids": link_ids,
        "log_ids": log_ids,
        "history_ids": history_ids,
    }


def reset_user_task_data(
    config: TaskSystemConfig,
    user_id: str,
    dry_run: bool = False,
    logger=None,
) -> Dict[str, Any]:
    """执行数据重置，返回删除数量统计。"""
    if logger is None:
        logger = init_logger("reset_user_task_data")

    ensure_database_url(config)

    # 延迟导入，确保环境变量已生效
    from open_webui.internal.db import get_db
    from open_webui.models.hsai_tasks import (
        HSAITask,
        HSAITaskStateLog,
    )
    from open_webui.models.hsai_blueprint_progress import (
        HSAIBlueprintProgress,
        HSAIBlueprintProgressHistory,
        HSAITaskBlueprintLink,
    )
    from open_webui.models.hsai_projects import HSAIProject
    from open_webui.models.hsai_companies import Company
    from open_webui.models.users import User

    with get_db() as session:
        user = session.get(User, user_id)
        if not user:
            raise ConfigError(f"未找到用户 {user_id}")

        ids = _collect_ids(session, user_id)
        companies = list(
            session.scalars(
                select(Company.id).where(Company.owner_user_id == user_id)
            )
        )

        summary = {
            "tasks": len(ids["task_ids"]),
            "task_logs": len(ids["log_ids"]),
            "task_links": len(ids["link_ids"]),
            "blueprint_progress": len(ids["progress_ids"]),
            "blueprint_history": len(ids["history_ids"]),
            "projects": len(ids["project_ids"]),
            "companies": len(companies),
        }

        if dry_run:
            logger.info("Dry run: %s", summary)
            return summary

        if ids["log_ids"]:
            session.execute(
                delete(HSAITaskStateLog).where(
                    HSAITaskStateLog.id.in_(ids["log_ids"])
                )
            )
        if ids["link_ids"]:
            session.execute(
                delete(HSAITaskBlueprintLink).where(
                    HSAITaskBlueprintLink.id.in_(ids["link_ids"])
                )
            )
        if ids["task_ids"]:
            session.execute(
                delete(HSAITask).where(HSAITask.id.in_(ids["task_ids"]))
            )
        if ids["history_ids"]:
            session.execute(
                delete(HSAIBlueprintProgressHistory).where(
                    HSAIBlueprintProgressHistory.id.in_(ids["history_ids"])
                )
            )
        if ids["progress_ids"]:
            session.execute(
                delete(HSAIBlueprintProgress).where(
                    HSAIBlueprintProgress.id.in_(ids["progress_ids"])
                )
            )
        if ids["project_ids"]:
            session.execute(
                delete(HSAIProject).where(
                    HSAIProject.id.in_(ids["project_ids"])
                )
            )
        if companies:
            session.execute(
                delete(Company).where(Company.id.in_(companies))
            )

        session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                info_collection_completed=False,
                business_name=None,
                company_id=None,
            )
        )

        session.commit()
        logger.info("已清理用户 %s 的任务系统数据", user_id)
        return summary


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="重置用户任务系统数据")
    parser.add_argument("--config", help="配置文件路径", default=None)
    parser.add_argument("--user-id", required=True, help="目标用户 ID")
    parser.add_argument("--dry-run", action="store_true", help="仅统计不执行删除")
    parser.add_argument("--yes", action="store_true", help="跳过二次确认")
    parser.add_argument("--verbose", action="store_true", help="输出调试日志")

    args = parser.parse_args(argv)
    logger = init_logger("reset_user_task_data", verbose=args.verbose)

    config = load_config(args.config)

    if not args.dry_run and not args.yes:
        confirm = input(
            f"将删除用户 {args.user_id} 的任务相关数据，确认继续？(yes/no): "
        )
        if confirm.strip().lower() != "yes":
            logger.info("操作已取消")
            return 0

    summary = reset_user_task_data(
        config=config,
        user_id=args.user_id,
        dry_run=args.dry_run,
        logger=logger,
    )
    logger.info("处理结果: %s", summary)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
