"""
Lightweight migration utilities for Open WebUI internal databases.

This package deliberately keeps runtime migrations minimal and idempotent.
Each helper should expose a pure function that can be reused both at
application startup and from standalone maintenance scripts.
"""

from .recurring_tasks import ensure_recurring_task_schema
from .legacy_organization import remove_legacy_organization_schema
from .materials_storage import ensure_materials_storage_schema

__all__ = [
    "ensure_recurring_task_schema",
    "remove_legacy_organization_schema",
    "ensure_materials_storage_schema",
]
