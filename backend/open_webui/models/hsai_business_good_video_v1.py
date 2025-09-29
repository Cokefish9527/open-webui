import logging
from typing import Optional, List
from datetime import datetime

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, Boolean, DateTime, BigInteger
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool, NullPool

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

# PostgreSQL数据库连接配置
# 数据库连接信息：pgm-bp1x8d937cl58d1afo.pg.rds.aliyuncs.com:5432
# 用户名：hsai
# 密码：c5agLR)ah28vnA3+%Yyn
# 数据库名：n8n_workflow

# 创建PostgreSQL数据库引擎
POSTGRES_DATABASE_URL = "postgresql://hsai:c5agLR)ah28vnA3+%Yyn@pgm-bp1x8d937cl58d1afo.pg.rds.aliyuncs.com:5432/n8n_workflow"

# 创建PostgreSQL引擎
postgres_engine = create_engine(
    POSTGRES_DATABASE_URL,
    pool_pre_ping=True,
    poolclass=NullPool
)

# 创建PostgreSQL会话
PostgresSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=postgres_engine, expire_on_commit=False
)

class PostgresSessionManager:
    def __enter__(self):
        self.db = PostgresSessionLocal()
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'db'):
            self.db.close()

def get_postgres_session():
    """获取PostgreSQL数据库会话"""
    return PostgresSessionManager()

####################
# HSAI Business Good Video V1 DB Schema
####################


class HSAIBusinessGoodVideoV1(Base):
    """HSAI优质视频表 (PostgreSQL)"""
    __tablename__ = "hsai_business_good_video_v1"

    id = Column(BigInteger, primary_key=True)               # 视频ID
    businessname = Column(String(255), nullable=False)      # 公司名称
    authorname = Column(Text, nullable=True)                # 作者名称
    authorid = Column(Text, nullable=True)                  # 作者ID
    authorurl = Column(Text, nullable=True)                 # 作者链接
    videourl = Column(Text, nullable=True)                  # 视频链接
    music = Column(String(255), nullable=True)              # 音乐
    musicurl = Column(Text, nullable=True)                  # 音乐链接
    text = Column(Text, nullable=True)                      # 视频文本
    hashtags = Column(Text, nullable=True)                  # 标签
    video_type = Column(Text, nullable=True)                # 视频类型
    publishedtime = Column(DateTime, nullable=True)         # 发布时间
    isad = Column(Boolean, nullable=False, default=False)   # 是否为广告
    diggcount = Column(BigInteger, nullable=False, default=0)  # 点赞数
    sharecount = Column(BigInteger, nullable=False, default=0) # 分享数
    playcount = Column(BigInteger, nullable=False, default=0)  # 播放数
    collectcount = Column(BigInteger, nullable=False, default=0) # 收藏数
    commentcount = Column(BigInteger, nullable=False, default=0) # 评论数
    createdat = Column(DateTime, nullable=False, default=datetime.now)  # 创建时间
    updatedat = Column(DateTime, nullable=False, default=datetime.now)  # 更新时间


####################
# Pydantic Models
####################


