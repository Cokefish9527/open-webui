"""
Central cache for task templates sourced from Owen Admin or fallback constants.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import MetaData, Table, select
from sqlalchemy.exc import SQLAlchemyError

from open_webui.config.blueprint_task_templates import (
    BLUEPRINT_MAIN_TASK_TEMPLATES as FALLBACK_BLUEPRINT_TEMPLATES,
)
from open_webui.config.project_task_templates import (
    PROJECT_MAIN_TASK_TEMPLATES as FALLBACK_PROJECT_TEMPLATES,
)
from open_webui.internal.db_admin import admin_engine, get_admin_db
from open_webui.env import ADMIN_DATABASE_SCHEMA

log = logging.getLogger(__name__)


SUPPORTED_TASK_TEMPLATE_COLUMNS = [
    "id",
    "template_key",
    "title",
    "name",
    "description",
    "task_type",
    "task_category",
    "template_scope",
    "priority",
    "status",
    "version",
    "config",
    "prompt_config",
    "notifications",
    "blueprint_section",
    "is_system",
    "created_at",
    "updated_at",
]

REQUIRED_TEMPLATE_IDENTIFIERS = {"template_key"}

_TABLE_CACHE: Dict[str, Optional[Table]] = {}
_METADATA = MetaData(schema=ADMIN_DATABASE_SCHEMA)


def _reflect_table(table_name: str) -> Optional[Table]:
    table = _TABLE_CACHE.get(table_name)
    if table is not None:
        return table
    try:
        table = Table(table_name, _METADATA, autoload_with=admin_engine)
        _TABLE_CACHE[table_name] = table
        return table
    except SQLAlchemyError as exc:
        log.warning(
            "Failed to reflect table %s from Owen Admin DB (schema=%s): %s",
            table_name,
            ADMIN_DATABASE_SCHEMA or "public",
            exc,
        )
    except Exception as exc:  # pylint: disable=broad-except
        log.warning("Unexpected error reflecting table %s: %s", table_name, exc)
    _TABLE_CACHE[table_name] = None
    return None


def _parse_json_field(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            log.warning("Failed to decode JSON field, returning empty dict: %s", value)
            return {}
    return {}


@dataclass(frozen=True)
class TaskTemplate:
    key: str
    title: str
    description: Optional[str]
    task_type: str
    task_category: Optional[str]
    template_scope: Optional[str]
    priority: int
    status: str
    version: Optional[str]
    config: Dict[str, Any] = field(default_factory=dict)
    prompt_config: Dict[str, Any] = field(default_factory=dict)
    notifications: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_blueprint_template(self) -> bool:
        category = (self.task_category or "").lower()
        if category.startswith("blueprint"):
            return True
        return bool(self.config.get("blueprint_section"))

    @property
    def is_project_seed_template(self) -> bool:
        if self.config.get("seed_default_project") is False:
            return False
        category = (self.task_category or "").lower()
        if category in {"main", "project_main"}:
            return True
        return self.template_scope == "project_seed"


class TaskTemplateRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._templates: Dict[str, TaskTemplate] = {}
        self._last_refreshed_at: float = 0.0
        self._source: str = "uninitialized"

    @property
    def source(self) -> str:
        return self._source

    def refresh(self, force: bool = False) -> None:
        with self._lock:
            if not force and self._templates and (time.time() - self._last_refreshed_at) < 30:
                return
            templates = self._load_from_admin_db()
            source = "admin_db"
            if not templates:
                templates = self._load_from_fallback()
                source = "fallback"
            self._templates = {template.key: template for template in templates}
            self._last_refreshed_at = time.time()
            self._source = source
            log.info(
                "Task template registry refreshed from %s (%s templates)",
                source,
                len(self._templates),
            )

    def _ensure_ready(self) -> None:
        if not self._templates:
            self.refresh(force=True)

    def get(self, template_key: str) -> Optional[TaskTemplate]:
        self._ensure_ready()
        return self._templates.get(template_key)

    def iter_all(self) -> Iterable[TaskTemplate]:
        self._ensure_ready()
        return list(self._templates.values())

    def iter_blueprint_templates(self) -> Iterable[TaskTemplate]:
        self._ensure_ready()
        return [tpl for tpl in self._templates.values() if tpl.is_blueprint_template]

    def iter_project_seed_templates(self) -> Iterable[TaskTemplate]:
        self._ensure_ready()
        return [tpl for tpl in self._templates.values() if tpl.is_project_seed_template]

    def _load_from_admin_db(self) -> List[TaskTemplate]:
        table = _reflect_table("task_templates")
        if table is None:
            return []

        select_columns = [
            getattr(table.c, column)
            for column in SUPPORTED_TASK_TEMPLATE_COLUMNS
            if hasattr(table.c, column)
        ]

        if not select_columns:
            log.warning(
                "task_templates table does not contain recognised columns; falling back"
            )
            return []

        stmt = select(*select_columns)
        if hasattr(table.c, "status"):
            stmt = stmt.where(table.c.status == "active")

        try:
            with get_admin_db() as db:
                rows = db.execute(stmt).mappings().all()
        except SQLAlchemyError as exc:
            log.error("Failed to load task templates from admin DB: %s", exc, exc_info=True)
            return []

        templates: List[TaskTemplate] = []
        missing_identifier = False
        for row in rows:
            template = self._row_to_template(dict(row))
            if template:
                templates.append(template)
            else:
                missing_identifier = True
        if missing_identifier:
            log.error(
                "Some task_templates rows are missing required identifiers (%s); see logs above",
                ", ".join(sorted(REQUIRED_TEMPLATE_IDENTIFIERS)),
            )
        return templates

    def _row_to_template(self, row: Dict[str, Any]) -> Optional[TaskTemplate]:
        template_key = (
            row.get("template_key")
            or row.get("templateKey")
            or row.get("id")
        )
        if not template_key:
            log.error("Skip task template row without template_key: %s", row)
            return None

        title = row.get("title") or row.get("name") or template_key
        config = _parse_json_field(row.get("config"))
        prompt_config = _parse_json_field(row.get("prompt_config"))
        notifications = _parse_json_field(row.get("notifications"))

        blueprint_section = row.get("blueprint_section")
        if blueprint_section and "blueprint_section" not in config:
            config["blueprint_section"] = blueprint_section

        priority = row.get("priority")
        try:
            priority = int(priority) if priority is not None else 0
        except Exception:
            priority = 0

        return TaskTemplate(
            key=str(template_key),
            title=str(title),
            description=row.get("description"),
            task_type=row.get("task_type") or "workflow_execution",
            task_category=row.get("task_category"),
            template_scope=row.get("template_scope"),
            priority=priority,
            status=row.get("status") or "active",
            version=row.get("version"),
            config=config,
            prompt_config=prompt_config,
            notifications=notifications,
            source="admin_db",
            raw=row,
        )

    def _load_from_fallback(self) -> List[TaskTemplate]:
        log.warning(
            "Falling back to in-repo task templates, admin DB data unavailable"
        )

        def _wrap_fallback(items: Dict[str, Dict[str, Any]]) -> List[TaskTemplate]:
            wrapped: List[TaskTemplate] = []
            for key, payload in items.items():
                wrapped.append(
                    TaskTemplate(
                        key=key,
                        title=payload.get("title", key),
                        description=payload.get("description"),
                        task_type=payload.get("task_type", "workflow_execution"),
                        task_category=payload.get("task_category"),
                        template_scope=payload.get("config", {}).get("template_scope"),
                        priority=int(payload.get("priority") or 0),
                        status="active",
                        version=None,
                        config=payload.get("config", {}),
                        prompt_config=payload.get("prompt_config", {}),
                        notifications=payload.get("notifications", {}),
                        source="fallback",
                        raw=payload,
                    )
                )
            return wrapped

        templates: List[TaskTemplate] = []
        templates.extend(_wrap_fallback(FALLBACK_BLUEPRINT_TEMPLATES))
        templates.extend(_wrap_fallback(FALLBACK_PROJECT_TEMPLATES))
        return templates


task_template_registry = TaskTemplateRegistry()


def get_task_template(template_key: str) -> Optional[TaskTemplate]:
    return task_template_registry.get(template_key)
