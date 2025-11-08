import logging
from typing import Iterable, List, Optional

from open_webui.internal.db_admin import AdminBase, get_admin_db
from open_webui.env import SRC_LOG_LEVELS

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

try:  # JSONB 在 PostgreSQL 下可用，其他引擎退回 JSON
    JSONType = JSONB
except Exception:  # pragma: no cover - SQLAlchemy 在缺失时自动回退
    from sqlalchemy import JSON as JSONType

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", "INFO"))


class ChecklistTemplate(AdminBase):
    __tablename__ = "checklist_templates"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    version = Column(String, nullable=True)
    description = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    total_items = Column(Integer, nullable=True)
    required_items = Column(Integer, nullable=True)
    status = Column(String, nullable=True)


class ChecklistScene(AdminBase):
    __tablename__ = "checklist_scenes"

    id = Column(String, primary_key=True)
    template_id = Column(String, ForeignKey("checklist_templates.id"), nullable=False)
    scene_code = Column(String, nullable=False)
    scene_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_required = Column(Boolean, default=True)


class ChecklistItem(AdminBase):
    __tablename__ = "checklist_items"

    id = Column(String, primary_key=True)
    scene_id = Column(String, ForeignKey("checklist_scenes.id"), nullable=False)
    item_code = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    shot_sizes = Column(Text, nullable=True)
    camera_movements = Column(Text, nullable=True)
    duration_min = Column(Integer, default=0)
    duration_max = Column(Integer, default=0)
    min_resolution = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    shooting_tips = Column(Text, nullable=True)
    quality_standards = Column(Text, nullable=True)
    reference_video = Column(Text, nullable=True)
    reference_image = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)


class ChecklistPublication(AdminBase):
    __tablename__ = "checklist_publications"

    id = Column(String, primary_key=True)
    template_id = Column(String, ForeignKey("checklist_templates.id"), nullable=False)
    title = Column(String, nullable=False)
    target_type = Column(String, nullable=True)
    target_criteria = Column(JSONType, nullable=True)
    publish_time = Column(DateTime, nullable=True)
    expire_time = Column(DateTime, nullable=True)
    notification_settings = Column(JSONType, nullable=True)
    completion_deadline = Column(Integer, default=30)
    status = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)


class UserChecklist(AdminBase):
    __tablename__ = "user_checklists"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    publication_id = Column(String, ForeignKey("checklist_publications.id"), nullable=True)
    template_id = Column(String, ForeignKey("checklist_templates.id"), nullable=False)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    status = Column(String, nullable=True)
    total_items = Column(Integer, nullable=True)
    completed_items = Column(Integer, nullable=True)
    completion_rate = Column(Integer, nullable=True)


class ChecklistTemplatesTable:
    def get_by_code(self, code: Optional[str]) -> Optional[ChecklistTemplate]:
        if not code:
            return None
        with get_admin_db() as db:
            try:
                query = (
                    db.query(ChecklistTemplate)
                    .filter(
                        ChecklistTemplate.code == code,
                        ChecklistTemplate.status == "published",
                    )
                    .first()
                )
                if not query:
                    query = (
                        db.query(ChecklistTemplate)
                        .filter(ChecklistTemplate.code == code)
                        .first()
                    )
                return query
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed to load checklist template %s: %s", code, exc)
                return None

    def get_by_id(self, template_id: Optional[str]) -> Optional[ChecklistTemplate]:
        if not template_id:
            return None
        with get_admin_db() as db:
            try:
                return db.get(ChecklistTemplate, template_id)
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed to load checklist template id=%s: %s", template_id, exc)
                return None


ChecklistTemplates = ChecklistTemplatesTable()


class ChecklistScenesTable:
    def list_by_template_ids(self, template_ids: Iterable[str]) -> List[ChecklistScene]:
        ids = [tid for tid in template_ids if tid]
        if not ids:
            return []
        with get_admin_db() as db:
            try:
                return (
                    db.query(ChecklistScene)
                    .filter(ChecklistScene.template_id.in_(ids))
                    .order_by(ChecklistScene.sort_order.asc(), ChecklistScene.id.asc())
                    .all()
                )
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed to load checklist scenes %s: %s", ids, exc)
                return []


ChecklistScenes = ChecklistScenesTable()


class ChecklistItemsTable:
    def list_by_scene_ids(self, scene_ids: Iterable[str]) -> List[ChecklistItem]:
        ids = [sid for sid in scene_ids if sid]
        if not ids:
            return []
        with get_admin_db() as db:
            try:
                return (
                    db.query(ChecklistItem)
                    .filter(ChecklistItem.scene_id.in_(ids))
                    .order_by(ChecklistItem.sort_order.asc(), ChecklistItem.id.asc())
                    .all()
                )
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed to load checklist items %s: %s", ids, exc)
                return []


ChecklistItems = ChecklistItemsTable()


class ChecklistPublicationsTable:
    def list_published(self) -> List[ChecklistPublication]:
        with get_admin_db() as db:
            try:
                return (
                    db.query(ChecklistPublication)
                    .filter(ChecklistPublication.status == "published")
                    .all()
                )
            except Exception as exc:  # pylint: disable=broad-except
                log.error("Failed to load checklist publications: %s", exc)
                return []


ChecklistPublications = ChecklistPublicationsTable()


class UserChecklistsTable:
    def list_by_user_or_company(self, user_id: str | None, company_id: str | None) -> List[UserChecklist]:
        if not user_id:
            return []
        with get_admin_db() as db:
            try:
                return (
                    db.query(UserChecklist)
                    .filter(UserChecklist.user_id == user_id)
                    .all()
                )
            except Exception as exc:  # pylint: disable=broad-except
                log.error(
                    "Failed to load user checklists for user=%s company=%s: %s",
                    user_id,
                    company_id,
                    exc,
                )
                return []


UserChecklists = UserChecklistsTable()
