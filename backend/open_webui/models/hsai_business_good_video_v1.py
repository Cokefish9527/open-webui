import logging
from typing import Optional, List
from datetime import datetime

from open_webui.internal.db import get_db
from open_webui.internal.db_n8n import N8NBase, get_n8n_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, Boolean, DateTime

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

REVIEW_STATUS_APPROVED = "approved"

####################
# ORM definitions
####################


class HSAIBusinessGoodVideoV1(N8NBase):
    """ORM model for hsai_business_good_video_v1 (PostgreSQL)."""

    __tablename__ = "hsai_business_good_video_v1"

    id = Column(BigInteger, primary_key=True)
    businessname = Column(String(255), nullable=False)
    authorname = Column(Text, nullable=True)
    authorid = Column(Text, nullable=True)
    authorurl = Column(Text, nullable=True)
    videourl = Column(Text, nullable=True)
    music = Column(String(255), nullable=True)
    musicurl = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)
    video_type = Column(Text, nullable=True)
    publishedtime = Column(DateTime, nullable=True)
    isad = Column(Boolean, nullable=False, default=False)
    diggcount = Column(BigInteger, nullable=False, default=0)
    sharecount = Column(BigInteger, nullable=False, default=0)
    playcount = Column(BigInteger, nullable=False, default=0)
    collectcount = Column(BigInteger, nullable=False, default=0)
    commentcount = Column(BigInteger, nullable=False, default=0)
    createdat = Column(DateTime, nullable=False, default=datetime.now)
    updatedat = Column(DateTime, nullable=False, default=datetime.now)
    review_status = Column(String(20), nullable=True, default="pending")
    review_time = Column(DateTime, nullable=True)
    reviewer_id = Column(String(50), nullable=True)
    review_comments = Column(Text, nullable=True)


####################
# Pydantic models
####################


