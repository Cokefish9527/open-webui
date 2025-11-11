import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from open_webui.models.admin_checklists import (
    ChecklistItem,
    ChecklistItems,
    ChecklistPublication,
    ChecklistPublications,
    ChecklistScene,
    ChecklistScenes,
    ChecklistTemplate,
    ChecklistTemplates,
    UserChecklists,
)
from open_webui.models.hsai_materials import HSAIMaterials

log = logging.getLogger(__name__)


@dataclass
class ChecklistTreeNode:
    """树节点模型，兼容前端 folder 响应字段"""

    id: str
    name: str
    node_type: str
    template_id: Optional[str] = None
    template_code: Optional[str] = None
    scene_id: Optional[str] = None
    scene_code: Optional[str] = None
    scene_name: Optional[str] = None
    item_id: Optional[str] = None
    item_code: Optional[str] = None
    description: Optional[str] = None
    is_required: Optional[bool] = None
    shot_sizes: Optional[str] = None
    camera_movements: Optional[str] = None
    duration_min: Optional[int] = None
    duration_max: Optional[int] = None
    min_resolution: Optional[str] = None
    priority: Optional[str] = None
    shooting_tips: Optional[str] = None
    quality_standards: Optional[str] = None
    reference_video: Optional[str] = None
    reference_image: Optional[str] = None
    material_count: int = 0
    children: Optional[List["ChecklistTreeNode"]] = None