class HSAIBusinessGoodVideoV1Model(BaseModel):
    """HSAI优质视频模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="视频ID")
    businessname: str = Field(description="公司名称")
    authorname: Optional[str] = Field(default=None, description="作者名称")
    authorid: Optional[str] = Field(default=None, description="作者ID")
    authorurl: Optional[str] = Field(default=None, description="作者链接")
    videourl: Optional[str] = Field(default=None, description="视频链接")
    music: Optional[str] = Field(default=None, description="音乐")
    musicurl: Optional[str] = Field(default=None, description="音乐链接")
    text: Optional[str] = Field(default=None, description="视频文本")
    hashtags: Optional[str] = Field(default=None, description="标签")
    video_type: Optional[str] = Field(default=None, description="视频类型")
    publishedtime: Optional[datetime] = Field(default=None, description="发布时间")
    isad: bool = Field(default=False, description="是否为广告")
    diggcount: int = Field(default=0, description="点赞数")
    sharecount: int = Field(default=0, description="分享数")
    playcount: int = Field(default=0, description="播放数")
    collectcount: int = Field(default=0, description="收藏数")
    commentcount: int = Field(default=0, description="评论数")
    createdat: datetime = Field(description="创建时间")
    updatedat: datetime = Field(description="更新时间")


class HSAIBusinessGoodVideoV1Table:
    """HSAI优质视频表操作类"""
    
    def get_videos(self, skip: int = 0, limit: int = 50) -> List[HSAIBusinessGoodVideoV1Model]:
        """分页获取视频列表"""
        with get_postgres_session() as db:
            videos = db.query(HSAIBusinessGoodVideoV1).offset(skip).limit(limit).all()
            return [HSAIBusinessGoodVideoV1Model.model_validate(video) for video in videos]
    
    def get_videos_with_status_filter(self, skip: int = 0, limit: int = 50, status_filter: str = "all") -> List[HSAIBusinessGoodVideoV1Model]:
        """分页获取视频列表，支持按学习状态筛选"""
        from open_webui.models.hsai_video_learning_status import HSAIVideoLearningStatus
        
        with get_postgres_session() as postgres_db:
            if status_filter == "all":
                # 不筛选状态，直接分页查询
                videos = postgres_db.query(HSAIBusinessGoodVideoV1).offset(skip).limit(limit).all()
                return [HSAIBusinessGoodVideoV1Model.model_validate(video) for video in videos]
            else:
                # 需要根据状态筛选
                with get_db() as sqlite_db:
                    if status_filter == "pending":
                        # 待学习状态：没有对应的学习状态记录
                        # 查询已有学习状态的视频ID
                        learning_video_ids = sqlite_db.query(HSAIVideoLearningStatus.video_id).all()
                        learning_video_ids = [v[0] for v in learning_video_ids]
                        
                        # 查询待学习的视频（ID不在学习状态表中的视频）
                        videos = postgres_db.query(HSAIBusinessGoodVideoV1).filter(
                            ~HSAIBusinessGoodVideoV1.id.in_([int(vid) for vid in learning_video_ids if vid.isdigit()])
                        ).offset(skip).limit(limit).all()
                    else:
                        # 其他状态：learning, learned, abandoned
                        # 查询具有指定状态的学习记录
                        status_video_ids = sqlite_db.query(HSAIVideoLearningStatus.video_id).filter(
                            HSAIVideoLearningStatus.status == status_filter
                        ).all()
                        status_video_ids = [v[0] for v in status_video_ids]
                        
                        # 查询对应的视频
                        videos = postgres_db.query(HSAIBusinessGoodVideoV1).filter(
                            HSAIBusinessGoodVideoV1.id.in_([int(vid) for vid in status_video_ids if vid.isdigit()])
                        ).offset(skip).limit(limit).all()
            
                return [HSAIBusinessGoodVideoV1Model.model_validate(video) for video in videos]
    
    def get_total_count_with_status_filter(self, status_filter: str = "all") -> int:
        """获取按状态筛选后的视频总数"""
        from open_webui.models.hsai_video_learning_status import HSAIVideoLearningStatus
        
        with get_postgres_session() as postgres_db:
            if status_filter == "all":
                # 不筛选状态，返回所有视频总数
                return postgres_db.query(HSAIBusinessGoodVideoV1).count()
            else:
                # 需要根据状态筛选
                with get_db() as sqlite_db:
                    if status_filter == "pending":
                        # 待学习状态：没有对应的学习状态记录
                        # 查询已有学习状态的视频ID
                        learning_video_ids = sqlite_db.query(HSAIVideoLearningStatus.video_id).all()
                        learning_video_ids = [v[0] for v in learning_video_ids]
                        
                        # 计算待学习的视频数量
                        total_count = postgres_db.query(HSAIBusinessGoodVideoV1).filter(
                            ~HSAIBusinessGoodVideoV1.id.in_([int(vid) for vid in learning_video_ids if vid.isdigit()])
                        ).count()
                        return total_count
                    else:
                        # 其他状态：learning, learned, abandoned
                        # 查询具有指定状态的学习记录数量
                        status_video_ids = sqlite_db.query(HSAIVideoLearningStatus.video_id).filter(
                            HSAIVideoLearningStatus.status == status_filter
                        ).all()
                        status_video_ids = [v[0] for v in status_video_ids]
                        
                        # 查询对应的视频数量
                        count = postgres_db.query(HSAIBusinessGoodVideoV1).filter(
                            HSAIBusinessGoodVideoV1.id.in_([int(vid) for vid in status_video_ids if vid.isdigit()])
                        ).count()
                        return count
    
    def get_video_by_id(self, video_id: int) -> Optional[HSAIBusinessGoodVideoV1Model]:
        """根据ID获取视频"""
        with get_postgres_session() as db:
            video = db.query(HSAIBusinessGoodVideoV1).filter(HSAIBusinessGoodVideoV1.id == video_id).first()
            return HSAIBusinessGoodVideoV1Model.model_validate(video) if video else None
    
    def get_total_count(self) -> int:
        """获取视频总数"""
        with get_postgres_session() as db:
            return db.query(HSAIBusinessGoodVideoV1).count()


# 全局实例
HSAIBusinessGoodVideos = HSAIBusinessGoodVideoV1Table()