"""
Sync required task templates into Owen_admin.public.task_templates.

Usage:
    python tool/sync_admin_task_templates.py        # apply changes
    python tool/sync_admin_task_templates.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, List

from pathlib import Path
import sys

from sqlalchemy import MetaData, Table, select
from sqlalchemy.exc import SQLAlchemyError

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from open_webui.env import ADMIN_DATABASE_SCHEMA
from open_webui.internal.db_admin import admin_engine, get_admin_db

REQUIRED_TEMPLATES: List[Dict[str, Any]] = [
    {
        "template_key": "company_info_collection",
        "title": "企业信息收集",
        "description": "在企业创建阶段收集法人主体、行业、规模等基础信息，为后续蓝图编排提供数据基线。",
        "task_type": "workflow_execution",
        "task_category": "main",
        "template_scope": "company_seed",
        "priority": 95,
        "status": "active",
        "is_system": True,
        "config": {
            "seed_default_project": True,
            "template_key": "company_info_collection",
            "template_scope": "company_seed",
            "auto_complete_on_blueprint": True,
            "checklist": [
                "确认企业工商主体、品牌名称与统一社会信用代码",
                "收集主营行业、成立年份、核心产品线",
                "确认联系人/企业负责人账号与可用渠道",
            ],
        },
        "prompt_config": {
            "system_prompt": (
                "You are an enterprise onboarding assistant. Collect required business facts "
                "so downstream workflows can trust the data."
            ),
            "initial_message": "您好！为了后续自动化编排，请先补充企业的基础信息。",
            "guidance_questions": [
                "企业法定名称和主要品牌名称是什么？",
                "企业主营行业与核心产品线有哪些？",
                "企业负责人/联系人是谁？请提供邮箱或电话。",
                "企业目前的社媒账号或内容渠道是否已经准备好？",
            ],
            "completion_criteria": "企业名称、行业、规模、联系人信息均已确认，并写入企业档案。",
            "success_message": "企业信息收集完毕，我们会据此继续配置蓝图与任务。",
        },
        "notifications": {
            "on_create": True,
            "on_update": True,
        },
    }
]


def _prepare_payload(template: Dict[str, Any], available_columns: List[str]) -> Dict[str, Any]:
    now = int(time.time())
    base_payload = {
        "id": template.get("id") or template["template_key"],
        "template_key": template["template_key"],
        "name": template["title"],
        "title": template["title"],
        "description": template.get("description"),
        "task_type": template.get("task_type"),
        "task_category": template.get("task_category"),
        "template_scope": template.get("template_scope"),
        "priority": template.get("priority"),
        "status": template.get("status", "active"),
        "is_system": template.get("is_system", True),
        "version": template.get("version"),
        "config": template.get("config"),
        "prompt_config": template.get("prompt_config"),
        "notifications": template.get("notifications"),
        "created_at": now,
        "updated_at": now,
    }
    filtered: Dict[str, Any] = {}
    for column in available_columns:
        if column not in base_payload:
            continue
        value = base_payload[column]
        if value is None:
            continue
        if column in {"config", "prompt_config", "notifications"} and not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        filtered[column] = value
    return filtered


def sync_templates(dry_run: bool = False) -> None:
    metadata = MetaData(schema=ADMIN_DATABASE_SCHEMA)
    table = Table("task_templates", metadata, autoload_with=admin_engine)
    available_columns = table.c.keys()

    lookup_column = "template_key" if "template_key" in available_columns else "id"

    with get_admin_db() as db:
        for template in REQUIRED_TEMPLATES:
            payload = _prepare_payload(template, available_columns)
            template_key = template["template_key"]

            identifier = template_key if lookup_column != "id" else payload.get("id")
            exists_stmt = select(getattr(table.c, lookup_column)).where(
                getattr(table.c, lookup_column) == identifier
            )
            exists = db.execute(exists_stmt).first()

            if exists:
                update_stmt = (
                    table.update()
                    .where(getattr(table.c, lookup_column) == identifier)
                    .values(**payload)
                )
                db.execute(update_stmt)
                print(f"[UPDATE] template_identifier={identifier}")
            else:
                insert_stmt = table.insert().values(**payload)
                db.execute(insert_stmt)
                print(f"[INSERT] template_identifier={identifier}")

        if dry_run:
            db.rollback()
            print("Dry run enabled, rolled back changes.")
        else:
            db.commit()
            print("Templates synchronized successfully.")


def main():
    parser = argparse.ArgumentParser(
        description="Sync required task templates into Owen_admin.public.task_templates"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print operations without committing changes",
    )
    args = parser.parse_args()
    try:
        sync_templates(dry_run=args.dry_run)
    except SQLAlchemyError as exc:
        print(f"[ERROR] Failed to sync templates: {exc}")
        raise


if __name__ == "__main__":
    main()
