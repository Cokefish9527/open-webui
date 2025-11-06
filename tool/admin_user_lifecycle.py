#!/usr/bin/env python3
"""
Admin API user lifecycle helpers for task system automated tests.

提供以下能力：
1. 通过 External Admin API 创建随机账号与公司；
2. 绑定用户与公司，并返回凭证摘要；
3. 根据需要删除账号与公司，清理测试数据。

脚本既可作为模块导入（供 orchestrator 使用），也可通过命令行独立执行。
"""

from __future__ import annotations

import argparse
import secrets
import string
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from task_system_utils import (
    ConfigError,
    TaskSystemConfig,
    create_admin_session,
    init_logger,
    load_config,
)

DEFAULT_EMAIL_DOMAIN = "example.com"


@dataclass
class CreatedAccount:
    user: Dict[str, Any]
    company: Dict[str, Any]
    password: str


def _random_suffix(length: int = 8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_random_account(
    config: TaskSystemConfig,
    prefix: str = "auto-task",
    session: Optional[requests.Session] = None,
    logger: Optional[Any] = None,
) -> CreatedAccount:
    """调用 Admin API 创建随机账号与公司。"""
    if logger is None:
        logger = init_logger("admin_user_lifecycle")

    sess = session or create_admin_session(config, logger=logger)
    suffix = _random_suffix()
    email = f"{prefix}.{suffix}@{DEFAULT_EMAIL_DOMAIN}"
    password = f"Aa{_random_suffix(12)}!"
    name = f"{prefix}-{suffix}"

    user_payload = {
        "name": name,
        "email": email,
        "password": password,
        "role": "user",
        "profile_image_url": "/user.png",
    }

    user_url = f"{config.admin_auth.base_url}/external/admin/users"
    resp = sess.post(user_url, json=user_payload, timeout=30)
    if resp.status_code != 200:
        raise ConfigError(f"创建用户失败: {resp.status_code} {resp.text}")
    user = resp.json()

    company_payload = {
        "owner_user_id": user["id"],
        "name": f"{name}-公司",
        "description": "自动化测试账号对应的公司实体。",
        "company_info": {
            "created_by": "task_system_auto_test",
            "seed": suffix,
        },
    }
    company_url = f"{config.admin_auth.base_url}/external/admin/companies"
    resp = sess.post(company_url, json=company_payload, timeout=30)
    if resp.status_code != 200:
        raise ConfigError(f"创建公司失败: {resp.status_code} {resp.text}")
    company = resp.json()

    assign_url = (
        f"{config.admin_auth.base_url}/external/admin/companies/{company['id']}/users/{user['id']}"
    )
    resp = sess.post(assign_url, timeout=30)
    if resp.status_code not in (200, 204):
        raise ConfigError(f"绑定用户与公司失败: {resp.status_code} {resp.text}")

    logger.info("已创建测试账号 %s (%s)", user["id"], email)
    return CreatedAccount(user=user, company=company, password=password)


def delete_account(
    config: TaskSystemConfig,
    user_id: str,
    company_id: Optional[str] = None,
    session: Optional[requests.Session] = None,
    logger: Optional[Any] = None,
) -> None:
    """调用 Admin API 删除账号及其公司。"""
    if logger is None:
        logger = init_logger("admin_user_lifecycle")

    sess = session or create_admin_session(config, logger=logger)

    user_url = f"{config.admin_auth.base_url}/external/admin/users/{user_id}"
    resp = sess.delete(user_url, timeout=30)
    if resp.status_code not in (200, 204):
        logger.warning("删除用户 %s 失败: %s %s", user_id, resp.status_code, resp.text)
    else:
        logger.info("已删除用户 %s", user_id)

    if company_id:
        company_url = f"{config.admin_auth.base_url}/external/admin/companies/{company_id}"
        resp = sess.delete(company_url, timeout=30)
        if resp.status_code in (200, 204, 404):
            if resp.status_code == 404:
                logger.debug("公司 %s 已不存在", company_id)
            else:
                logger.info("已删除公司 %s", company_id)
        else:
            logger.warning(
                "删除公司 %s 失败: %s %s", company_id, resp.status_code, resp.text
            )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Admin API 账号生命周期工具")
    parser.add_argument("--config", help="配置文件路径", default=None)
    parser.add_argument("--verbose", action="store_true", help="输出调试日志")

    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create-random", help="创建随机测试账号")
    create_parser.add_argument("--prefix", default="auto-task", help="账号前缀")

    delete_parser = subparsers.add_parser("delete", help="删除账号/公司")
    delete_parser.add_argument("--user-id", required=True, help="待删除的用户 ID")
    delete_parser.add_argument("--company-id", help="可选，公司 ID")

    args = parser.parse_args(argv)
    logger = init_logger("admin_user_lifecycle", verbose=args.verbose)

    config = load_config(args.config)

    if args.command == "create-random":
        created = create_random_account(config, prefix=args.prefix, logger=logger)
        logger.info(
            "创建完成: user_id=%s company_id=%s password=%s",
            created.user["id"],
            created.company["id"],
            created.password,
        )
    elif args.command == "delete":
        delete_account(
            config,
            user_id=args.user_id,
            company_id=args.company_id,
            logger=logger,
        )
    else:  # pragma: no cover
        parser.error("未知命令")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
