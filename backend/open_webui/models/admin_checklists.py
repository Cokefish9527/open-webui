import logging
from typing import Optional

from open_webui.internal.db_admin import AdminBase, get_admin_db
from open_webui.env import SRC_LOG_LEVELS

from sqlalchemy import Column, String, Integer, Boolean

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