class MaterialChecklistService:
    CACHE_TTL_SECONDS = 60

    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[float, List[ChecklistTreeNode]]] = {}

    def get_tree_for_user(self, user) -> List[ChecklistTreeNode]:
        cache_key = f"{getattr(user, 'company_id', '')}:{getattr(user, 'id', '')}"
        cached = self._cache.get(cache_key)
        if cached and cached[0] > time.time():
            return cached[1]

        tree = self._build_tree(user)
        self._cache[cache_key] = (time.time() + self.CACHE_TTL_SECONDS, tree)
        return tree

    def invalidate(self, user) -> None:
        cache_key = f"{getattr(user, 'company_id', '')}:{getattr(user, 'id', '')}"
        self._cache.pop(cache_key, None)

    def get_node(self, user, node_id: Optional[str]) -> Optional[ChecklistTreeNode]:
        if not node_id:
            return None
        tree = self.get_tree_for_user(user)
        for root in tree:
            found = self._find_node(root, node_id)
            if found:
                return found
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_tree(self, user) -> List[ChecklistTreeNode]:
        template_ids = self._resolve_template_ids(user)
        if not template_ids:
            log.info(
                "[Checklist] No published templates found for user=%s company=%s",
                getattr(user, "id", None),
                getattr(user, "company_id", None),
            )
            return []

        templates = {tpl.id: tpl for tpl in self._load_templates(template_ids)}
        scenes = ChecklistScenes.list_by_template_ids(template_ids)
        scenes_by_template: Dict[str, List[ChecklistScene]] = {}
        for scene in scenes:
            scenes_by_template.setdefault(scene.template_id, []).append(scene)

        scene_ids = [scene.id for scene in scenes]
        items = ChecklistItems.list_by_scene_ids(scene_ids)
        items_by_scene: Dict[str, List[ChecklistItem]] = {}
        for item in items:
            items_by_scene.setdefault(item.scene_id, []).append(item)

        counts = self._aggregate_material_counts(user_id=getattr(user, "id", ""))

        tree: List[ChecklistTreeNode] = []
        for template_id, template in templates.items():
            template_node = ChecklistTreeNode(
                id=f"template:{template_id}",
                name=template.name or template.code or template_id,
                node_type="template",
                template_id=template_id,
                template_code=template.code,
                description=template.description,
                children=[],
            )

            for scene in scenes_by_template.get(template_id, []):
                scene_node = ChecklistTreeNode(
                    id=f"scene:{scene.id}",
                    name=scene.scene_name,
                    node_type="scene",
                    template_id=template_id,
                    template_code=template.code,
                    scene_id=scene.id,
                    scene_code=scene.scene_code,
                    scene_name=scene.scene_name,
                    description=scene.description,
                    is_required=scene.is_required,
                    children=[],
                )

                for item in items_by_scene.get(scene.id, []):
                    count = counts.get((scene.scene_code, item.item_code), 0)
                    item_node = ChecklistTreeNode(
                        id=f"item:{item.id}",
                        name=item.item_name,
                        node_type="item",
                        template_id=template_id,
                        template_code=template.code,
                        scene_id=scene.id,
                        scene_code=scene.scene_code,
                        scene_name=scene.scene_name,
                        item_id=item.id,
                        item_code=item.item_code,
                        description=item.description,
                        shot_sizes=item.shot_sizes,
                        camera_movements=item.camera_movements,
                        duration_min=item.duration_min,
                        duration_max=item.duration_max,
                        min_resolution=item.min_resolution,
                        priority=item.priority,
                        shooting_tips=item.shooting_tips,
                        quality_standards=item.quality_standards,
                        reference_video=item.reference_video,
                        reference_image=item.reference_image,
                        material_count=count,
                    )
                    if scene_node.children is not None:
                        scene_node.children.append(item_node)
                    scene_node.material_count += count
                template_node.material_count += scene_node.material_count
                template_node.children.append(scene_node)

            tree.append(template_node)

        return tree

    def _find_node(self, node: ChecklistTreeNode, target_id: str) -> Optional[ChecklistTreeNode]:
        if node.id == target_id:
            return node
        if not node.children:
            return None
        for child in node.children:
            found = self._find_node(child, target_id)
            if found:
                return found
        return None

    def _resolve_template_ids(self, user) -> List[str]:
        user_id = getattr(user, "id", None)
        company_id = getattr(user, "company_id", None)
        template_ids = {chk.template_id for chk in UserChecklists.list_by_user_or_company(user_id, company_id)}
        if template_ids:
            return list(template_ids)

        matched_publications = [
            pub
            for pub in ChecklistPublications.list_published()
            if self._matches_publication(pub, user)
        ]
        template_ids.update(pub.template_id for pub in matched_publications if pub.template_id)
        return list(template_ids)

    def _load_templates(self, template_ids: Sequence[str]) -> List[ChecklistTemplate]:
        results: List[ChecklistTemplate] = []
        for template_id in template_ids:
            template = ChecklistTemplates.get_by_id(template_id)
            if template:
                results.append(template)
        return results

    def _aggregate_material_counts(self, user_id: str) -> Dict[Tuple[Optional[str], Optional[str]], int]:
        records = HSAIMaterials.aggregate_by_scene_and_item(user_id)
        aggregated: Dict[Tuple[Optional[str], Optional[str]], int] = {}
        for record in records:
            key = (record.get("scene_code"), record.get("item_code"))
            aggregated[key] = aggregated.get(key, 0) + int(record.get("materials_count", 0))
        return aggregated

    def _matches_publication(self, publication: ChecklistPublication, user) -> bool:
        if not publication:
            return False
        target_type = (publication.target_type or "all").lower()
        criteria = publication.target_criteria or {}
        company_id = getattr(user, "company_id", None)
        user_id = getattr(user, "id", None)

        if target_type == "all":
            return True
        if target_type in {"company", "company_ids", "specific_company", "specific_companies"}:
            company_ids = set(criteria.get("company_ids", []) or criteria.get("companies", []))
            return bool(company_id and company_id in company_ids)
        if target_type in {"specific_users", "user", "users"}:
            user_ids = set(criteria.get("user_ids", []))
            return bool(user_id and user_id in user_ids)
        if target_type == "industry":
            industry = None
            info = getattr(user, "info", None) or {}
            if isinstance(info, dict):
                industry = info.get("industry") or info.get("company_industry")
            industries = set(criteria.get("industries", []) or criteria.get("industry", []))
            return bool(industry and industry in industries)
        if target_type == "company_size":
            company_size = None
            info = getattr(user, "info", None) or {}
            if isinstance(info, dict):
                company_size = info.get("company_size")
            sizes = set(criteria.get("company_sizes", []) or criteria.get("sizes", []))
            return bool(company_size and company_size in sizes)
        return False


material_checklist_service = MaterialChecklistService()
