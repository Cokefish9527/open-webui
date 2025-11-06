#!/usr/bin/env python3
"""
Task system automated testing orchestrator.

流程：
1. 创建随机测试账号与公司；
2. （可选）重置用户任务数据；
3. 模拟 Redis 蓝图消息；
4. 轮询校验任务/蓝图节点；
5. 汇总日志、生成报告；
6. 清理账号与数据。
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from task_system_utils import (
    ConfigError,
    TaskSystemConfig,
    create_admin_session,
    ensure_database_url,
    init_logger,
    load_config,
)

from admin_user_lifecycle import create_random_account, delete_account
from reset_user_task_data import reset_user_task_data
from verify_task_system_nodes import verify_task_system_nodes
from collect_service_logs import collect_service_logs
from simulate_blueprint_redis_message import (
    generate_blueprint_message,
    get_redis_connection,
    send_blueprint_message,
)


def _write_report(report_dir: Path, payload: Dict[str, Any]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"task_system_auto_test_report_{timestamp}.md"

    content = [
        "# 任务系统自动化测试报告",
        f"- 执行时间（UTC）: {payload['timestamps']['start']} - {payload['timestamps']['end']}",
        f"- 行为结果: **{payload['status'].upper()}**",
        "",
        "## 账号信息",
        f"- 用户 ID: `{payload['account']['user_id']}`",
        f"- 公司 ID: `{payload['account']['company_id']}`",
        f"- 登录邮箱: `{payload['account']['email']}`",
        f"- 初始密码: `{payload['account']['password']}`",
        "",
        "## 数据重置摘要",
        "```json",
        json.dumps(payload["reset_summary"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 蓝图触发结果",
        f"- Redis 队列: `{payload['blueprint']['queue']}`",
        f"- 消息 ID: `{payload['blueprint']['message_id']}`",
        "",
        "## 数据校验结果",
        f"- 校验状态: **{payload['verification']['status']}**",
        "```json",
        json.dumps(payload["verification"]["details"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 日志采集",
        f"- 匹配条数: {len(payload['logs']['matches'])}",
    ]

    if payload["logs"]["matches"]:
        content.append("```")
        content.extend(payload["logs"]["matches"])
        content.append("```")

    content.append("")
    content.append("## 警告")
    if payload["verification"]["warnings"]:
        for warn in payload["verification"]["warnings"]:
            content.append(f"- {warn}")
    else:
        content.append("- 无")

    report_path.write_text("\n".join(content), encoding="utf-8")
    return report_path


def run_orchestration(
    config: TaskSystemConfig,
    logger,
    max_retry: int = 5,
    poll_interval: float = 5.0,
    dry_run: bool = False,
) -> Dict[str, Any]:
    ensure_database_url(config)

    report_payload: Dict[str, Any] = {
        "status": "failed",
        "timestamps": {
            "start": datetime.utcnow().isoformat(),
            "end": None,
        },
    }

    session = create_admin_session(config, logger=logger)
    account = None
    redis_client = None

    try:
        if dry_run:
            logger.info("Dry run 模式，仅创建报告骨架")
            report_payload.update(
                {
                    "account": {
                        "user_id": "dry-run",
                        "company_id": "dry-run",
                        "email": "dry-run@example.com",
                        "password": "N/A",
                    },
                    "reset_summary": {},
                    "blueprint": {"queue": config.redis.queue, "message_id": "dry-run"},
                    "verification": {"status": "skipped", "warnings": [], "details": {}},
                    "logs": {"matches": []},
                }
            )
            report_payload["status"] = "skipped"
            return report_payload

        logger.info("创建随机测试账号")
        account = create_random_account(config, session=session, logger=logger)
        report_payload["account"] = {
            "user_id": account.user["id"],
            "company_id": account.company["id"],
            "email": account.user["email"],
            "password": account.password,
        }

        logger.info("重置用户历史数据")
        reset_summary = reset_user_task_data(
            config, account.user["id"], dry_run=False, logger=logger
        )
        report_payload["reset_summary"] = reset_summary

        logger.info("发送蓝图触发消息到 Redis")
        redis_client = get_redis_connection(
            host=config.redis.host,
            port=config.redis.port,
            db=0,
        )
        message = generate_blueprint_message(user_id=account.user["id"])
        send_blueprint_message(redis_client, message, queue_name=config.redis.queue)
        report_payload["blueprint"] = {
            "queue": config.redis.queue,
            "message_id": message["data"]["id"],
        }

        logger.info("轮询等待任务系统数据同步")
        verification = None
        for attempt in range(max_retry):
            verification = verify_task_system_nodes(
                config, account.user["id"], logger=logger
            )
            if verification.status == "passed":
                break
            logger.warning(
                "第 %s 次校验未通过，等待 %s 秒后重试",
                attempt + 1,
                poll_interval,
            )
            time.sleep(poll_interval)

        if not verification:
            raise ConfigError("未得到校验结果")

        report_payload["verification"] = {
            "status": verification.status,
            "warnings": verification.warnings,
            "details": verification.details,
        }

        log_matches: List[str] = []
        logs_conf = config.raw.get("logs", {})
        log_path_value = logs_conf.get("path")
        if log_path_value:
            log_path = Path(log_path_value)
            keywords = logs_conf.get("keywords") or []
            log_matches = collect_service_logs(log_path, keywords=keywords)
        else:
            logger.info("未配置日志路径，跳过日志采集")

        report_payload["logs"] = {"matches": log_matches}

        status = (
            "passed"
            if verification.status == "passed" and not log_matches
            else "warning"
        )
        report_payload["status"] = status
        return report_payload

    finally:
        if account and not dry_run:
            logger.info("清理测试账号")
            try:
                delete_account(
                    config,
                    user_id=account.user["id"],
                    company_id=account.company["id"],
                    session=session,
                    logger=logger,
                )
            except Exception as exc:  # pragma: no cover
                logger.exception("删除测试账号失败: %s", exc)

        report_payload["timestamps"]["end"] = datetime.utcnow().isoformat()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="任务系统自动化测试编排器")
    parser.add_argument("--config", help="配置文件路径", default=None)
    parser.add_argument("--max-retry", type=int, default=5, help="最大校验重试次数")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="重试间隔秒数")
    parser.add_argument("--dry-run", action="store_true", help="跳过实际执行")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args(argv)
    logger = init_logger("task_system_orchestrator", verbose=args.verbose)

    config = load_config(args.config)
    report_payload = run_orchestration(
        config,
        logger=logger,
        max_retry=args.max_retry,
        poll_interval=args.poll_interval,
        dry_run=args.dry_run,
    )

    report_dir = config.report.ensure_report_dir()
    report_path = _write_report(report_dir, report_payload)
    logger.info("报告已生成: %s", report_path)
    if report_payload["status"] == "passed":
        return 0
    if report_payload["status"] == "warning":
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
