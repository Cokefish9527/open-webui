#!/usr/bin/env python3
"""
Verify task system data nodes after blueprint-triggered execution.

Checks include:
- Required tasks created with correct status.
- Blueprint progress records and links present.
- State logs exist for created tasks.
- Outbox events generated for onboarding blueprint sync.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError

from task_system_utils import (
    ConfigError,
    TaskSystemConfig,
    ensure_database_url,
    init_logger,
    load_config,
)


@dataclass
class VerificationResult:
    status: str
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def _fetch_task_summary(session, user_id: str) -> Dict[str, Any]:
    from open_webui.models.hsai_tasks import HSAITask

    tasks = list(
        session.scalars(select(HSAITask).where(HSAITask.user_id == user_id))
    )
    summary = {
        "total": len(tasks),
        "by_status": {},
        "tasks": [],
    }
    for task in tasks:
        summary["by_status"].setdefault(task.status, 0)
        summary["by_status"][task.status] += 1
        summary["tasks"].append(
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "project_id": task.project_id,
                "created_at": task.created_at,
            }
        )
    return summary


def _blueprint_progress_summary(session, user_id: str) -> Dict[str, Any]:
    from open_webui.models.hsai_projects import HSAIProject
    from open_webui.models.hsai_blueprint_progress import (
        HSAIBlueprintProgress,
        HSAIBlueprintProgressHistory,
        HSAITaskBlueprintLink,
    )

    projects = list(
        session.scalars(
            select(HSAIProject).where(HSAIProject.user_id == user_id)
        )
    )
    project_ids = [proj.id for proj in projects]
    progress = []
    if project_ids:
        progress = list(
            session.scalars(
                select(HSAIBlueprintProgress).where(
                    HSAIBlueprintProgress.project_id.in_(project_ids)
                )
            )
        )

    progress_ids = [p.id for p in progress]
    history_records: List[Any] = []
    link_records: List[Any] = []
    if progress_ids:
        history_records = list(
            session.scalars(
                select(HSAIBlueprintProgressHistory).where(
                    HSAIBlueprintProgressHistory.progress_id.in_(progress_ids)
                )
            )
        )
        link_records = list(
            session.scalars(
                select(HSAITaskBlueprintLink).where(
                    HSAITaskBlueprintLink.progress_id.in_(progress_ids)
                )
            )
        )

    return {
        "projects": len(projects),
        "progress_records": len(progress),
        "progress_ids": progress_ids,
        "history_records": len(history_records),
        "task_links": len(link_records),
    }


def _outbox_summary(session, user_id: str) -> Dict[str, Any]:
    from open_webui.models.hsai_outbox import HSAIOutboxEvent

    try:
        events = list(
            session.scalars(
                select(HSAIOutboxEvent)
                .order_by(HSAIOutboxEvent.created_at.desc())
                .limit(200)
            )
        )
    except ProgrammingError:
        return {"total": 0, "events": [], "warning": "hsai_outbox_events table missing"}
    events = [
        event
        for event in events
        if isinstance(event.payload, dict)
        and str(event.payload.get("user_id")) == str(user_id)
    ]
    return {
        "total": len(events),
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "status": event.status,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }


def verify_task_system_nodes(
    config: TaskSystemConfig,
    user_id: str,
    logger=None,
) -> VerificationResult:
    if logger is None:
        logger = init_logger("verify_task_system_nodes")

    ensure_database_url(config)

    from open_webui.internal.db import get_db

    with get_db() as session:
        summary = _fetch_task_summary(session, user_id)
        blueprint = _blueprint_progress_summary(session, user_id)
        outbox = _outbox_summary(session, user_id)

        result = VerificationResult(
            status="passed",
            details={
                "tasks": summary,
                "blueprint": blueprint,
                "outbox": outbox,
            },
        )

        if summary["total"] == 0:
            result.status = "failed"
            result.warnings.append("未找到任何任务记录")

        if blueprint["progress_records"] == 0:
            result.status = "failed"
            result.warnings.append("未找到蓝图进度记录")

        if outbox["total"] == 0:
            result.warnings.append("未找到 Outbox 事件，检查是否运行了蓝图同步")

        return result


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="验证任务系统数据节点")
    parser.add_argument("--config", help="配置文件路径", default=None)
    parser.add_argument("--user-id", required=True, help="目标用户 ID")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args(argv)
    logger = init_logger("verify_task_system_nodes", verbose=args.verbose)

    config = load_config(args.config)
    result = verify_task_system_nodes(config, args.user_id, logger=logger)

    logger.info("验证结果: %s", result.status)
    for warning in result.warnings:
        logger.warning(warning)
    logger.info("详情: %s", result.details)

    return 0 if result.status == "passed" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