class HSAIBusinessGoodVideoV1Model(BaseModel):
    """Read model for business good videos."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Video identifier")
    businessname: str = Field(description="Company or tenant name")
    authorname: Optional[str] = Field(default=None, description="Author name")
    authorid: Optional[str] = Field(default=None, description="Author identifier")
    authorurl: Optional[str] = Field(default=None, description="Author url")
    videourl: Optional[str] = Field(default=None, description="Video url")
    music: Optional[str] = Field(default=None, description="Music name")
    musicurl: Optional[str] = Field(default=None, description="Music url")
    text: Optional[str] = Field(default=None, description="Video text content")
    hashtags: Optional[str] = Field(default=None, description="Hashtags")
    video_type: Optional[str] = Field(default=None, description="Video category")
    publishedtime: Optional[datetime] = Field(default=None, description="Published at")
    isad: bool = Field(default=False, description="Whether it is an ad video")
    diggcount: int = Field(default=0, description="Likes count")
    sharecount: int = Field(default=0, description="Shares count")
    playcount: int = Field(default=0, description="Plays count")
    collectcount: int = Field(default=0, description="Collections count")
    commentcount: int = Field(default=0, description="Comments count")
    createdat: datetime = Field(description="Created at")
    updatedat: datetime = Field(description="Updated at")
    review_status: Optional[str] = Field(default=None, description="Moderation status")
    review_time: Optional[datetime] = Field(default=None, description="Moderation timestamp")
    reviewer_id: Optional[str] = Field(default=None, description="Moderator identifier")
    review_comments: Optional[str] = Field(default=None, description="Moderation remarks")


class HSAIBusinessGoodVideoV1Table:
    """Table operations for hsai_business_good_video_v1."""

    @staticmethod
    def _approved_query(postgres_db):
        return postgres_db.query(HSAIBusinessGoodVideoV1).filter(
            HSAIBusinessGoodVideoV1.review_status == REVIEW_STATUS_APPROVED
        )

    def get_videos(
        self,
        skip: int = 0,
        limit: int = 50,
        business_name: Optional[str] = None,
    ) -> List[HSAIBusinessGoodVideoV1Model]:
        """Return videos. business_name is preserved for compatibility but not used for filtering."""
        with get_n8n_db() as db:
            query = self._approved_query(db)
            videos = query.offset(skip).limit(limit).all()
            return [HSAIBusinessGoodVideoV1Model.model_validate(video) for video in videos]

    def get_videos_with_status_filter(
        self,
        skip: int = 0,
        limit: int = 50,
        status_filter: str = "all",
        business_name: Optional[str] = None,
    ) -> List[HSAIBusinessGoodVideoV1Model]:
        """Return video list filtered by learning status for the given tenant."""
        from open_webui.models.hsai_video_learning_status import (
            HSAIVideoLearningStatus,
            HSAIVideoLearningStatuses,
        )

        with get_n8n_db() as postgres_db:
            query = self._approved_query(postgres_db)

            if status_filter == "all":
                videos = query.offset(skip).limit(limit).all()
                return [HSAIBusinessGoodVideoV1Model.model_validate(video) for video in videos]

            with get_db() as sqlite_db:
                if status_filter == "pending":
                    if business_name:
                        learning_video_ids = HSAIVideoLearningStatuses.list_video_ids_by_business(business_name)
                    else:
                        learning_video_ids = [
                            row[0] for row in sqlite_db.query(HSAIVideoLearningStatus.video_id).all()
                        ]
                    numeric_ids = [int(vid) for vid in learning_video_ids if str(vid).isdigit()]
                    if numeric_ids:
                        query = query.filter(~HSAIBusinessGoodVideoV1.id.in_(numeric_ids))
                else:
                    if business_name:
                        status_video_ids = HSAIVideoLearningStatuses.list_video_ids_by_business(
                            business_name, status_filter=status_filter
                        )
                    else:
                        status_video_ids = [
                            row[0]
                            for row in sqlite_db.query(HSAIVideoLearningStatus.video_id).filter(
                                HSAIVideoLearningStatus.status == status_filter
                            ).all()
                        ]
                    numeric_ids = [int(vid) for vid in status_video_ids if str(vid).isdigit()]
                    if not numeric_ids:
                        return []
                    query = query.filter(HSAIBusinessGoodVideoV1.id.in_(numeric_ids))

            videos = query.offset(skip).limit(limit).all()
            return [HSAIBusinessGoodVideoV1Model.model_validate(video) for video in videos]

    def get_total_count_with_status_filter(
        self,
        status_filter: str = "all",
        business_name: Optional[str] = None,
    ) -> int:
        """Return total count with status filtering."""
        from open_webui.models.hsai_video_learning_status import (
            HSAIVideoLearningStatus,
            HSAIVideoLearningStatuses,
        )

        with get_n8n_db() as postgres_db:
            query = self._approved_query(postgres_db)

            if status_filter == "all":
                return query.count()

            with get_db() as sqlite_db:
                if status_filter == "pending":
                    if business_name:
                        learning_video_ids = HSAIVideoLearningStatuses.list_video_ids_by_business(business_name)
                    else:
                        learning_video_ids = [
                            row[0] for row in sqlite_db.query(HSAIVideoLearningStatus.video_id).all()
                        ]
                    numeric_ids = [int(vid) for vid in learning_video_ids if str(vid).isdigit()]
                    if not numeric_ids:
                        return query.count()
                    return query.filter(~HSAIBusinessGoodVideoV1.id.in_(numeric_ids)).count()
                else:
                    if business_name:
                        status_video_ids = HSAIVideoLearningStatuses.list_video_ids_by_business(
                            business_name, status_filter=status_filter
                        )
                    else:
                        status_video_ids = [
                            row[0]
                            for row in sqlite_db.query(HSAIVideoLearningStatus.video_id).filter(
                                HSAIVideoLearningStatus.status == status_filter
                            ).all()
                        ]
                    numeric_ids = [int(vid) for vid in status_video_ids if str(vid).isdigit()]
                    if not numeric_ids:
                        return 0
                    return query.filter(HSAIBusinessGoodVideoV1.id.in_(numeric_ids)).count()

    def get_video_by_id(self, video_id: int) -> Optional[HSAIBusinessGoodVideoV1Model]:
        """Return a single video by id."""
        with get_n8n_db() as db:
            video = (
                self._approved_query(db)
                .filter(HSAIBusinessGoodVideoV1.id == video_id)
                .first()
            )
            return HSAIBusinessGoodVideoV1Model.model_validate(video) if video else None

    def get_total_count(self) -> int:
        """Return total video count."""
        with get_n8n_db() as db:
            return self._approved_query(db).count()


# Global helper
HSAIBusinessGoodVideos = HSAIBusinessGoodVideoV1Table()
