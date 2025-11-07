import logging
from typing import Optional, List, Dict, Any

from open_webui.internal.db_n8n import N8NBase, get_n8n_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, DateTime, Boolean

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# ORM definitions
####################


class HSAIBusinessVideoContentLearned(N8NBase):
    """ORM model for hsai_business_video_content_learned (PostgreSQL)."""

    __tablename__ = "hsai_business_video_content_learned"

    id = Column(BigInteger, primary_key=True)
    videoid = Column(BigInteger, nullable=False, default=0)
    businessname = Column(String(255), nullable=False)
    videourl = Column(Text, nullable=True)
    music = Column(String(255), nullable=True)
    musicurl = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)
    videotype = Column(Text, nullable=True)
    publishedtime = Column(DateTime, nullable=True)
    isad = Column(Boolean, nullable=False, default=False)
    diggcount = Column(BigInteger, nullable=False, default=0)
    sharecount = Column(BigInteger, nullable=False, default=0)
    playcount = Column(BigInteger, nullable=False, default=0)
    collectcount = Column(BigInteger, nullable=False, default=0)
    commentcount = Column(BigInteger, nullable=False, default=0)
    videotranscript = Column(Text, nullable=True)
    videoshots = Column(Text, nullable=True)
    newttscontent = Column(Text, nullable=True)
    newtags = Column(Text, nullable=True)
    userid = Column(Text, nullable=True)
    status = Column(Text, nullable=True)
    createdat = Column(DateTime, nullable=True)
    updatedat = Column(DateTime, nullable=True)


####################
# Pydantic Models
####################


class HSAIBusinessVideoContentLearnedModel(BaseModel):
    """Read model for business video content learned."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Primary key")
    videoid: int = Field(description="Video identifier")
    businessname: str = Field(description="Business name")
    videourl: Optional[str] = Field(description="Video URL")
    music: Optional[str] = Field(description="Music name")
    musicurl: Optional[str] = Field(description="Music URL")
    text: Optional[str] = Field(description="Video text")
    hashtags: Optional[str] = Field(description="Hashtags")
    videotype: Optional[str] = Field(description="Video type")
    publishedtime: Optional[str] = Field(description="Published time")
    isad: bool = Field(description="Is advertisement")
    diggcount: int = Field(description="Like count")
    sharecount: int = Field(description="Share count")
    playcount: int = Field(description="Play count")
    collectcount: int = Field(description="Collect count")
    commentcount: int = Field(description="Comment count")
    videotranscript: Optional[str] = Field(description="Video transcript")
    videoshots: Optional[str] = Field(description="Video shots")
    newttscontent: Optional[str] = Field(description="New TTS content")
    newtags: Optional[str] = Field(description="New tags")
    userid: Optional[str] = Field(description="User ID")
    status: Optional[str] = Field(description="Status")
    createdat: Optional[str] = Field(description="Created at")
    updatedat: Optional[str] = Field(description="Updated at")


class UpdateVideoContentLearnedRequest(BaseModel):
    """Request model for updating video content learned."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(description="Video content learned ID")
    videotranscript: Optional[str] = Field(None, description="Video transcript")
    newttscontent: Optional[str] = Field(None, description="New TTS content")


class HSAIBusinessVideoContentLearnedTable:
    """Table operations for hsai_business_video_content_learned."""

    def get_video_content_by_id(self, id: int) -> Optional[HSAIBusinessVideoContentLearnedModel]:
        """Retrieve video content learned by id."""
        with get_n8n_db() as db:
            video_content = db.query(HSAIBusinessVideoContentLearned).filter(HSAIBusinessVideoContentLearned.id == id).first()
            return HSAIBusinessVideoContentLearnedModel.model_validate(video_content) if video_content else None

    def update_video_content(self, id: int, form_data: Dict[str, Any]) -> Optional[HSAIBusinessVideoContentLearnedModel]:
        """Update video content learned by id."""
        with get_n8n_db() as db:
            video_content = db.query(HSAIBusinessVideoContentLearned).filter(HSAIBusinessVideoContentLearned.id == id).first()
            if video_content:
                for key, value in form_data.items():
                    if hasattr(video_content, key) and value is not None:
                        setattr(video_content, key, value)
                
                db.commit()
                db.refresh(video_content)
                
                return HSAIBusinessVideoContentLearnedModel.model_validate(video_content)
            return None

    def count_unused_scripts(
        self,
        business_name: Optional[str],
        status_whitelist: Optional[List[str]] = None,
    ) -> int:
        """Count scripts that are still available for a given business."""
        if not business_name:
            return 0
        allowed = status_whitelist or ["pending", "unused", "available", None]
        with get_n8n_db() as db:
            try:
                query = db.query(HSAIBusinessVideoContentLearned).filter(
                    HSAIBusinessVideoContentLearned.businessname == business_name
                )
                if allowed:
                    clauses = []
                    for status in allowed:
                        if status is None:
                            clauses.append(HSAIBusinessVideoContentLearned.status.is_(None))
                        else:
                            clauses.append(HSAIBusinessVideoContentLearned.status == status)
                    if clauses:
                        condition = clauses[0]
                        for clause in clauses[1:]:
                            condition = condition | clause
                        query = query.filter(condition)
                return query.count()
            except Exception as exc:  # pylint: disable=broad-except
                log.error(
                    "Failed counting video scripts business=%s err=%s",
                    business_name,
                    exc,
                    exc_info=True,
                )
                return 0


# Global helper
HSAIBusinessVideoContentLearneds = HSAIBusinessVideoContentLearnedTable()
