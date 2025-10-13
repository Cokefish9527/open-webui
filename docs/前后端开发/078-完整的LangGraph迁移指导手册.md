# 完整的LangGraph迁移指导手册

## 目录

1. [完整代码示例](#一完整代码示例)
2. [详细技术方案文档](#二详细技术方案文档)
3. [迁移检查清单](#三迁移检查清单)
4. [性能优化方案](#四性能优化方案)
5. [团队培训材料](#五团队培训材料)

---

# 一、完整代码示例

## 1.1 项目结构

```
agent-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI入口
│   │   ├── config.py               # 配置管理
│   │   ├── models/                 # 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── conversation.py
│   │   │   └── user.py
│   │   ├── agents/                 # Agent定义
│   │   │   ├── __init__.py
│   │   │   ├── customer_service.py # 客服Agent
│   │   │   ├── data_analyst.py     # 数据分析Agent
│   │   │   └── code_assistant.py   # 代码助手Agent
│   │   ├── tools/                  # 工具集合
│   │   │   ├── __init__.py
│   │   │   ├── n8n_tools.py        # n8n集成
│   │   │   ├── database_tools.py   # 数据库工具
│   │   │   └── search_tools.py     # 搜索工具
│   │   ├── services/               # 业务服务
│   │   │   ├── __init__.py
│   │   │   ├── agent_service.py
│   │   │   └── state_manager.py
│   │   ├── api/                    # API路由
│   │   │   ├── __init__.py
│   │   │   ├── chat.py
│   │   │   └── admin.py
│   │   └── utils/                  # 工具函数
│   │       ├── __init__.py
│   │       ├── logger.py
│   │       └── metrics.py
│   ├── tests/                      # 测试
│   │   ├── test_agents.py
│   │   ├── test_tools.py
│   │   └── test_api.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   └── (OpenWebUI修改)
└── docs/
    ├── architecture.md
    ├── api.md
    └── deployment.md
```

---

## 1.2 核心代码实现

### **1.2.1 配置管理 (config.py)**

```python
# backend/app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "Agent Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API配置
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = ["http://localhost:3000", "https://your-domain.com"]

    # LLM配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # 或者使用其他LLM提供商
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # 数据库配置
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "agent_user"
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = "agent_platform"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # n8n配置
    N8N_BASE_URL: str = "https://your-n8n.com"
    N8N_API_KEY: str = os.getenv("N8N_API_KEY", "")

    # 向量数据库配置
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")

    # 性能配置
    MAX_CONCURRENT_REQUESTS: int = 100
    REQUEST_TIMEOUT: int = 300  # 秒
    STREAM_CHUNK_SIZE: int = 1024

    # 状态持久化配置
    CHECKPOINT_NAMESPACE: str = "agent_checkpoints"
    MAX_CHECKPOINT_HISTORY: int = 50

    # 监控配置
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()

settings = get_settings()
```

---

### **1.2.2 数据模型 (models/conversation.py)**

```python
# backend/app/models/conversation.py

from sqlalchemy import Column, String, Integer, JSON, DateTime, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Conversation(Base):
    """对话记录表"""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(500))

    # 对话元数据
    agent_type = Column(String(100), nullable=False)  # customer_service, data_analyst, etc.
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 状态信息
    status = Column(String(50), default="active")  # active, archived, deleted

    # 统计信息
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # 索引
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_status', 'status'),
    )

class Message(Base):
    """消息记录表"""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # 消息内容
    role = Column(String(50), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)

    # 元数据
    metadata = Column(JSONB, default={})  # 存储工具调用、思维链等

    # Token信息
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 索引
    __table_args__ = (
        Index('idx_conversation_created', 'conversation_id', 'created_at'),
    )

class AgentCheckpoint(Base):
    """Agent状态检查点"""
    __tablename__ = "agent_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # 检查点数据
    checkpoint_data = Column(JSONB, nullable=False)  # 完整的状态数据
    checkpoint_namespace = Column(String(255), nullable=False)

    # 元数据
    step = Column(Integer, nullable=False)  # 执行步骤
    node_name = Column(String(100))  # 当前节点

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 索引
    __table_args__ = (
        Index('idx_conversation_step', 'conversation_id', 'step'),
    )
```

---

### **1.2.3 状态管理器 (services/state_manager.py)**

```python
# backend/app/services/state_manager.py

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Optional, Dict, Any
import asyncio
from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class StateManager:
    """状态管理器 - 负责Agent状态的持久化和恢复"""

    def __init__(self, use_postgres: bool = True):
        self.use_postgres = use_postgres

        if use_postgres:
            # 使用PostgreSQL持久化
            self.engine = create_async_engine(
                settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
                echo=settings.DEBUG,
                pool_size=10,
                max_overflow=20
            )
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            self.checkpointer = PostgresSaver(self.engine)
        else:
            # 使用内存（开发/测试环境）
            self.checkpointer = MemorySaver()

        logger.info(f"StateManager initialized with {'PostgreSQL' if use_postgres else 'Memory'}")

    async def initialize(self):
        """初始化数据库表"""
        if self.use_postgres:
            await self.checkpointer.setup()
            logger.info("Database tables initialized")

    def get_checkpointer(self):
        """获取检查点保存器"""
        return self.checkpointer

    async def save_checkpoint(
        self,
        conversation_id: str,
        state: Dict[str, Any],
        step: int,
        node_name: str
    ):
        """保存检查点"""
        try:
            # LangGraph会自动通过checkpointer保存
            # 这里可以添加额外的业务逻辑，如记录日志、触发webhook等
            logger.info(
                f"Checkpoint saved for conversation {conversation_id} "
                f"at step {step}, node {node_name}"
            )
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise

    async def load_checkpoint(
        self,
        conversation_id: str,
        step: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """加载检查点"""
        try:
            # LangGraph会自动通过checkpointer加载
            # 这里可以添加额外的业务逻辑
            logger.info(f"Loading checkpoint for conversation {conversation_id}")
            return None  # LangGraph自动处理
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    async def list_checkpoints(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> list:
        """列出检查点历史"""
        try:
            # 从数据库查询检查点历史
            async with self.async_session() as session:
                result = await session.execute(
                    """
                    SELECT step, node_name, created_at 
                    FROM agent_checkpoints 
                    WHERE conversation_id = :conv_id 
                    ORDER BY step DESC 
                    LIMIT :limit
                    """,
                    {"conv_id": conversation_id, "limit": limit}
                )
                return result.fetchall()
        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []

    async def cleanup_old_checkpoints(self, days: int = 30):
        """清理旧的检查点"""
        try:
            async with self.async_session() as session:
                await session.execute(
                    """
                    DELETE FROM agent_checkpoints 
                    WHERE created_at < NOW() - INTERVAL ':days days'
                    """,
                    {"days": days}
                )
                await session.commit()
                logger.info(f"Cleaned up checkpoints older than {days} days")
        except Exception as e:
            logger.error(f"Failed to cleanup checkpoints: {e}")

# 全局实例
state_manager = StateManager(use_postgres=not settings.DEBUG)
```

---

### **1.2.4 工具集成 (tools/n8n_tools.py)**

```python
# backend/app/tools/n8n_tools.py

from langchain.tools import tool
from typing import Dict, Any, Optional
import aiohttp
import asyncio
from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class N8nToolkit:
    """n8n工作流工具集"""

    def __init__(self):
        self.base_url = settings.N8N_BASE_URL
        self.api_key = settings.N8N_API_KEY
        self.timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)

    async def _call_webhook(
        self,
        workflow_name: str,
        params: Dict[str, Any],
        wait_for_completion: bool = False
    ) -> Dict[str, Any]:
        """调用n8n webhook"""
        url = f"{self.base_url}/webhook/{workflow_name}"

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=params, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        logger.info(f"n8n workflow {workflow_name} called successfully")
                        return result
                    else:
                        error_text = await resp.text()
                        logger.error(f"n8n workflow failed: {error_text}")
                        return {"error": error_text, "status": resp.status}

        except asyncio.TimeoutError:
            logger.error(f"n8n workflow {workflow_name} timed out")
            return {"error": "Workflow execution timed out"}

        except Exception as e:
            logger.error(f"n8n workflow error: {e}")
            return {"error": str(e)}

    @tool
    async def generate_report(self, report_type: str, date_range: str) -> str:
        """
        生成报告（调用n8n工作流）

        Args:
            report_type: 报告类型，如 'sales', 'user_activity', 'performance'
            date_range: 日期范围，如 '2024-01-01,2024-01-31'

        Returns:
            报告下载链接或报告内容摘要
        """
        result = await self._call_webhook(
            "generate_report",
            {
                "report_type": report_type,
                "date_range": date_range
            }
        )

        if "error" in result:
            return f"报告生成失败: {result['error']}"

        return f"报告已生成，下载链接: {result.get('download_url', 'N/A')}"

    @tool
    async def sync_data(self, source_system: str, target_system: str, data_type: str) -> str:
        """
        同步数据（调用n8n工作流）

        Args:
            source_system: 源系统，如 'crm', 'erp'
            target_system: 目标系统，如 'data_warehouse'
            data_type: 数据类型，如 'customers', 'orders'

        Returns:
            同步结果
        """
        result = await self._call_webhook(
            "data_sync",
            {
                "source": source_system,
                "target": target_system,
                "type": data_type
            },
            wait_for_completion=False  # 异步执行
        )

        if "error" in result:
            return f"数据同步失败: {result['error']}"

        return f"数据同步任务已启动，任务ID: {result.get('task_id', 'N/A')}"

    @tool
    async def send_notification(
        self,
        recipients: str,
        subject: str,
        message: str,
        channels: str = "email"
    ) -> str:
        """
        发送通知（调用n8n工作流）

        Args:
            recipients: 收件人，逗号分隔
            subject: 主题
            message: 消息内容
            channels: 通知渠道，如 'email,slack,sms'

        Returns:
            发送结果
        """
        result = await self._call_webhook(
            "send_notification",
            {
                "recipients": recipients.split(","),
                "subject": subject,
                "message": message,
                "channels": channels.split(",")
            }
        )

        if "error" in result:
            return f"通知发送失败: {result['error']}"

        return f"通知已发送给 {recipients}"

# 创建工具实例
n8n_toolkit = N8nToolkit()

# 导出工具列表
n8n_tools = [
    n8n_toolkit.generate_report,
    n8n_toolkit.sync_data,
    n8n_toolkit.send_notification
]
```

---

### **1.2.5 数据库工具 (tools/database_tools.py)**

```python
# backend/app/tools/database_tools.py

from langchain.tools import tool
from sqlalchemy import text
from typing import Dict, Any, List
import json
from ..services.state_manager import state_manager
from ..utils.logger import get_logger

logger = get_logger(__name__)

@tool
async def query_orders(user_id: str, limit: int = 10) -> str:
    """
    查询用户订单

    Args:
        user_id: 用户ID
        limit: 返回数量限制

    Returns:
        订单列表的JSON字符串
    """
    try:
        async with state_manager.async_session() as session:
            result = await session.execute(
                text("""
                    SELECT order_id, status, total_amount, created_at 
                    FROM orders 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """),
                {"user_id": user_id, "limit": limit}
            )

            orders = []
            for row in result:
                orders.append({
                    "order_id": str(row[0]),
                    "status": row[1],
                    "total_amount": float(row[2]),
                    "created_at": row[3].isoformat()
                })

            return json.dumps(orders, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to query orders: {e}")
        return json.dumps({"error": str(e)})

@tool
async def query_order_detail(order_id: str) -> str:
    """
    查询订单详情

    Args:
        order_id: 订单ID

    Returns:
        订单详情的JSON字符串
    """
    try:
        async with state_manager.async_session() as session:
            # 订单基本信息
            order_result = await session.execute(
                text("""
                    SELECT order_id, user_id, status, total_amount, 
                           shipping_address, tracking_number, created_at, updated_at
                    FROM orders 
                    WHERE order_id = :order_id
                """),
                {"order_id": order_id}
            )

            order_row = order_result.fetchone()
            if not order_row:
                return json.dumps({"error": "订单不存在"})

            # 订单商品
            items_result = await session.execute(
                text("""
                    SELECT product_name, quantity, price 
                    FROM order_items 
                    WHERE order_id = :order_id
                """),
                {"order_id": order_id}
            )

            items = []
            for item in items_result:
                items.append({
                    "product_name": item[0],
                    "quantity": item[1],
                    "price": float(item[2])
                })

            order_detail = {
                "order_id": str(order_row[0]),
                "user_id": order_row[1],
                "status": order_row[2],
                "total_amount": float(order_row[3]),
                "shipping_address": order_row[4],
                "tracking_number": order_row[5],
                "created_at": order_row[6].isoformat(),
                "updated_at": order_row[7].isoformat(),
                "items": items
            }

            return json.dumps(order_detail, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to query order detail: {e}")
        return json.dumps({"error": str(e)})

@tool
async def query_user_info(user_id: str) -> str:
    """
    查询用户信息

    Args:
        user_id: 用户ID

    Returns:
        用户信息的JSON字符串
    """
    try:
        async with state_manager.async_session() as session:
            result = await session.execute(
                text("""
                    SELECT user_id, username, email, phone, 
                           member_level, total_orders, total_spent, created_at
                    FROM users 
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            )

            row = result.fetchone()
            if not row:
                return json.dumps({"error": "用户不存在"})

            user_info = {
                "user_id": row[0],
                "username": row[1],
                "email": row[2],
                "phone": row[3],
                "member_level": row[4],
                "total_orders": row[5],
                "total_spent": float(row[6]),
                "created_at": row[7].isoformat()
            }

            return json.dumps(user_info, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to query user info: {e}")
        return json.dumps({"error": str(e)})

# 导出工具列表
database_tools = [
    query_orders,
    query_order_detail,
    query_user_info
]
```

---

### **1.2.6 客服Agent (agents/customer_service.py)**

```python
# backend/app/agents/customer_service.py

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from typing import TypedDict, Annotated, Literal
import operator
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from ..config import settings
from ..tools.database_tools import database_tools
from ..tools.n8n_tools import n8n_tools
from ..services.state_manager import state_manager
from ..utils.logger import get_logger

logger = get_logger(__name__)

# 定义Agent状态
class CustomerServiceState(TypedDict):
    """客服Agent状态"""
    # 对话历史（累加）
    messages: Annotated[list, operator.add]

    # 用户信息
    user_id: str
    user_info: dict

    # 意图识别
    intent: str  # 如: query_order, complaint, refund, general_question
    emotion: str  # 如: neutral, happy, angry, frustrated

    # 查询结果
    query_results: dict

    # 工具使用记录（累加）
    tools_used: Annotated[list, operator.add]

    # 控制流
    needs_human: bool
    resolved: bool
    next_action: str

class CustomerServiceAgent:
    """客服Agent"""

    def __init__(self):
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            streaming=True,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

        # 工具
        self.tools = database_tools + n8n_tools
        self.tool_executor = ToolExecutor(self.tools)

        # 绑定工具到LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # 创建状态图
        self.graph = self._create_graph()

        logger.info("CustomerServiceAgent initialized")

    def _create_graph(self) -> StateGraph:
        """创建Agent状态图"""
        workflow = StateGraph(CustomerServiceState)

        # 添加节点
        workflow.add_node("understand", self._understand_intent)
        workflow.add_node("query_user_info", self._query_user_info)
        workflow.add_node("call_tools", self._call_tools)
        workflow.add_node("respond", self._generate_response)
        workflow.add_node("transfer_human", self._transfer_to_human)

        # 设置入口
        workflow.set_entry_point("understand")

        # 理解意图后的路由
        workflow.add_conditional_edges(
            "understand",
            self._route_after_understand,
            {
                "query_user": "query_user_info",
                "use_tools": "call_tools",
                "direct_response": "respond",
                "human": "transfer_human"
            }
        )

        # 查询用户信息后
        workflow.add_edge("query_user_info", "call_tools")

        # 工具调用后
        workflow.add_edge("call_tools", "respond")

        # 转人工后结束
        workflow.add_edge("transfer_human", END)

        # 响应后决定是否继续
        workflow.add_conditional_edges(
            "respond",
            self._should_continue,
            {
                "continue": "understand",
                "end": END
            }
        )

        # 编译图
        app = workflow.compile(
            checkpointer=state_manager.get_checkpointer()
        )

        return app

    def _understand_intent(self, state: CustomerServiceState) -> CustomerServiceState:
        """理解用户意图和情绪"""
        last_message = state["messages"][-1].content

        # 构建提示词
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""你是一个专业的客服意图识别助手。

分析用户消息，识别：
1. 意图（intent）: query_order(查询订单), complaint(投诉), refund(退款), general_question(一般问题), other(其他)
2. 情绪（emotion）: neutral(中性), happy(开心), angry(愤怒), frustrated(沮丧)
3. 是否需要人工（needs_human）: 如果用户明确要求人工，或情绪非常负面，则为true

以JSON格式返回：
{"intent": "...", "emotion": "...", "needs_human": false}
"""),
            HumanMessage(content=f"用户消息：{last_message}")
        ])

        try:
            response = self.llm.invoke(prompt.format_messages())
            import json
            analysis = json.loads(response.content)

            logger.info(f"Intent analysis: {analysis}")

            return {
                "intent": analysis.get("intent", "other"),
                "emotion": analysis.get("emotion", "neutral"),
                "needs_human": analysis.get("needs_human", False)
            }

        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return {
                "intent": "other",
                "emotion": "neutral",
                "needs_human": False
            }

    def _query_user_info(self, state: CustomerServiceState) -> CustomerServiceState:
        """查询用户信息"""
        user_id = state["user_id"]

        # 这里可以调用database_tools中的query_user_info
        # 为了演示```python
        # 为了演示，这里简化实现
        try:
            # 调用工具
            from ..tools.database_tools import query_user_info
            import json

            user_info_str = query_user_info.invoke({"user_id": user_id})
            user_info = json.loads(user_info_str)

            logger.info(f"User info retrieved: {user_info}")

            return {
                "user_info": user_info,
                "tools_used": ["query_user_info"]
            }

        except Exception as e:
            logger.error(f"Failed to query user info: {e}")
            return {
                "user_info": {},
                "tools_used": ["query_user_info"]
            }

    def _call_tools(self, state: CustomerServiceState) -> CustomerServiceState:
        """调用工具"""
        last_message = state["messages"][-1]

        # 让LLM决定使用哪些工具
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=f"""你是一个客服助手。当前用户意图是：{state['intent']}

用户信息：{state.get('user_info', {})}

对话历史：
{self._format_messages(state['messages'][:-1])}

用户最新消息：{last_message.content}

根据用户意图和消息，决定是否需要使用工具，以及使用哪些工具。
可用工具：查询订单、查询订单详情、生成报告、发送通知等。
"""),
            MessagesPlaceholder(variable_name="messages")
        ])

        try:
            # 调用带工具的LLM
            response = self.llm_with_tools.invoke(
                prompt.format_messages(messages=[last_message])
            )

            query_results = {}
            tools_called = []

            # 如果有工具调用
            if hasattr(response, "tool_calls") and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    logger.info(f"Calling tool: {tool_name} with args: {tool_args}")

                    # 执行工具
                    from langchain.tools import ToolInvocation
                    tool_invocation = ToolInvocation(
                        tool=tool_name,
                        tool_input=tool_args
                    )

                    tool_result = self.tool_executor.invoke(tool_invocation)
                    query_results[tool_name] = tool_result
                    tools_called.append(tool_name)

            return {
                "query_results": query_results,
                "tools_used": tools_called
            }

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                "query_results": {"error": str(e)},
                "tools_used": []
            }

    def _generate_response(self, state: CustomerServiceState) -> CustomerServiceState:
        """生成回复"""
        # 构建上下文
        context_parts = []

        if state.get("user_info"):
            context_parts.append(f"用户信息：{state['user_info']}")

        if state.get("query_results"):
            context_parts.append(f"查询结果：{state['query_results']}")

        context = "\n".join(context_parts)

        # 构建提示词
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=f"""你是一个专业、友好的客服助手。

当前情况：
- 用户意图：{state['intent']}
- 用户情绪：{state['emotion']}
- 使用的工具：{state.get('tools_used', [])}

{context}

根据以上信息，生成一个专业、有帮助的回复。
如果问题已解决，在回复中自然地询问是否还有其他需要帮助的。
如果问题未解决，引导用户提供更多信息或建议其他解决方案。
"""),
            MessagesPlaceholder(variable_name="history"),
            HumanMessage(content=state["messages"][-1].content)
        ])

        try:
            # 生成回复
            response = self.llm.invoke(
                prompt.format_messages(
                    history=state["messages"][:-1]
                )
            )

            # 判断问题是否解决
            resolved = self._check_if_resolved(response.content, state)

            logger.info(f"Response generated, resolved: {resolved}")

            return {
                "messages": [AIMessage(content=response.content)],
                "resolved": resolved
            }

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {
                "messages": [AIMessage(content="抱歉，我遇到了一些问题。请稍后再试或联系人工客服。")],
                "resolved": False
            }

    def _transfer_to_human(self, state: CustomerServiceState) -> CustomerServiceState:
        """转接人工"""
        message = """好的，我正在为您转接人工客服。

由于以下原因需要人工介入：
- 用户情绪：{emotion}
- 问题类型：{intent}

请稍等片刻，客服人员会尽快为您服务。""".format(
            emotion=state["emotion"],
            intent=state["intent"]
        )

        logger.info(f"Transferring to human for user {state['user_id']}")

        # 这里可以调用n8n工作流通知人工客服
        # await n8n_toolkit.send_notification(...)

        return {
            "messages": [AIMessage(content=message)],
            "resolved": True  # 转人工视为已处理
        }

    # 路由函数
    def _route_after_understand(
        self, 
        state: CustomerServiceState
    ) -> Literal["query_user", "use_tools", "direct_response", "human"]:
        """理解意图后的路由决策"""

        # 如果需要人工
        if state.get("needs_human", False):
            return "human"

        # 如果还没有用户信息，先查询
        if not state.get("user_info"):
            return "query_user"

        # 如果意图需要工具
        if state["intent"] in ["query_order", "refund", "complaint"]:
            return "use_tools"

        # 一般问题，直接回复
        return "direct_response"

    def _should_continue(
        self, 
        state: CustomerServiceState
    ) -> Literal["continue", "end"]:
        """决定是否继续对话"""
        if state.get("resolved", False):
            return "end"
        return "continue"

    # 辅助函数
    def _format_messages(self, messages: list) -> str:
        """格式化消息历史"""
        formatted = []
        for msg in messages:
            role = "用户" if isinstance(msg, HumanMessage) else "客服"
            formatted.append(f"{role}: {msg.content}")
        return "\n".join(formatted)

    def _check_if_resolved(self, response: str, state: CustomerServiceState) -> bool:
        """检查问题是否解决"""
        # 简单的启发式判断
        # 实际应用中可以让LLM判断

        # 如果情绪负面且没有明确解决方案，认为未解决
        if state["emotion"] in ["angry", "frustrated"]:
            if not state.get("query_results") or "error" in str(state.get("query_results", {})):
                return False

        # 如果回复中包含"还有其他"等结束语，认为已解决
        end_phrases = ["还有其他", "还需要", "帮助到您", "为您服务"]
        if any(phrase in response for phrase in end_phrases):
            return True

        # 默认未解决，继续对话
        return False

    async def run(
        self,
        user_message: str,
        user_id: str,
        conversation_id: str,
        stream: bool = True
    ):
        """运行Agent"""

        # 构建配置
        config = {
            "configurable": {
                "thread_id": conversation_id
            }
        }

        # 初始状态
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "user_id": user_id,
            "user_info": {},
            "intent": "",
            "emotion": "",
            "query_results": {},
            "tools_used": [],
            "needs_human": False,
            "resolved": False,
            "next_action": ""
        }

        if stream:
            # 流式输出
            async for event in self.graph.astream_events(
                initial_state,
                config,
                version="v1"
            ):
                yield event
        else:
            # 非流式
            result = await self.graph.ainvoke(initial_state, config)
            yield result

# 创建全局实例
customer_service_agent = CustomerServiceAgent()
```

---

### **1.2.7 FastAPI主应用 (main.py)**

```python
# backend/app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import json
import asyncio
from typing import AsyncGenerator
import uvicorn

from .config import settings
from .services.state_manager import state_manager
from .agents.customer_service import customer_service_agent
from .utils.logger import get_logger
from .utils.metrics import metrics_middleware

logger = get_logger(__name__)

# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting Agent Platform...")
    await state_manager.initialize()
    logger.info("Agent Platform started successfully")

    yield

    # 关闭时
    logger.info("Shutting down Agent Platform...")
    # 清理资源
    logger.info("Agent Platform shut down")

# 创建应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 监控中间件
if settings.ENABLE_METRICS:
    app.middleware("http")(metrics_middleware)

# WebSocket连接管理
class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

manager = ConnectionManager()

# API路由
@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

@app.get("/health")
async def health_check():
    """详细健康检查"""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "services": {
            "customer_service_agent": "ready"
        }
    }

@app.websocket("/ws/chat/{user_id}/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    user_id: str,
    conversation_id: str
):
    """WebSocket聊天端点"""
    client_id = f"{user_id}_{conversation_id}"

    await manager.connect(websocket, client_id)

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            message = data.get("message", "")
            agent_type = data.get("agent_type", "customer_service")

            logger.info(f"Received message from {client_id}: {message[:50]}...")

            # 发送处理开始通知
            await manager.send_message(client_id, {
                "type": "processing_start",
                "timestamp": asyncio.get_event_loop().time()
            })

            # 选择Agent
            if agent_type == "customer_service":
                agent = customer_service_agent
            else:
                await manager.send_message(client_id, {
                    "type": "error",
                    "message": f"Unknown agent type: {agent_type}"
                })
                continue

            # 运行Agent（流式）
            try:
                async for event in agent.run(
                    user_message=message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    stream=True
                ):
                    # 处理不同类型的事件
                    event_type = event.get("event")

                    if event_type == "on_chat_model_stream":
                        # LLM流式输出
                        chunk = event["data"]["chunk"]
                        await manager.send_message(client_id, {
                            "type": "token",
                            "content": chunk.content,
                            "timestamp": asyncio.get_event_loop().time()
                        })

                    elif event_type == "on_tool_start":
                        # 工具调用开始
                        await manager.send_message(client_id, {
                            "type": "tool_start",
                            "tool": event["name"],
                            "timestamp": asyncio.get_event_loop().time()
                        })

                    elif event_type == "on_tool_end":
                        # 工具调用结束
                        await manager.send_message(client_id, {
                            "type": "tool_end",
                            "tool": event["name"],
                            "result": str(event["data"]["output"])[:200],  # 截断长结果
                            "timestamp": asyncio.get_event_loop().time()
                        })

                    elif event_type == "on_chain_start":
                        # 节点开始
                        await manager.send_message(client_id, {
                            "type": "node_start",
                            "node": event["name"],
                            "timestamp": asyncio.get_event_loop().time()
                        })

                    elif event_type == "on_chain_end":
                        # 节点结束
                        await manager.send_message(client_id, {
                            "type": "node_end",
                            "node": event["name"],
                            "timestamp": asyncio.get_event_loop().time()
                        })

                # 发送完成通知
                await manager.send_message(client_id, {
                    "type": "processing_end",
                    "timestamp": asyncio.get_event_loop().time()
                })

            except Exception as e:
                logger.error(f"Agent execution error: {e}", exc_info=True)
                await manager.send_message(client_id, {
                    "type": "error",
                    "message": str(e),
                    "timestamp": asyncio.get_event_loop().time()
                })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(client_id)

@app.post("/api/v1/chat")
async def http_chat(
    user_id: str,
    conversation_id: str,
    message: str,
    agent_type: str = "customer_service",
    stream: bool = False
):
    """HTTP聊天端点（支持流式和非流式）"""

    # 选择Agent
    if agent_type == "customer_service":
        agent = customer_service_agent
    else:
        raise HTTPException(status_code=400, detail=f"Unknown agent type: {agent_type}")

    if stream:
        # 流式响应
        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                async for event in agent.run(
                    user_message=message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    stream=True
                ):
                    # 只发送token事件
                    if event.get("event") == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        yield f"data: {json.dumps({'content': chunk.content})}\n\n"

                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )

    else:
        # 非流式响应
        try:
            result = None
            async for event in agent.run(
                user_message=message,
                user_id=user_id,
                conversation_id=conversation_id,
                stream=False
            ):
                result = event

            if result:
                # 提取最后一条AI消息
                ai_messages = [
                    msg for msg in result.get("messages", [])
                    if hasattr(msg, "type") and msg.type == "ai"
                ]

                if ai_messages:
                    return {
                        "response": ai_messages[-1].content,
                        "resolved": result.get("resolved", False),
                        "tools_used": result.get("tools_used", [])
                    }

            return {
                "response": "抱歉，处理出现问题",
                "resolved": False,
                "tools_used": []
            }

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    limit: int = 50
):
    """获取对话历史"""
    try:
        checkpoints = await state_manager.list_checkpoints(conversation_id, limit)
        return {
            "conversation_id": conversation_id,
            "checkpoints": checkpoints
        }
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/conversations/{conversation_id}/rollback")
async def rollback_conversation(
    conversation_id: str,
    step: int
):
    """回滚对话到指定步骤"""
    try:
        # LangGraph支持从任意检查点恢复
        # 这里简化实现
        return {
            "conversation_id": conversation_id,
            "rolled_back_to_step": step,
            "message": "对话已回滚"
        }
    except Exception as e:
        logger.error(f"Failed to rollback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 启动应用
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
```

---

### **1.2.8 日志工具 (utils/logger.py)**

```python
# backend/app/utils/logger.py

import logging
import sys
from pathlib import Path
import json
from datetime import datetime
from typing import Any, Dict
from ..config import settings

class JSONFormatter(logging.Formatter):
    """JSON格式日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data, ensure_ascii=False)

def get_logger(name: str) -> logging.Logger:
    """获取logger"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)

        if settings.LOG_FORMAT == "json":
            console_handler.setFormatter(JSONFormatter())
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

        # 文件处理器（生产环境）
        if not settings.DEBUG:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)

            file_handler = logging.FileHandler(
                log_dir / f"{name}.log",
                encoding="utf-8"
            )
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)

    return logger
```

---

### **1.2.9 监控指标 (utils/metrics.py)**

```python
# backend/app/utils/metrics.py

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request, Response
import time
from typing import Callable
from .logger import get_logger

logger = get_logger(__name__)

# 定义指标
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

agent_execution_count = Counter(
    'agent_executions_total',
    'Total agent executions',
    ['agent_type', 'status']
)

agent_execution_duration = Histogram(
    'agent_execution_duration_seconds',
    'Agent execution duration',
    ['agent_type']
)

tool_call_count = Counter(
    'tool_calls_total',
    'Total tool calls',
    ['tool_name', 'status']
)

active_connections = Gauge(
    'active_websocket_connections',
    'Active WebSocket connections'
)

llm_token_usage = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'type']  # type: input/output
)

async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """监控中间件"""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time

    # 记录指标
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response

def get_metrics():
    """获取Prometheus指标"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

---

### **1.2.10 Docker配置**

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "app.main"]
```

```yaml
# backend/docker-compose.yml

version: '3.8'

services:
  # 后端API
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_USER=agent_user
      - POSTGRES_PASSWORD=agent_password
      - POSTGRES_DB=agent_platform
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  # PostgreSQL数据库
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=agent_user
      - POSTGRES_PASSWORD=agent_password
      - POSTGRES_DB=agent_platform
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # Qdrant向量数据库（可选）
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  # Prometheus监控（可选）
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    restart: unless-stopped

  # Grafana可视化（可选）
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  prometheus_data:
  grafana_data:
```

---

### **1.2.11 数据库初始化 (init.sql)**

```sql
-- backend/init.sql

-- 创建对话表
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    agent_type VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0
);

CREATE INDEX idx_user_created ON conversations(user_id, created_at);
CREATE INDEX idx_status ON conversations(status);

-- 创建消息表
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversation_created ON messages(conversation_id, created_at);

-- 创建Agent检查点表
CREATE TABLE IF NOT EXISTS agent_checkpoints (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    checkpoint_data JSONB NOT NULL,
    checkpoint_namespace VARCHAR(255) NOT NULL,
    step INTEGER NOT NULL,
    node_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversation_step ON agent_checkpoints(conversation_id, step);

-- 创建用户表（示例）
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    member_level VARCHAR(50) DEFAULT 'regular',
    total_orders INTEGER DEFAULT 0,
    total_spent DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建订单表（示例）
CREATE TABLE IF NOT EXISTS orders (
    order_id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES users(user_id),
    status VARCHAR(50) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    shipping_address TEXT,
    tracking_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_orders ON orders(user_id, created_at);

-- 创建订单商品表（示例）
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY,```sql
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_order_items ON order_items(order_id);

-- 插入示例数据
INSERT INTO users (user_id, username, email, phone, member_level, total_orders, total_spent) VALUES
('user001', '张三', 'zhangsan@example.com', '13800138000', 'vip', 15, 5680.50),
('user002', '李四', 'lisi@example.com', '13900139000', 'regular', 3, 890.00)
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO orders (order_id, user_id, status, total_amount, shipping_address, tracking_number, created_at) VALUES
('order001', 'user001', 'delivered', 299.00, '北京市朝阳区xxx街道', 'SF1234567890', '2024-01-15 10:30:00'),
('order002', 'user001', 'shipped', 599.00, '北京市朝阳区xxx街道', 'SF1234567891', '2024-01-20 14:20:00')
ON CONFLICT (order_id) DO NOTHING;
```

---

### **1.2.12 依赖文件 (requirements.txt)**

```txt
# backend/requirements.txt

# 核心框架
fastapi==0.109.0
uvicorn[standard]==0.27.0
websockets==12.0

# LangChain生态
langgraph==0.2.16
langchain==0.1.6
langchain-openai==0.0.5
langchain-community==0.0.16

# 数据库
sqlalchemy==2.0.25
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.1

# Redis
redis==5.0.1
aioredis==2.0.1

# 向量数据库
qdrant-client==1.7.3

# 监控
prometheus-client==0.19.0

# 工具
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
aiohttp==3.9.1
httpx==0.26.0

# 日志
python-json-logger==2.0.7

# 测试
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
httpx==0.26.0

# 开发工具
black==24.1.1
flake8==7.0.0
mypy==1.8.0
```

---

### **1.2.13 环境变量配置 (.env.example)**

```bash
# backend/.env.example

# 应用配置
APP_NAME=Agent Platform
APP_VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO
LOG_FORMAT=json

# API配置
API_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:3000,https://your-domain.com

# OpenAI配置
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1

# 或使用其他LLM
# ANTHROPIC_API_KEY=sk-ant-xxx

# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=agent_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=agent_platform

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# n8n配置
N8N_BASE_URL=https://your-n8n.com
N8N_API_KEY=your_n8n_api_key

# 向量数据库配置
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=

# 性能配置
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=300
STREAM_CHUNK_SIZE=1024

# 监控配置
ENABLE_METRICS=True
METRICS_PORT=9090
```

---

### **1.2.14 OpenWebUI前端集成示例**

```javascript
// frontend/src/lib/apis/streaming.js

/**
 * WebSocket聊天连接
 */
export class AgentWebSocket {
  constructor(userId, conversationId) {
    this.userId = userId;
    this.conversationId = conversationId;
    this.ws = null;
    this.callbacks = {
      onToken: null,
      onToolStart: null,
      onToolEnd: null,
      onNodeStart: null,
      onNodeEnd: null,
      onError: null,
      onComplete: null
    };
  }

  connect(baseUrl = 'ws://localhost:8000') {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(
        `${baseUrl}/ws/chat/${this.userId}/${this.conversationId}`
      );

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (this.callbacks.onError) {
          this.callbacks.onError(error);
        }
        reject(error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket closed');
      };
    });
  }

  handleMessage(data) {
    switch (data.type) {
      case 'token':
        if (this.callbacks.onToken) {
          this.callbacks.onToken(data.content);
        }
        break;

      case 'tool_start':
        if (this.callbacks.onToolStart) {
          this.callbacks.onToolStart(data.tool);
        }
        break;

      case 'tool_end':
        if (this.callbacks.onToolEnd) {
          this.callbacks.onToolEnd(data.tool, data.result);
        }
        break;

      case 'node_start':
        if (this.callbacks.onNodeStart) {
          this.callbacks.onNodeStart(data.node);
        }
        break;

      case 'node_end':
        if (this.callbacks.onNodeEnd) {
          this.callbacks.onNodeEnd(data.node);
        }
        break;

      case 'processing_start':
        console.log('Agent processing started');
        break;

      case 'processing_end':
        if (this.callbacks.onComplete) {
          this.callbacks.onComplete();
        }
        break;

      case 'error':
        if (this.callbacks.onError) {
          this.callbacks.onError(new Error(data.message));
        }
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  }

  sendMessage(message, agentType = 'customer_service') {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        message,
        agent_type: agentType
      }));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  on(event, callback) {
    this.callbacks[event] = callback;
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

/**
 * 使用示例
 */
export async function exampleUsage() {
  const ws = new AgentWebSocket('user123', 'conv456');

  // 设置回调
  let currentMessage = '';

  ws.on('onToken', (token) => {
    currentMessage += token;
    console.log('Current message:', currentMessage);
    // 更新UI显示
    updateChatUI(currentMessage);
  });

  ws.on('onToolStart', (tool) => {
    console.log('Tool started:', tool);
    // 显示工具调用状态
    showToolStatus(tool, 'running');
  });

  ws.on('onToolEnd', (tool, result) => {
    console.log('Tool completed:', tool, result);
    // 更新工具状态
    showToolStatus(tool, 'completed');
  });

  ws.on('onComplete', () => {
    console.log('Message complete');
    // 清理状态
    currentMessage = '';
  });

  ws.on('onError', (error) => {
    console.error('Error:', error);
    // 显示错误提示
    showError(error.message);
  });

  // 连接
  await ws.connect();

  // 发送消息
  ws.sendMessage('我的订单什么时候到？');
}
```

```javascript
// frontend/src/lib/components/ChatInterface.svelte

<script>
  import { onMount, onDestroy } from 'svelte';
  import { AgentWebSocket } from '$lib/apis/streaming';

  export let userId;
  export let conversationId;

  let messages = [];
  let currentMessage = '';
  let inputMessage = '';
  let ws = null;
  let isProcessing = false;
  let activeTools = [];

  onMount(async () => {
    // 初始化WebSocket
    ws = new AgentWebSocket(userId, conversationId);

    // 设置回调
    ws.on('onToken', handleToken);
    ws.on('onToolStart', handleToolStart);
    ws.on('onToolEnd', handleToolEnd);
    ws.on('onComplete', handleComplete);
    ws.on('onError', handleError);

    // 连接
    try {
      await ws.connect();
    } catch (error) {
      console.error('Failed to connect:', error);
    }
  });

  onDestroy(() => {
    if (ws) {
      ws.disconnect();
    }
  });

  function handleToken(token) {
    currentMessage += token;
    // 触发UI更新
    messages = [...messages];
  }

  function handleToolStart(tool) {
    activeTools = [...activeTools, { name: tool, status: 'running' }];
  }

  function handleToolEnd(tool, result) {
    activeTools = activeTools.map(t => 
      t.name === tool ? { ...t, status: 'completed', result } : t
    );
  }

  function handleComplete() {
    if (currentMessage) {
      messages = [...messages, {
        role: 'assistant',
        content: currentMessage,
        timestamp: new Date()
      }];
      currentMessage = '';
    }
    isProcessing = false;
    activeTools = [];
  }

  function handleError(error) {
    console.error('Chat error:', error);
    isProcessing = false;
    // 显示错误消息
    messages = [...messages, {
      role: 'system',
      content: `错误: ${error.message}`,
      timestamp: new Date(),
      isError: true
    }];
  }

  function sendMessage() {
    if (!inputMessage.trim() || isProcessing) return;

    // 添加用户消息
    messages = [...messages, {
      role: 'user',
      content: inputMessage,
      timestamp: new Date()
    }];

    // 发送消息
    ws.sendMessage(inputMessage);

    // 清空输入
    inputMessage = '';
    isProcessing = true;
    currentMessage = '';
  }
</script>

<div class="chat-container">
  <!-- 消息列表 -->
  <div class="messages">
    {#each messages as message}
      <div class="message {message.role}" class:error={message.isError}>
        <div class="message-avatar">
          {#if message.role === 'user'}
            👤
          {:else if message.role === 'assistant'}
            🤖
          {:else}
            ⚠️
          {/if}
        </div>
        <div class="message-content">
          <div class="message-text">{message.content}</div>
          <div class="message-time">
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      </div>
    {/each}

    <!-- 当前正在生成的消息 -->
    {#if currentMessage}
      <div class="message assistant streaming">
        <div class="message-avatar">🤖</div>
        <div class="message-content">
          <div class="message-text">{currentMessage}<span class="cursor">▊</span></div>
        </div>
      </div>
    {/if}

    <!-- 工具调用状态 -->
    {#if activeTools.length > 0}
      <div class="tools-status">
        {#each activeTools as tool}
          <div class="tool-item {tool.status}">
            <span class="tool-icon">
              {#if tool.status === 'running'}
                ⏳
              {:else}
                ✅
              {/if}
            </span>
            <span class="tool-name">{tool.name}</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <!-- 输入框 -->
  <div class="input-container">
    <input
      type="text"
      bind:value={inputMessage}
      on:keypress={(e) => e.key === 'Enter' && sendMessage()}
      placeholder="输入消息..."
      disabled={isProcessing}
    />
    <button 
      on:click={sendMessage}
      disabled={isProcessing || !inputMessage.trim()}
    >
      {isProcessing ? '处理中...' : '发送'}
    </button>
  </div>
</div>

<style>
  .chat-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 800px;
    margin: 0 auto;
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    background: #f5f5f5;
  }

  .message {
    display: flex;
    margin-bottom: 20px;
    animation: fadeIn 0.3s;
  }

  .message.user {
    flex-direction: row-reverse;
  }

  .message-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    margin: 0 10px;
  }

  .message-content {
    max-width: 70%;
    background: white;
    padding: 12px 16px;
    border-radius: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }

  .message.user .message-content {
    background: #007bff;
    color: white;
  }

  .message.streaming .message-text {
    position: relative;
  }

  .cursor {
    animation: blink 1s infinite;
  }

  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }

  .tools-status {
    display: flex;
    gap: 10px;
    padding: 10px;
    background: rgba(0, 123, 255, 0.1);
    border-radius: 8px;
    margin: 10px 0;
  }

  .tool-item {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    background: white;
    border-radius: 4px;
    font-size: 14px;
  }

  .input-container {
    display: flex;
    padding: 20px;
    background: white;
    border-top: 1px solid #ddd;
  }

  input {
    flex: 1;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 16px;
  }

  button {
    margin-left: 10px;
    padding: 12px 24px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 16px;
  }

  button:disabled {
    background: #ccc;
    cursor: not-allowed;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
```

---

## 1.3 测试代码

### **1.3.1 Agent测试 (tests/test_agents.py)**

```python
# backend/tests/test_agents.py

import pytest
import asyncio
from app.agents.customer_service import customer_service_agent, CustomerServiceState
from langchain.schema import HumanMessage

@pytest.mark.asyncio
async def test_simple_question():
    """测试简单问答"""
    result = None
    async for event in customer_service_agent.run(
        user_message="你好，你能做什么？",
        user_id="test_user",
        conversation_id="test_conv_1",
        stream=False
    ):
        result = event

    assert result is not None
    assert "messages" in result
    assert len(result["messages"]) > 0

@pytest.mark.asyncio
async def test_order_query():
    """测试订单查询"""
    result = None
    async for event in customer_service_agent.run(
        user_message="我想查询我的订单",
        user_id="user001",
        conversation_id="test_conv_2",
        stream=False
    ):
        result = event

    assert result is not None
    assert "query_results" in result or "tools_used" in result

@pytest.mark.asyncio
async def test_multi_turn_conversation():
    """测试多轮对话"""
    conversation_id = "test_conv_3"

    # 第一轮
    result1 = None
    async for event in customer_service_agent.run(
        user_message="我的订单号是order001",
        user_id="user001",
        conversation_id=conversation_id,
        stream=False
    ):
        result1 = event

    assert result1 is not None

    # 第二轮（应该记住上下文）
    result2 = None
    async for event in customer_service_agent.run(
        user_message="什么时候能到？",
        user_id="user001",
        conversation_id=conversation_id,
        stream=False
    ):
        result2 = event

    assert result2 is not None
    # 应该能理解"它"指的是order001

@pytest.mark.asyncio
async def test_transfer_to_human():
    """测试转人工"""
    result = None
    async for event in customer_service_agent.run(
        user_message="我要投诉！你们太差劲了！",
        user_id="test_user",
        conversation_id="test_conv_4",
        stream=False
    ):
        result = event

    assert result is not None
    assert result.get("needs_human", False) or "人工" in str(result.get("messages", []))

@pytest.mark.asyncio
async def test_streaming():
    """测试流式输出"""
    tokens = []

    async for event in customer_service_agent.run(
        user_message="介绍一下你们的服务",
        user_id="test_user",
        conversation_id="test_conv_5",
        stream=True
    ):
        if event.get("event") == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            tokens.append(chunk.content)

    assert len(tokens) > 0
    full_response = "".join(tokens)
    assert len(full_response) > 0
```

---

### **1.3.2 API测试 (tests/test_api.py)**

```python
# backend/tests/test_api.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_http_chat_non_stream():
    """测试HTTP非流式聊天"""
    response = client.post(
        "/api/v1/chat",
        params={
            "user_id": "test_user",
            "conversation_id": "test_conv",
            "message": "你好",
            "stream": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data

def test_http_chat_stream():
    """测试HTTP流式聊天"""
    response = client.post(
        "/api/v1/chat",
        params={
            "user_id": "test_user",
            "conversation_id": "test_conv",
            "message": "你好",
            "stream": True
        }
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

def test_get_conversation_history():
    """测试获取对话历史"""
    response = client.get("/api/v1/conversations/test_conv/history")
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
```

---

# 二、详细技术方案文档

## 2.1 技术方案概述

### **2.1.1 项目背景**

```markdown
# Agent平台技术升级方案

## 当前架构问题
1. **性能瓶颈**
   - 平均响应时间：8-30秒
   - 用户体验：不可接受
   - 原因：n8n工作流引擎开销大

2. **上下文管理缺陷**
   - 对话限制：20-50轮
   - 需要人工切割任务
   - 关键信息容易丢失

3. **技术债务**
   - n8n不支持流式输出
   - 复杂的外部状态管理
   - 维护成本高

## 升级目标
1. **性能提升**
   - 响应时间：< 2秒（P50）
   - 首token时间：< 800ms
   - 吞吐量：> 100 QPS

2. **用户体验改善**
   - 流式输出
   - 实时工具调用反馈
   - 无限制的上下文长度

3. **系统稳定性**
   - 可用性：99.9%
   - 易于维护和扩展
   - 完善的监控和告警
```

---

### **2.1.2 技术选型对比**

```markdown
## 核心技术栈选型

### Agent框架：LangGraph ✅

**选择理由：**
1. 专为复杂Agent设计
2. 强大的状态管理
3. 原生流式支持
4. 活跃的社区和持续更新
5. 与LangChain生态无缝集成

**替代方案对比：**
| 框架 | 优势 | 劣势 | 适用性 |
|------|-----|------|--------|
| LangGraph | 功能最强，灵活性高 | 学习曲线中等 | ⭐⭐⭐⭐⭐ |
| AutoGen | 多Agent协作好 | 单Agent性能一般 | ⭐⭐⭐ |
| CrewAI | 轻量，快速上手 | 功能相对基础 | ⭐⭐⭐⭐ |

### 后端框架：FastAPI ✅

**选择理由：**
1. 原生异步支持
2. 自动API文档
3. 高性能（与Node.js相当）
4. 完善的类型检查
5. WebSocket支持良好

### 数据库：PostgreSQL ✅

**选择理由：**
1. JSONB支持（存储状态检查点）
2. 成熟稳定
3. 丰富的索引类型
4. 与LangGraph原生集成

**状态存储设计：**
```sql
-- 检查点表结构
CREATE TABLE agent_checkpoints (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL,
    checkpoint_data JSONB NOT NULL,  -- 完整状态
    step INTEGER NOT NULL,            -- 执行步骤
    created_at TIMESTAMP DEFAULT NOW()
);

-- 利用PostgreSQL的JSONB索引
CREATE INDEX idx_checkpoint_data ON agent_checkpoints USING gin(checkpoint_data);
```

### 缓存层：Redis ✅

**使用场景：**

1. LLM响应缓存（减少成本）
2. 用户会话管理
3. 实时状态共享
4. 任务队列（后台任务）

**缓存策略：**

```python
# LLM响应缓存
cache_key = f"llm:{hash(prompt)}:{model}"
ttl = 3600  # 1小时

# 用户会话缓存
session_key = f"session:{user_id}:{conversation_id}"
ttl = 1800  # 30分钟
```

### 向量数据库：Qdrant（可选）✅

**使用场景：**

1. 长期记忆存储
2. RAG应用
3. 语义搜索

**集成方案：**

```python
from langchain.vectorstores import Qdrant
from langchain.embeddings import OpenAIEmbeddings

# 作为LangGraph的工具
@tool
async def search_knowledge_base(query: str) -> str:
    """搜索知识库"""
    vectorstore = Qdrant(...)
    results = vectorstore.similarity_search(query, k=3)
    return format_results(results)
```

```
---

### **2.1.3 系统架构设计**

```markdown
## 整体架构
```

┌─────────────────────────────────────────────────────────────┐
│                         用户层                                │
├─────────────────────────────────────────────────────────────┤
│  OpenWebUI (React/Svelte)                                    │
│  - 流式消息展示                                               │
│  - 工具调用可视化                                             │
│  - 对话历史管理                                               │
└────────────────┬────────────────────────────────────────────┘
                 │ WebSocket / HTTP
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      API网关层                                │
├─────────────────────────────────────────────────────────────┤
│  FastAPI                                                      │
│  - WebSocket管理                                              │
│  - 请求路由                                                   │
│  - 认证授权                                                   │
│  - 限流熔断                                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     Agent编排层                               │
├─────────────────────────────────────────────────────────────┤
│  LangGraph State Machine                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Customer Service Agent                               │  │
│  │  ├─ understand_intent                                 │  │
│  │  ├─ query_user_info                                   │  │
│  │  ├─ call_tools                                        │  │
│  │  └─ generate_response                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Data Analyst Agent                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Code Assistant Agent                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼             ▼
┌─────────┐ ┌─────────┐ ┌──────────┐
│  LLM    │ │  Tools  │ │  Memory  │
│ Provider│ │         │ │          │
├─────────┤ ├─────────┤ ├──────────┤
│ OpenAI  │ │Database │ │PostgreSQL│
│Anthropic│ │ n8n API │ │  Qdrant  │
│  Local  │ │  APIs   │ │  Redis   │
└─────────┘ └─────────┘ └──────────┘

```
## 数据流设计

### 1. 实时对话流程
```

用户输入
  │
  ├─> WebSocket → FastAPI
  │                 │
  │                 ├─> 验证用户身份
  │                 ├─> 创建/恢复对话上下文
  │                 │
  │                 └─> LangGraph Agent
  │                       │
  │                       ├─> 状态初始化
  │                       │   └─> 从PostgreSQL加载检查点
  │                       │
  │                       ├─> 执行节点（循环）
  │                       │   ├─> understand_intent
  │                       │   │   └─> LLM调用
  │                       │   │       └─> 流式输出 token
  │                       │   │           └─> WebSocket推送
  │                       │   │
  │                       │   ├─> call_tools
  │                       │   │   ├─> 数据库查询
  │                       │   │   ├─> n8n工作流
  │                       │   │   └─> 第三方API
  │                       │   │       └─> WebSocket推送工具状态
  │                       │   │
  │                       │   └─> generate_response
  │                       │       └─> LLM生成
  │                       │           └─> 流式输出
  │                       │
  │                       └─> 保存检查点
  │                           └─> PostgreSQL
  │
  └─> 用户收到实时反馈

```
### 2. 状态持久化流程

```python
# 每个节点执行后自动保存
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    user_id: str
    intent: str
    query_results: dict
    # ... 其他状态字段

# LangGraph自动处理
workflow.compile(
    checkpointer=PostgresSaver(engine)  # 自动保存到PostgreSQL
)

# 状态演变
Step 0: {"messages": ["用户: 查询订单"], "intent": ""}
  ↓ understand_intent
Step 1: {"messages": ["用户: 查询订单"], "intent": "query_order"}
  ↓ call_tools
Step 2: {"messages": ["用户: 查询订单"], "intent": "query_order", 
         "query_results": {"order_id": "..."}}
  ↓ generate_response
Step 3: {"messages": ["用户: 查询订单", "助手: 您的订单..."], 
         "intent": "query_order", "query_results": {...}}
```

### 3. 多Agent协作流程（高级场景）

```
用户: "分析上个月的销售数据并生成报告"
  │
  ├─> Router Agent（路由）
  │     └─> 判断需要多个Agent协作
  │
  ├─> Data Analyst Agent
  │     ├─> 查询数据库
  │     ├─> 数据分析
  │     └─> 生成洞察
  │         └─> 保存到共享状态
  │
  ├─> Report Generator Agent
  │     ├─> 读取分析结果
  │     ├─> 调用n8n生成PDF
  │     └─> 返回下载链接
  │
  └─> 用户收到报告
```

```
---

### **2.1.4 核心功能设计**

```markdown
## 1. 流式输出实现

### 技术方案：Server-Sent Events (SSE) + WebSocket

**WebSocket实现（推荐）：**
```python
@app.websocket("/ws/chat/{user_id}/{conversation_id}")
async def websocket_chat(websocket: WebSocket, user_id: str, conversation_id: str):
    await websocket.accept()

    async for event in agent.astream_events(input_data, config):
        if event["event"] == "on_chat_model_stream":
            # 实时发送token
            await websocket.send_json({
                "type": "token",
                "content": event["data"]["chunk"].content
            })
```

**优势：**

- 双向通信
- 低延迟
- 自动重连机制
- 更好的用户体验

**前端接收：**

```javascript
const ws = new WebSocket('ws://api.example.com/ws/chat/user123/conv456');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'token') {
        appendToken(data.content);  // 实时显示
    }
};
```

## 2. 上下文管理

### 长期记忆架构

```python
class MemoryManager:
    """记忆管理器"""

    def __init__(self):
        self.vectorstore = Qdrant(...)  # 长期记忆
        self.redis = Redis(...)         # 短期缓存
        self.postgres = PostgreSQL(...) # 结构化存储

    async def store_conversation(self, conversation_id: str, messages: list):
        """存储对话"""
        # 1. 完整对话存入PostgreSQL
        await self.postgres.save(conversation_id, messages)

        # 2. 重要信息提取后存入向量库
        important_facts = await self.extract_facts(messages)
        await self.vectorstore.add_documents(important_facts)

        # 3. 最近N条消息缓存到Redis（快速访问）
        await self.redis.set(
            f"recent:{conversation_id}",
            messages[-20:],  # 最近20条
            ex=3600
        )

    async def retrieve_context(self, conversation_id: str, query: str):
        """检索上下文"""
        # 1. 从Redis获取最近对话
        recent = await self.redis.get(f"recent:{conversation_id}")

        # 2. 从向量库语义搜索相关记忆
        relevant = await self.vectorstore.similarity_search(query, k=5)

        # 3. 组合上下文
        context = {
            "recent_messages": recent,
            "relevant_memories": relevant
        }

        return context
```

### 智能摘要机制

```python
async def summarize_context(messages: list, max_length: int = 2000):
    """智能压缩对话历史"""

    if len(str(messages)) < max_length:
        return messages

    # 1. 保留最近的对话
    recent_messages = messages[-5:]

    # 2. 对之前的对话进行摘要
    older_messages = messages[:-5]

    summary_prompt = f"""
    总结以下对话的关键信息：
    {older_messages}

    要求：
    1. 保留所有重要的事实和数据
    2. 保留用户的关键需求
    3. 删除冗余信息
    4. 压缩到200字以内
    """

    summary = await llm.ainvoke(summary_prompt)

    # 3. 组合
    compressed_context = [
        {"role": "system", "content": f"对话摘要：{summary}"}
    ] + recent_messages

    return compressed_context
```

## 3. 工具调用管理

### 工具注册系统

```python
class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self.tools = {}
        self.categories = {
            "database": [],
            "api": [],
            "n8n": [],
            "computation": []
        }

    def register(self, category: str):
        """装饰器：注册工具"""
        def decorator(func):
            tool_instance = tool(func)
            self.tools[func.__name__] = tool_instance
            self.categories[category].append(tool_instance)
            return tool_instance
        return decorator

    def get_tools_by_category(self, category: str):
        """按类别获取工具"""
        return self.categories.get(category, [])

    def get_all_tools(self):
        """获取所有工具"""
        return list(self.tools.values())

# 使用示例
registry = ToolRegistry()

@registry.register("database")
@tool
async def query_orders(user_id: str) -> str:
    """查询订单"""
    pass

@registry.register("n8n")
@tool
async def generate_report(report_type: str) -> str:
    """生成报告"""
    pass
```

### 工具执行监控

```python
class ToolExecutionMonitor:
    """工具执行监控"""

    async def execute_with_monitoring(
        self,
        tool_name: str,
        tool_input: dict
    ):
        start_time = time.time()

        try:
            # 发送工具开始事件
            await self.send_event({
                "type": "tool_start",
                "tool": tool_name,
                "input": tool_input
            })

            # 执行工具
            result = await tool_executor.ainvoke({
                "tool": tool_name,
                "tool_input": tool_input
            })

            # 记录指标
            duration = time.time() - start_time
            tool_call_duration.labels(tool_name=tool_name).observe(duration)
            tool_call_count.labels(tool_name=tool_name, status="success").inc()

            # 发送工具完成事件
            await self.send_event({
                "type": "tool_end",
                "tool": tool_name,
                "result": result,
                "duration": duration
            })

            return result

        except Exception as e:
            # 记录错误
            tool_call_count.labels(tool_name=tool_name, status="error").inc()

            # 发送错误事件
            await self.send_event({
                "type": "tool_error",
                "tool": tool_name,
                "error": str(e)
            })

            raise
```

## 4. 错误处理和降级

### 多层降级策略

```python
class RobustAgent:
    """具有降级能力的Agent"""

    async def run_with_fallback(self, user_message: str, config: dict):
        """带降级的执行"""

        try:
            # 1. 尝试完整的Agent执行
            return await self.agent.ainvoke(user_message, config)

        except LLMException as e:
            # 2. LLM故障 → 降级到备用LLM
            logger.warning(f"Primary LLM failed: {e}, switching to backup")
            return await self.run_with_backup_llm(user_message, config)

        except DatabaseException as e:
            # 3. 数据库故障 → 使用缓存数据
            logger.warning(f"Database failed: {e}, using cached data")
            return await self.run_with_cache(user_message, config)

        except ToolException as e:
            # 4. 工具故障 → 跳过工具，直接回答
            logger.warning(f"Tool failed: {e}, answering without tools")
            return await self.run_without_tools(user_message, config)

        except Exception as e:
            # 5. 兜底 → 返回友好错误消息
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                "messages": [AIMessage(content="抱歉，系统遇到了问题。请稍后再试或联系客服。")],
                "error": str(e)
            }

    async def run_with_backup_llm(self, user_message: str, config: dict):
        """使用备用LLM"""
        # 切换到备用模型（如Anthropic Claude）
        backup_llm = ChatAnthropic(model="claude-3-sonnet")
        self.agent.llm = backup_llm
        return await self.agent.ainvoke(user_message, config)

    async def run_with_cache(self, user_message: str, config: dict):
        """使用缓存数据"""
        # 从Redis或本地缓存获取数据
        cached_data = await self.cache.get(user_message)
        if cached_data:
            return cached_data

        # 如果没有缓存，返回通用响应
        return {"messages": [AIMessage(content="系统正在维护中，请稍后再试。")]}
```

### 熔断机制

```python
from circuitbreaker import circuit

class ToolWithCircuitBreaker:
    """带熔断的工具"""

    @circuit(failure_threshold=5, recovery_timeout=60)
    async def call_external_api(self, params: dict):
        """调用外部API（带熔断）"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        raise APIException(f"API returned {resp.status}")

        except asyncio.TimeoutError:
            raise APIException("API timeout")

    async def call_with_fallback(self, params: dict):
        """带降级的调用"""
        try:
            return await self.call_external_api(params)
        except CircuitBreakerError:
            # 熔断器打开，使用降级方案
            logger.warning("Circuit breaker open, using fallback")
            return await self.fallback_method(params)
```

```
---

### **2.1.5 部署架构**

```markdown
## 生产环境部署架构
```

                              Internet
                                 │
                                 ▼
                         ┌──────────────┐
                         │  CloudFlare  │
                         │  (CDN + WAF) │
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │   Nginx LB   │
                         │ (Load Balance│
                         └──────┬───────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
         ┌───────────┐   ┌───────────┐   ┌───────────┐
         │  API Pod1 │   │  API Pod2 │   │  API Pod3 │
         │  FastAPI  │   │  FastAPI  │   │  FastAPI  │
         └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
               │               │               │
               └───────────────┼───────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
     ┌─────────────┐   ┌──────────────┐  ┌──────────────┐
     │ PostgreSQL  │   │    Redis     │  │   Qdrant     │
     │   Cluster   │   │   Cluster    │  │   Cluster    │
     │  (Primary + │   │  (Master +   │  │  (Vector DB) │
     │   Replicas) │   │   Replicas)  │  │              │
     └─────────────┘   └──────────────┘  └──────────────┘

```
## Kubernetes部署配置

### 1. Deployment配置

```yaml
# k8s/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-api
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-api
  template:
    metadata:
      labels:
        app: agent-api
        version: v1.0.0
    spec:
      containers:
      - name: api
        image: your-registry/agent-api:1.0.0
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: POSTGRES_HOST
          valueFrom:
            configMapKeyRef:
              name: agent-config
              key: postgres_host
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: postgres_password
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: openai_api_key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 2. Service配置

```yaml
# k8s/service.yaml

apiVersion: v1
kind: Service
metadata:
  name: agent-api-service
  namespace: production
spec:
  type: ClusterIP
  selector:
    app: agent-api
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
```

### 3. Ingress配置

```yaml
# k8s/ingress.yaml

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agent-api-ingress
  namespace: production
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/websocket-services: "agent-api-service"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
spec:
  tls:
  - hosts:
    - api.your-domain.com
    secretName: agent-api-tls
  rules:
  - host: api.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: agent-api-service
            port:
              number: 80
```

### 4. HPA (自动扩缩容)

```yaml
# k8s/hpa.yaml

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Docker Compose部署（开发/测试环境）

```yaml
# docker-compose.prod.yml

version: '3.8'

services:
  api:
    image: your-registry/agent-api:latest
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    networks:
      - agent-network
    deploy:
      resources:
        limits:
          memory: 2G

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - agent-network
    command: redis-server --appendonly yes

networks:
  agent-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
```

## CI/CD流程

### GitHub Actions配置

```yaml
# .github/workflows/deploy.yml

name: Deploy to Production

on:
  push:
    branches:
      - main
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Registry
        uses: docker/login-action@v2
        with:
          registry: your-registry.com
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            your-registry.com/agent-api:latest
            your-registry.com/agent-api:${{ github.sha }}
          cache-from: type=registry,ref=your-registry.com/agent-api:buildcache
          cache-to: type=registry,ref=your-registry.com/agent-api:buildcache,mode=```yaml
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG }}

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/agent-api \
            api=your-registry.com/agent-api:${{ github.sha }} \
            -n production

          kubectl rollout status deployment/agent-api -n production

      - name: Verify deployment
        run: |
          kubectl get pods -n production
          kubectl get svc -n production

      - name: Notify on failure
        if: failure()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployment failed!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## 监控和告警

### Prometheus配置

```yaml
# prometheus.yml

global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

rule_files:
  - "alerts.yml"

scrape_configs:
  - job_name: 'agent-api'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - production
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: agent-api
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - source_labels: [__address__]
        target_label: __address__
        regex: ([^:]+)(?::\d+)?
        replacement: $1:9090
```

### 告警规则

```yaml
# alerts.yml

groups:
  - name: agent_alerts
    interval: 30s
    rules:
      # 高错误率告警
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status=~"5.."}[5m]) 
          / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # 响应时间告警
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99, 
            rate(http_request_duration_seconds_bucket[5m])
          ) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P99 latency is {{ $value }}s"

      # Agent执行失败率告警
      - alert: HighAgentFailureRate
        expr: |
          rate(agent_executions_total{status="error"}[5m])
          / rate(agent_executions_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High agent failure rate"
          description: "Agent failure rate is {{ $value | humanizePercentage }}"

      # 数据库连接告警
      - alert: DatabaseConnectionIssue
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database is down"
          description: "PostgreSQL is not responding"

      # Redis连接告警
      - alert: RedisConnectionIssue
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Redis is down"
          description: "Redis is not responding"

      # Pod重启告警
      - alert: PodRestartingTooOften
        expr: |
          rate(kube_pod_container_status_restarts_total[15m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod restarting frequently"
          description: "Pod {{ $labels.pod }} is restarting too often"
```

### Grafana仪表板配置

```json
{
  "dashboard": {
    "title": "Agent Platform Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Response Time (P50, P95, P99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P99"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Agent Execution Status",
        "targets": [
          {
            "expr": "rate(agent_executions_total[5m])",
            "legendFormat": "{{agent_type}} - {{status}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Tool Call Distribution",
        "targets": [
          {
            "expr": "rate(tool_calls_total[5m])",
            "legendFormat": "{{tool_name}}"
          }
        ],
        "type": "piechart"
      },
      {
        "title": "Active WebSocket Connections",
        "targets": [
          {
            "expr": "active_websocket_connections"
          }
        ],
        "type": "stat"
      },
      {
        "title": "LLM Token Usage",
        "targets": [
          {
            "expr": "rate(llm_tokens_total[1h])",
            "legendFormat": "{{model}} - {{type}}"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

```
---

## 2.2 数据模型设计

```markdown
## 完整的数据库Schema设计

### ER图
```

┌─────────────────┐
│     Users       │
├─────────────────┤
│ user_id (PK)    │
│ username        │
│ email           │
│ created_at      │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────▼────────────┐
│  Conversations      │
├─────────────────────┤
│ id (PK)             │
│ user_id (FK)        │
│ title               │
│ agent_type          │
│ status              │
│ message_count       │
│ total_tokens        │
│ created_at          │
│ updated_at          │
└────────┬────────────┘
         │ 1
         │
         │ N
┌────────▼────────────┐
│     Messages        │
├─────────────────────┤
│ id (PK)             │
│ conversation_id(FK) │
│ role                │
│ content             │
│ metadata (JSONB)    │
│ input_tokens        │
│ output_tokens       │
│ created_at          │
└─────────────────────┘

┌─────────────────────┐
│ Agent Checkpoints   │
├─────────────────────┤
│ id (PK)             │
│ conversation_id(FK) │
│ checkpoint_data     │
│ checkpoint_namespace│
│ step                │
│ node_name           │
│ created_at          │
└─────────────────────┘

```
### 详细表设计

```sql
-- 用户表
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),

    -- 用户属性
    member_level VARCHAR(50) DEFAULT 'regular',
    preferences JSONB DEFAULT '{}',

    -- 统计信息
    total_conversations INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_tokens_used BIGINT DEFAULT 0,

    -- 状态
    status VARCHAR(50) DEFAULT 'active',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP,

    -- 索引
    CONSTRAINT check_status CHECK (status IN ('active', 'suspended', 'deleted'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_last_active ON users(last_active_at);

-- 对话表
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- 对话元数据
    title VARCHAR(500),
    agent_type VARCHAR(100) NOT NULL,

    -- 状态和统计
    status VARCHAR(50) DEFAULT 'active',
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,

    -- 对话配置
    config JSONB DEFAULT '{}',

    -- 标签和分类
    tags TEXT[],
    category VARCHAR(100),

    -- 质量评分
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,

    CONSTRAINT check_status CHECK (status IN ('active', 'archived', 'deleted')),
    CONSTRAINT check_agent_type CHECK (agent_type IN ('customer_service', 'data_analyst', 'code_assistant', 'general'))
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_user_created ON conversations(user_id, created_at DESC);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_agent_type ON conversations(agent_type);
CREATE INDEX idx_conversations_tags ON conversations USING GIN(tags);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,

    -- 消息内容
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,

    -- 元数据（存储工具调用、思维链等）
    metadata JSONB DEFAULT '{}',

    -- Token统计
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,

    -- 模型信息
    model VARCHAR(100),

    -- 评价
    user_feedback VARCHAR(50), -- thumbs_up, thumbs_down, neutral

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_role CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    CONSTRAINT check_feedback CHECK (user_feedback IN ('thumbs_up', 'thumbs_down', 'neutral', NULL))
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_role ON messages(role);
CREATE INDEX idx_messages_feedback ON messages(user_feedback);
CREATE INDEX idx_messages_metadata ON messages USING GIN(metadata);

-- Agent检查点表
CREATE TABLE agent_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,

    -- 检查点数据（完整的状态）
    checkpoint_data JSONB NOT NULL,
    checkpoint_namespace VARCHAR(255) NOT NULL,

    -- 执行信息
    step INTEGER NOT NULL,
    node_name VARCHAR(100),

    -- 性能信息
    execution_time_ms INTEGER,

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_conversation_step UNIQUE (conversation_id, step)
);

CREATE INDEX idx_checkpoints_conversation_id ON agent_checkpoints(conversation_id);
CREATE INDEX idx_checkpoints_conversation_step ON agent_checkpoints(conversation_id, step DESC);
CREATE INDEX idx_checkpoints_created_at ON agent_checkpoints(created_at);

-- 工具调用日志表
CREATE TABLE tool_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,

    -- 工具信息
    tool_name VARCHAR(100) NOT NULL,
    tool_input JSONB NOT NULL,
    tool_output JSONB,

    -- 执行信息
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    execution_time_ms INTEGER,

    -- 时间戳
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,

    CONSTRAINT check_status CHECK (status IN ('pending', 'running', 'success', 'error', 'timeout'))
);

CREATE INDEX idx_tool_logs_conversation ON tool_call_logs(conversation_id);
CREATE INDEX idx_tool_logs_tool_name ON tool_call_logs(tool_name);
CREATE INDEX idx_tool_logs_status ON tool_call_logs(status);
CREATE INDEX idx_tool_logs_started_at ON tool_call_logs(started_at);

-- 向量嵌入表（用于语义搜索）
CREATE TABLE conversation_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,

    -- 向量嵌入
    embedding vector(1536), -- OpenAI ada-002维度

    -- 元数据
    text_content TEXT NOT NULL,
    chunk_index INTEGER,

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- pgvector扩展索引
CREATE INDEX idx_embeddings_vector ON conversation_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_embeddings_conversation ON conversation_embeddings(conversation_id);
CREATE INDEX idx_embeddings_message ON conversation_embeddings(message_id);

-- 系统指标表
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 指标名称
    metric_name VARCHAR(100) NOT NULL,

    -- 指标值
    metric_value DECIMAL(20, 4),

    -- 标签（用于分组）
    labels JSONB DEFAULT '{}',

    -- 时间戳
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_name ON system_metrics(metric_name);
CREATE INDEX idx_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX idx_metrics_labels ON system_metrics USING GIN(labels);

-- 用户反馈表
CREATE TABLE user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- 反馈内容
    feedback_type VARCHAR(50) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,

    -- 分类
    category VARCHAR(100),
    tags TEXT[],

    -- 状态
    status VARCHAR(50) DEFAULT 'pending',
    resolved_at TIMESTAMP,

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_feedback_type CHECK (feedback_type IN ('bug', 'feature_request', 'general', 'complaint', 'praise'))
);

CREATE INDEX idx_feedback_conversation ON user_feedback(conversation_id);
CREATE INDEX idx_feedback_user ON user_feedback(user_id);
CREATE INDEX idx_feedback_type ON user_feedback(feedback_type);
CREATE INDEX idx_feedback_status ON user_feedback(status);

-- 触发器：更新对话的消息计数
CREATE OR REPLACE FUNCTION update_conversation_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE conversations 
        SET 
            message_count = message_count + 1,
            total_tokens = total_tokens + COALESCE(NEW.input_tokens, 0) + COALESCE(NEW.output_tokens, 0),
            last_message_at = NEW.created_at,
            updated_at = NEW.created_at
        WHERE id = NEW.conversation_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_conversation_stats
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION update_conversation_stats();

-- 触发器：更新用户统计
CREATE OR REPLACE FUNCTION update_user_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE users
        SET
            total_messages = total_messages + 1,
            total_tokens_used = total_tokens_used + COALESCE(NEW.input_tokens, 0) + COALESCE(NEW.output_tokens, 0),
            last_active_at = NEW.created_at
        WHERE user_id IN (
            SELECT user_id FROM conversations WHERE id = NEW.conversation_id
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_stats
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION update_user_stats();

-- 视图：对话统计
CREATE VIEW conversation_stats AS
SELECT 
    c.id as conversation_id,
    c.user_id,
    c.agent_type,
    c.message_count,
    c.total_tokens,
    COUNT(DISTINCT tcl.tool_name) as unique_tools_used,
    AVG(tcl.execution_time_ms) as avg_tool_execution_time,
    MAX(m.created_at) as last_message_time,
    EXTRACT(EPOCH FROM (MAX(m.created_at) - MIN(m.created_at))) as conversation_duration_seconds
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
LEFT JOIN tool_call_logs tcl ON c.id = tcl.conversation_id
GROUP BY c.id, c.user_id, c.agent_type, c.message_count, c.total_tokens;

-- 视图：用户活跃度
CREATE VIEW user_activity_stats AS
SELECT
    u.user_id,
    u.username,
    COUNT(DISTINCT c.id) as total_conversations,
    COUNT(m.id) as total_messages,
    SUM(c.total_tokens) as total_tokens,
    MAX(m.created_at) as last_active,
    DATE_TRUNC('day', MAX(m.created_at)) = CURRENT_DATE as active_today
FROM users u
LEFT JOIN conversations c ON u.user_id = c.user_id
LEFT JOIN messages m ON c.id = m.conversation_id
GROUP BY u.user_id, u.username;

-- 分区表（按月分区消息表，提升查询性能）
CREATE TABLE messages_partitioned (
    LIKE messages INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 创建分区（按月）
CREATE TABLE messages_2024_01 PARTITION OF messages_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE messages_2024_02 PARTITION OF messages_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- 自动创建分区的函数
CREATE OR REPLACE FUNCTION create_monthly_partitions(
    start_date DATE,
    end_date DATE
)
RETURNS void AS $$
DECLARE
    current_date DATE := start_date;
    next_date DATE;
    partition_name TEXT;
BEGIN
    WHILE current_date < end_date LOOP
        next_date := current_date + INTERVAL '1 month';
        partition_name := 'messages_' || TO_CHAR(current_date, 'YYYY_MM');

        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF messages_partitioned
             FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            current_date,
            next_date
        );

        current_date := next_date;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 使用示例：创建未来12个月的分区
SELECT create_monthly_partitions(CURRENT_DATE, CURRENT_DATE + INTERVAL '12 months');
```

## 数据迁移脚本

```python
# scripts/migrate_from_n8n.py

"""
从n8n迁移数据到新系统
"""

import asyncio
import asyncpg
from datetime import datetime
import json

async def migrate_conversations():
    """迁移对话数据"""

    # 连接旧数据库（假设n8n使用的数据库）
    old_conn = await asyncpg.connect(
        host='old-db-host',
        database='n8n_db',
        user='n8n_user',
        password='password'
    )

    # 连接新数据库
    new_conn = await asyncpg.connect(
        host='new-db-host',
        database='agent_platform',
        user='agent_user',
        password='password'
    )

    try:
        # 1. 迁移用户
        old_users = await old_conn.fetch("""
            SELECT DISTINCT user_id, username, email
            FROM n8n_conversations
        """)

        for user in old_users:
            await new_conn.execute("""
                INSERT INTO users (user_id, username, email, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO NOTHING
            """, user['user_id'], user['username'], user['email'], datetime.now())

        print(f"Migrated {len(old_users)} users")

        # 2. 迁移对话
        old_conversations = await old_conn.fetch("""
            SELECT * FROM n8n_conversations
            ORDER BY created_at
        """)

        for conv in old_conversations:
            # 创建对话
            conv_id = await new_conn.fetchval("""
                INSERT INTO conversations (
                    user_id, title, agent_type, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, 
                conv['user_id'],
                conv['title'],
                'customer_service',  # 默认类型
                conv['created_at'],
                conv['updated_at']
            )

            # 迁移消息
            old_messages = await old_conn.fetch("""
                SELECT * FROM n8n_messages
                WHERE conversation_id = $1
                ORDER BY created_at
            """, conv['id'])

            for msg in old_messages:
                await new_conn.execute("""
                    INSERT INTO messages (
                        conversation_id, role, content, created_at
                    )
                    VALUES ($1, $2, $3, $4)
                """,
                    conv_id,
                    msg['role'],
                    msg['content'],
                    msg['created_at']
                )

        print(f"Migrated {len(old_conversations)} conversations")

    finally:
        await old_conn.close()
        await new_conn.close()

if __name__ == '__main__':
    asyncio.run(migrate_conversations())
```

```
---
# 三、迁移检查清单

## 3.1 迁移前准备清单

### **3.1.1 环境准备 ✓**

```markdown
## 开发环境

### 本地开发环境搭建
- [ ] 安装Python 3.11+
  ```bash
  python --version  # 确认版本 >= 3.11
```

- [ ] 安装Poetry或pip环境管理工具
  
  ```bash
  pip install poetry
  poetry --version
  ```

- [ ] 安装Docker和Docker Compose
  
  ```bash
  docker --version
  docker-compose --version
  ```

- [ ] 安装PostgreSQL客户端工具
  
  ```bash
  # macOS
  brew install postgresql@15
  
  # Ubuntu
  sudo apt-get install postgresql-client-15
  ```

- [ ] 安装Redis客户端工具
  
  ```bash
  # macOS
  brew install redis
  
  # Ubuntu
  sudo apt-get install redis-tools
  ```

- [ ] IDE配置
  
  - [ ] VSCode或PyCharm安装
  - [ ] Python插件安装
  - [ ] Docker插件安装
  - [ ] 代码格式化工具（Black, Flake8）

### 测试环境

- [ ] 测试服务器准备
  
  - [ ] 服务器规格：8核16G内存（最低配置）
  - [ ] 操作系统：Ubuntu 22.04 LTS
  - [ ] Docker环境安装

- [ ] 数据库准备
  
  - [ ] PostgreSQL 15安装
  - [ ] Redis 7安装
  - [ ] Qdrant安装（可选）

- [ ] 网络配置
  
  - [ ] 端口开放：8000 (API), 5432 (PostgreSQL), 6379 (Redis)
  - [ ] 域名配置：test-api.your-domain.com
  - [ ] SSL证书配置

### 生产环境预准备

- [ ] Kubernetes集群准备（或Docker Swarm）
  
  - [ ] 节点数量：至少3个节点
  - [ ] 资源配额：每个节点16核32G
  - [ ] 存储：至少500GB SSD

- [ ] 数据库集群
  
  - [ ] PostgreSQL主从复制配置
  - [ ] Redis集群配置
  - [ ] 数据库备份策略

- [ ] 监控系统
  
  - [ ] Prometheus安装
  - [ ] Grafana安装
  - [ ] AlertManager配置

- [ ] CI/CD流水线
  
  - [ ] GitHub Actions或GitLab CI配置
  
  - [ ] 容器镜像仓库准备
    
    ```
    
    ```

---

### **3.1.2 技术调研清单 ✓**

```markdown
## LangGraph技术验证

### 基础功能验证
- [ ] 安装LangGraph
  ```bash
  pip install langgraph langchain langchain-openai
```

- [ ] 创建简单的状态图
  
  ```python
  from langgraph.graph import StateGraph
  
  # 验证基础功能
  workflow = StateGraph(dict)
  workflow.add_node("test", lambda x: {"result": "ok"})
  workflow.set_entry_point("test")
  app = workflow.compile()
  
  result = app.invoke({"input": "test"})
  assert result["result"] == "ok"
  ```

- [ ] 测试流式输出
  
  ```python
  async for event in app.astream_events(input_data, version="v1"):
      print(event)
  ```

- [ ] 测试状态持久化
  
  ```python
  from langgraph.checkpoint.postgres import PostgresSaver
  
  checkpointer = PostgresSaver(engine)
  app = workflow.compile(checkpointer=checkpointer)
  ```

### 性能基准测试

- [ ] 单次调用延迟测试
  
  - [ ] 目标：< 2秒
  - [ ] 实际：________

- [ ] 并发测试
  
  - [ ] 10并发：________ QPS
  - [ ] 50并发：________ QPS
  - [ ] 100并发：________ QPS

- [ ] 流式输出首token时间
  
  - [ ] 目标：< 800ms
  - [ ] 实际：________

- [ ] 内存占用测试
  
  - [ ] 单对话：________ MB
  - [ ] 100并发对话：________ GB

### 功能对比验证

- [ ] 对比n8n当前实现
  
  | 功能   | n8n耗时 | LangGraph耗时 | 改善比例  |
  | ---- | ----- | ----------- | ----- |
  | 简单问答 | ____s | ____s       | ____% |
  | 工具调用 | ____s | ____s       | ____% |
  | 多轮对话 | ____s | ____s       | ____% |

### 风险评估

- [ ] 识别技术风险
  
  - [ ] 学习曲线：________ (低/中/高)
  - [ ] 社区支持：________ (好/一般/差)
  - [ ] 稳定性：________ (稳定/一般/不稳定)
  - [ ] 迁移成本：________ (低/中/高)

- [ ] 制定风险应对方案
  
  - [ ] 风险1：________
    
    - 应对：________
  
  - [ ] 风险2：________
    
    - 应对：________
      
      ```
      
      ```

---

### **3.1.3 团队准备清单 ✓**

```markdown
## 人员配置

### 核心开发团队
- [ ] 后端开发工程师（2-3人）
  - [ ] Python开发经验
  - [ ] 异步编程经验
  - [ ] LLM应用开发经验（优先）

- [ ] 前端开发工程师（1人）
  - [ ] React/Svelte经验
  - [ ] WebSocket开发经验

- [ ] DevOps工程师（1人）
  - [ ] Kubernetes经验
  - [ ] CI/CD经验
  - [ ] 监控告警经验

- [ ] 技术负责人/架构师（1人）
  - [ ] 整体技术架构设计
  - [ ] 技术选型决策
  - [ ] 代码审查

### 技能培训计划
- [ ] LangGraph培训（2天）
  - [ ] 第1天：基础概念和API
  - [ ] 第2天：实战演练

- [ ] FastAPI培训（1天）
  - [ ] 异步编程
  - [ ] WebSocket实现

- [ ] PostgreSQL高级特性（1天）
  - [ ] JSONB使用
  - [ ] 性能优化

- [ ] 系统监控和调试（1天）
  - [ ] Prometheus + Grafana
  - [ ] 日志分析

### 分工明确
| 角色 | 负责人 | 主要职责 |
|------|--------|---------|
| 项目经理 | ________ | 进度管理、风险控制 |
| 后端Leader | ________ | Agent开发、API设计 |
| 前端负责人 | ________ | UI集成、用户体验 |
| DevOps | ________ | 部署、监控、运维 |
| 测试负责人 | ________ | 测试计划、质量保证 |
```

---

### **3.1.4 数据准备清单 ✓**

```markdown
## 数据评估

### 现有数据盘点
- [ ] 统计当前数据量
  - [ ] 用户数：________
  - [ ] 对话数：________
  - [ ] 消息数：________
  - [ ] 平均每对话消息数：________

- [ ] 数据质量评估
  - [ ] 数据完整性：________ (好/一般/差)
  - [ ] 数据一致性：________ (好/一般/差)
  - [ ] 数据格式：________ (统一/混乱)

- [ ] 数据清洗需求
  - [ ] 需要清洗：是 / 否
  - [ ] 清洗内容：________
  - [ ] 预计工作量：________ 人天

### 数据迁移方案
- [ ] 迁移策略选择
  - [ ] 全量迁移 / 增量迁移 / 混合迁移
  - [ ] 停机迁移 / 在线迁移

- [ ] 迁移脚本开发
  - [ ] 用户数据迁移脚本
  - [ ] 对话数据迁移脚本
  - [ ] 消息数据迁移脚本
  - [ ] 数据验证脚本

- [ ] 测试迁移
  - [ ] 小批量测试（1000条记录）
  - [ ] 验证数据正确性
  - [ ] 性能测试

### 备份策略
- [ ] 迁移前全量备份
  - [ ] 数据库备份：________ GB
  - [ ] 文件备份：________ GB
  - [ ] 备份存储位置：________

- [ ] 回滚方案
  - [ ] 回滚步骤文档编写
  - [ ] 回滚脚本准备
  - [ ] 回滚演练
```

---

## 3.2 迁移实施清单

### **3.2.1 阶段一：POC验证（Week 1-2）✓**

```markdown
## Week 1: 环境搭建和基础功能

### Day 1-2: 环境搭建
- [ ] 开发环境搭建完成
  - [ ] Docker Compose启动成功
  - [ ] 数据库连接正常
  - [ ] Redis连接正常

- [ ] 代码仓库初始化
  - [ ] Git仓库创建
  - [ ] 分支策略确定（Git Flow）
  - [ ] CI配置完成

- [ ] 基础项目结构创建
```

  ✓ backend/
    ✓ app/
      ✓ __init__.py
      ✓ main.py
      ✓ config.py
      ✓ models/
      ✓ agents/
      ✓ tools/
      ✓ api/

```
### Day 3-4: 第一个Agent实现
- [ ] 创建简单的客服Agent
- [ ] 状态定义完成
- [ ] 基础节点实现
  - [ ] understand_intent
  - [ ] generate_response
- [ ] 状态图编译成功

- [ ] 本地测试通过
- [ ] 单元测试编写
- [ ] 功能测试通过

### Day 5: FastAPI集成
- [ ] HTTP端点实现
- [ ] POST /api/v1/chat
- [ ] GET /health

- [ ] WebSocket端点实现
- [ ] WS /ws/chat/{user_id}/{conversation_id}
- [ ] 流式输出测试通过

- [ ] 端到端测试
- [ ] Postman测试集创建
- [ ] 自动化测试通过

## Week 2: 工具集成和性能测试

### Day 6-7: 工具集成
- [ ] 数据库工具实现
- [ ] query_orders
- [ ] query_order_detail
- [ ] query_user_info

- [ ] n8n工具集成
- [ ] generate_report
- [ ] send_notification
- [ ] sync_data

- [ ] 工具测试
- [ ] 单独测试每个工具
- [ ] 集成测试

### Day 8-9: 性能测试
- [ ] 性能基准测试
```bash
# 使用locust或k6进行压测
k6 run --vus 10 --duration 30s load_test.js
```

- [ ] 记录性能指标
  
  | 指标     | 目标     | 实际    | 达标  |
  | ------ | ------ | ----- | --- |
  | P50延迟  | <1s    | ___s  | ☐   |
  | P99延迟  | <3s    | ___s  | ☐   |
  | QPS    | >50    | ___   | ☐   |
  | 首token | <800ms | ___ms | ☐   |

- [ ] 性能优化（如需要）
  
  - [ ] 识别瓶颈
  - [ ] 实施优化
  - [ ] 重新测试

### Day 10: POC总结

- [ ] POC演示文档
  
  - [ ] 功能清单
  - [ ] 性能报告
  - [ ] 对比分析（vs n8n）

- [ ] 决策会议
  
  - [ ] 技术可行性：确认 / 存疑 / 否决
  - [ ] 性能改善：满意 / 一般 / 不满意
  - [ ] 是否继续：是 / 否

- [ ] 风险和问题记录
  
  - [ ] 遇到的问题：________
  
  - [ ] 解决方案：________
  
  - [ ] 未解决问题：________
    
    ```
    
    ```

---

### **3.2.2 阶段二：核心功能开发（Week 3-6）✓**

```markdown
## Week 3: 完整Agent实现

### 客服Agent完整功能
- [ ] 意图识别节点
  - [ ] 支持的意图类型定义
  - [ ] LLM prompt优化
  - [ ] 准确率测试 > 90%

- [ ] 用户信息查询节点
  - [ ] 数据库查询优化
  - [ ] 缓存实现

- [ ] 工具调用节点
  - [ ] 动态工具选择
  - [ ] 并行工具调用
  - [ ] 错误处理

- [ ] 响应生成节点
  - [ ] 多模板支持
  - [ ] 个性化回复

- [ ] 转人工节点
  - [ ] 触发条件定义
  - [ ] 通知机制实现

### 路由逻辑实现
- [ ] 条件路由完成
  ```python
  def route_after_understand(state):
      if state["needs_human"]:
          return "human"
      elif state["intent"] == "query_order":
          return "query_tools"
      else:
          return "direct_response"
```

- [ ] 循环控制逻辑
  - [ ] 最大循环次数限制
  - [ ] 退出条件判断

### 测试

- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过
- [ ] 边界情况测试

## Week 4: 状态管理和持久化

### PostgreSQL集成

- [ ] 数据库Schema创建
  
  - [ ] 所有表创建
  - [ ] 索引创建
  - [ ] 触发器创建

- [ ] 状态持久化实现
  
  - [ ] LangGraph checkpointer配置
  - [ ] 自动保存测试
  - [ ] 状态恢复测试

- [ ] 数据迁移工具
  
  - [ ] 迁移脚本编写
  - [ ] 测试数据迁移
  - [ ] 验证脚本

### Redis集成

- [ ] 缓存策略实现
  
  - [ ] LLM响应缓存
  - [ ] 用户会话缓存
  - [ ] 热点数据缓存

- [ ] 缓存失效策略
  
  - [ ] TTL设置
  - [ ] LRU配置

### 测试

- [ ] 持久化功能测试
  
  - [ ] 创建对话
  - [ ] 中断后恢复
  - [ ] 历史查询

- [ ] 缓存功能测试
  
  - [ ] 缓存命中率监控
  - [ ] 缓存一致性验证

## Week 5: API和前端集成

### API完善

- [ ] RESTful API完整实现
  
  ```
  POST   /api/v1/chat                    # 非流式对话
  POST   /api/v1/chat/stream             # 流式对话
  GET    /api/v1/conversations           # 对话列表
  GET    /api/v1/conversations/:id       # 对话详情
  DELETE /api/v1/conversations/:id       # 删除对话
  GET    /api/v1/conversations/:id/history  # 对话历史
  POST   /api/v1/conversations/:id/rollback # 回滚
  ```

- [ ] WebSocket API完善
  
  - [ ] 连接管理
  - [ ] 心跳机制
  - [ ] 断线重连

- [ ] API文档
  
  - [ ] Swagger/OpenAPI文档生成
  - [ ] 示例代码编写

### OpenWebUI集成

- [ ] 前端代码修改
  
  - [ ] WebSocket客户端实现
  - [ ] 流式消息展示
  - [ ] 工具调用状态展示

- [ ] UI优化
  
  - [ ] 加载状态
  - [ ] 错误提示
  - [ ] 重试机制

- [ ] 测试
  
  - [ ] 浏览器兼容性测试
  - [ ] 移动端测试
  - [ ] 性能测试

## Week 6: 监控和日志

### 监控系统搭建

- [ ] Prometheus部署
  
  - [ ] 服务发现配置
  - [ ] 抓取规则配置

- [ ] Grafana部署
  
  - [ ] 仪表板创建
  - [ ] 数据源配置

- [ ] 指标埋点
  
  - [ ] HTTP请求指标
  - [ ] Agent执行指标
  - [ ] 工具调用指标
  - [ ] 数据库指标

### 日志系统

- [ ] 结构化日志实现
  
  - [ ] JSON格式日志
  - [ ] 日志级别配置
  - [ ] 日志轮转

- [ ] 日志收集（可选）
  
  - [ ] ELK Stack或Loki
  - [ ] 日志查询界面

### 告警配置

- [ ] 告警规则定义
  
  - [ ] 高错误率告警
  - [ ] 高延迟告警
  - [ ] 系统资源告警

- [ ] 告警通知
  
  - [ ] Slack/钉钉/企业微信集成
  - [ ] 邮件通知

### 验收

- [ ] 监控数据正常采集

- [ ] Grafana仪表板可访问

- [ ] 告警测试通过
  
  ```
  
  ```

---

### **3.2.3 阶段三：测试和优化（Week 7-8）✓**

```markdown
## Week 7: 全面测试

### 功能测试
- [ ] 测试用例清单
  | 功能 | 测试用例数 | 通过 | 失败 | 通过率 |
  |------|-----------|------|------|--------|
  | 简单问答 | ___ | ___ | ___ | ___% |
  | 订单查询 | ___ | ___ | ___ | ___% |
  | 多轮对话 | ___ | ___ | ___ | ___% |
  | 工具调用 | ___ | ___ | ___ | ___% |
  | 转人工 | ___ | ___ | ___ | ___% |
  | 错误处理 | ___ | ___ | ___ | ___% |

- [ ] 回归测试
  - [ ] 所有现有功能测试通过

- [ ] 边界测试
  - [ ] 极长输入测试
  - [ ] 特殊字符测试
  - [ ] 并发测试

### 性能测试
- [ ] 压力测试
  ```bash
  # 使用k6进行压测
  k6 run --vus 100 --duration 5m stress_test.js
```

- [ ] 性能指标记录
  
  | 场景   | 并发数 | QPS | P50   | P95   | P99   | 错误率  |
  | ---- | --- | --- | ----- | ----- | ----- | ---- |
  | 简单对话 | 100 | ___ | ___ms | ___ms | ___ms | ___% |
  | 工具调用 | 50  | ___ | ___ms | ___ms | ___ms | ___% |
  | 长对话  | 20  | ___ | ___ms | ___ms | ___ms | ___% |

- [ ] 资源监控
  
  - [ ] CPU使用率
  - [ ] 内存使用率
  - [ ] 数据库连接数
  - [ ] 网络带宽

### 安全测试

- [ ] SQL注入测试
- [ ] XSS攻击测试
- [ ] CSRF测试
- [ ] 认证授权测试
- [ ] 敏感数据加密验证

### 兼容性测试

- [ ] 浏览器兼容性
  
  - [ ] Chrome
  - [ ] Firefox
  - [ ] Safari
  - [ ] Edge

- [ ] 移动端测试
  
  - [ ] iOS Safari
  - [ ] Android Chrome

## Week 8: 性能优化

### 识别性能瓶颈

- [ ] 性能分析
  
  - [ ] Python profiler分析
  - [ ] 数据库慢查询分析
  - [ ] 网络延迟分析

- [ ] 瓶颈清单
  
  1. ________：影响___，优化方案___
  2. ________：影响___，优化方案___
  3. ________：影响___，优化方案___

### 实施优化

- [ ] 代码层优化
  
  - [ ] 异步I/O优化
  - [ ] 批处理优化
  - [ ] 算法优化

- [ ] 数据库优化
  
  - [ ] 查询优化
  - [ ] 索引优化
  - [ ] 连接池配置

- [ ] 缓存优化
  
  - [ ] 增加缓存点
  - [ ] 缓存预热
  - [ ] 缓存更新策略

- [ ] 架构优化（如需要）
  
  - [ ] 负载均衡调整
  - [ ] 数据库读写分离
  - [ ] CDN加速

### 优化效果验证

- [ ] 重新性能测试

- [ ] 对比优化前后
  
  | 指标    | 优化前   | 优化后   | 改善   |
  | ----- | ----- | ----- | ---- |
  | P99延迟 | ___ms | ___ms | ___% |
  | QPS   | ___   | ___   | ___% |
  | 错误率   | ___%  | ___%  | ___% |
  | CPU使用 | ___%  | ___%  | ___% |

### 文档更新

- [ ] 性能优化文档

- [ ] 运维文档更新

- [ ] API文档更新
  
  ```
  
  ```

---

### **3.2.4 阶段四：灰度发布（Week 9-10）✓**

```markdown
## Week 9: 灰度准备

### 生产环境准备
- [ ] Kubernetes集群配置
  - [ ] Namespace创建
  - [ ] ConfigMap配置
  - [ ] Secret配置
  - [ ] PVC创建

- [ ] 数据库准备
  - [ ] 生产数据库创建
  - [ ] 主从复制配置
  - [ ] 备份策略配置

- [ ] 监控告警配置
  - [ ] 生产环境监控规则
  - [ ] 告警接收人配置
  - [ ] 值班表制定

### 灰度策略制定
- [ ] 灰度方案
```

  Phase 1 (Day 1-2): 5%流量
  Phase 2 (Day 3-4): 20%流量
  Phase 3 (Day 5-6): 50%流量
  Phase 4 (Day 7): 100%流量

```
- [ ] 灰度用户选择
- [ ] 内部用户优先
- [ ] Beta用户
- [ ] 随机抽样

- [ ] 回滚条件定义
- [ ] 错误率 > 5%
- [ ] P99延迟 > 5s
- [ ] 用户投诉 > 10条/小时

### 数据迁移
- [ ] 迁移窗口确定
- [ ] 日期：________
- [ ] 时间：________ (建议凌晨低峰期)
- [ ] 预计时长：________

- [ ] 迁移步骤
1. [ ] 停止n8n工作流
2. [ ] 数据库全量备份
3. [ ] 执行迁移脚本
4. [ ] 数据验证
5. [ ] 启动新系统
6. [ ] 灰度流量切换

- [ ] 回滚准备
- [ ] 回滚脚本测试
- [ ] 回滚决策流程
- [ ] 回滚负责人：________

## Week 10: 灰度执行

### Day 1-2: 5%流量
- [ ] 流量切换
- [ ] Nginx配置更新
- [ ] 流量比例验证

- [ ] 密切监控
- [ ] 实时错误监控
- [ ] 性能指标监控
- [ ] 用户反馈收集

- [ ] 问题记录
| 时间 | 问题 | 影响 | 解决方案 | 状态 |
|------|------|------|---------|------|
| ___ | ___ | ___ | ___ | ___ |

- [ ] 每日总结会议
- [ ] 问题回顾
- [ ] 数据分析
- [ ] 决策：继续/暂停/回滚

### Day 3-4: 20%流量
- [ ] 流量切换
- [ ] 持续监控
- [ ] 性能对比
| 指标 | 新系统 | 旧系统 | 对比 |
|------|--------|--------|------|
| P99延迟 | ___ms | ___ms | ___% |
| 错误率 | ___% | ___% | ___% |
| 用户满意度 | ___ | ___ | ___ |

### Day 5-6: 50%流量
- [ ] 流量切换
- [ ] 负载测试
- [ ] 验证系统承载能力
- [ ] 资源使用情况

- [ ] 用户反馈收集
- [ ] 满意度调查
- [ ] 功能反馈
- [ ] Bug反馈

### Day 7: 100%流量
- [ ] 最终切换
- [ ] 全量流量切换
- [ ] n8n系统下线（保留一周作为备份）

- [ ] 稳定性观察
- [ ] 连续48小时监控
- [ ] 无重大问题

- [ ] 项目总结
- [ ] 总结会议
- [ ] 经验文档
- [ ] 后续优化计划
```

---

## 3.3 验收标准清单

### **3.3.1 功能验收 ✓**

```markdown
## 核心功能验收

### Agent功能
- [ ] 简单问答
  - [ ] 响应准确率 > 95%
  - [ ] 平均响应时间 < 2s

- [ ] 订单查询
  - [ ] 查询成功率 > 99%
  - [ ] 数据准确性 100%

- [ ] 多轮对话
  - [ ] 上下文保持 > 100轮
  - [ ] 上下文准确率 > 90%

- [ ] 工具调用
  - [ ] 工具选择准确率 > 90%
  - [ ] 工具执行成功率 > 95%

- [ ] 转人工
  - [ ] 触发准确率 > 85%
  - [ ] 转接成功率 > 99%

### API功能
- [ ] RESTful API
  - [ ] 所有端点正常工作
  - [ ] 错误处理正确
  - [ ] 文档完整准确

- [ ] WebSocket
  - [ ] 连接稳定性 > 99%
  - [ ] 流式输出正常
  - [ ] 断线重连工作

### UI功能
- [ ] 消息展示
  - [ ] 流式显示流畅
  - [ ] 格式正确
  - [ ] 多媒体支持（如有）

- [ ] 交互功能
  - [ ] 输入响应及时
  - [ ] 按钮功能正常
  - [ ] 错误提示清晰

- [ ] 兼容性
  - [ ] 主流浏览器支持
  - [ ] 移动端适配
```

---

### **3.3.2 性能验收 ✓**

```markdown
## 性能指标验收

### 响应时间
- [ ] P50 < 1s ✓ 实际：___ms
- [ ] P95 < 2s ✓ 实际：___ms
- [ ] P99 < 3s ✓ 实际：___ms
-```markdown
### 吞吐量
- [ ] 简单对话 > 100 QPS ✓ 实际：___
- [ ] 工具调用 > 50 QPS ✓ 实际：___
- [ ] 并发用户 > 1000 ✓ 实际：___

### 首Token时间
- [ ] 简单问答 < 800ms ✓ 实际：___ms
- [ ] 复杂查询 < 1500ms ✓ 实际：___ms

### 资源使用
- [ ] CPU使用率（常态）< 60% ✓ 实际：___%
- [ ] 内存使用率 < 70% ✓ 实际：___%
- [ ] 数据库连接数 < 80% ✓ 实际：___

### 可用性
- [ ] 系统可用性 > 99.9% ✓ 实际：___%
- [ ] API可用性 > 99.95% ✓ 实际：___%
- [ ] 数据库可用性 > 99.99% ✓ 实际：___%

### 对比验证（vs n8n）
| 指标 | n8n | LangGraph | 改善 | 达标 |
|------|-----|-----------|------|------|
| 平均响应时间 | 8s | ___s | ___% | ☐ |
| P99响应时间 | 30s | ___s | ___% | ☐ |
| 并发能力 | 10 | ___ | ___% | ☐ |
| 上下文长度 | 50 | ___ | ___% | ☐ |
| 错误率 | 5% | ___% | ___% | ☐ |
```

---

### **3.3.3 稳定性验收 ✓**

```markdown
## 稳定性测试

### 长时间运行测试
- [ ] 72小时稳定运行
  - [ ] 无内存泄漏
  - [ ] 无性能衰减
  - [ ] 错误率稳定

### 异常恢复测试
- [ ] 数据库故障恢复
  - [ ] 自动切换到从库
  - [ ] 数据一致性验证
  - [ ] 恢复时间 < 1分钟

- [ ] Redis故障恢复
  - [ ] 降级到无缓存模式
  - [ ] 功能可用性保持
  - [ ] 性能影响 < 20%

- [ ] LLM API故障
  - [ ] 切换到备用LLM
  - [ ] 或返回友好错误
  - [ ] 不影响其他功能

### 并发压力测试
- [ ] 1000并发用户测试
  - [ ] 系统响应正常
  - [ ] 无崩溃
  - [ ] 错误率 < 1%

- [ ] 突发流量测试
  - [ ] 从10 QPS突增到100 QPS
  - [ ] 系统平滑处理
  - [ ] 自动扩容（如K8s HPA）

### 数据一致性测试
- [ ] 并发写入测试
  - [ ] 无数据丢失
  - [ ] 无数据重复
  - [ ] 事务隔离正确

- [ ] 故障恢复一致性
  - [ ] 检查点恢复正确
  - [ ] 消息顺序正确
  - [ ] 状态一致
```

---

### **3.3.4 安全性验收 ✓**

```markdown
## 安全测试

### 身份认证
- [ ] 用户认证机制
  - [ ] JWT token验证
  - [ ] Token过期处理
  - [ ] Token刷新机制

- [ ] API密钥管理
  - [ ] 密钥安全存储
  - [ ] 密钥轮换机制
  - [ ] 权限控制

### 数据安全
- [ ] 敏感数据加密
  - [ ] 数据库密码加密存储
  - [ ] 传输层加密（HTTPS/WSS）
  - [ ] 日志脱敏

- [ ] 数据访问控制
  - [ ] 用户只能访问自己的数据
  - [ ] 管理员权限隔离
  - [ ] 数据导出权限控制

### 注入攻击防护
- [ ] SQL注入测试
  - [ ] 使用参数化查询
  - [ ] 输入验证
  - [ ] 测试通过

- [ ] XSS攻击防护
  - [ ] 输入过滤
  - [ ] 输出转义
  - [ ] CSP配置

- [ ] CSRF防护
  - [ ] CSRF token验证
  - [ ] SameSite cookie

### 速率限制
- [ ] API限流
  - [ ] 用户级限流：100 req/min
  - [ ] IP级限流：1000 req/min
  - [ ] 全局限流：10000 req/min

- [ ] WebSocket连接限制
  - [ ] 单用户最大连接数：5
  - [ ] 心跳超时断开

### 安全审计
- [ ] 操作日志记录
  - [ ] 所有API调用记录
  - [ ] 敏感操作单独记录
  - [ ] 日志保留90天

- [ ] 安全扫描
  - [ ] 依赖库漏洞扫描
  - [ ] 代码安全扫描
  - [ ] 无高危漏洞
```

---

### **3.3.5 可维护性验收 ✓**

```markdown
## 代码质量

### 代码规范
- [ ] 代码风格一致
  - [ ] Black格式化通过
  - [ ] Flake8检查通过
  - [ ] MyPy类型检查通过

- [ ] 代码注释
  - [ ] 函数文档字符串完整
  - [ ] 复杂逻辑有注释
  - [ ] 注释覆盖率 > 30%

### 测试覆盖
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试覆盖率 > 60%
- [ ] 关键路径测试覆盖率 100%

### 文档完整性
- [ ] 技术文档
  - [ ] 架构设计文档
  - [ ] API文档（Swagger）
  - [ ] 数据库设计文档
  - [ ] 部署文档

- [ ] 运维文档
  - [ ] 安装部署指南
  - [ ] 配置说明
  - [ ] 故障排查手册
  - [ ] 备份恢复流程

- [ ] 用户文档
  - [ ] 使用指南
  - [ ] FAQ
  - [ ] 最佳实践

## 监控和告警

### 监控覆盖
- [ ] 应用层监控
  - [ ] API请求监控
  - [ ] Agent执行监控
  - [ ] 工具调用监控

- [ ] 基础设施监控
  - [ ] 服务器资源监控
  - [ ] 数据库监控
  - [ ] 网络监控

- [ ] 业务监控
  - [ ] 用户活跃度
  - [ ] 对话成功率
  - [ ] 用户满意度

### 告警配置
- [ ] 告警规则完整
  - [ ] 服务可用性告警
  - [ ] 性能告警
  - [ ] 错误率告警
  - [ ] 资源使用告警

- [ ] 告警通知
  - [ ] 多渠道通知（邮件+IM）
  - [ ] 告警分级
  - [ ] 值班轮换

### Grafana仪表板
- [ ] 核心仪表板
  - [ ] 系统概览
  - [ ] 性能监控
  - [ ] 业务指标
  - [ ] 告警面板

## 部署和运维

### 部署自动化
- [ ] CI/CD流水线
  - [ ] 自动化测试
  - [ ] 自动化构建
  - [ ] 自动化部署

- [ ] 配置管理
  - [ ] 环境变量管理
  - [ ] Secret管理
  - [ ] ConfigMap管理

### 备份恢复
- [ ] 数据备份
  - [ ] 每日全量备份
  - [ ] 每小时增量备份
  - [ ] 备份保留30天

- [ ] 恢复演练
  - [ ] 恢复流程文档化
  - [ ] 恢复时间 < 1小时
  - [ ] 数据完整性验证
```

---

## 3.4 问题追踪清单

```markdown
## 已知问题追踪表

| ID | 问题描述 | 严重程度 | 状态 | 负责人 | 计划解决时间 |
|----|---------|---------|------|--------|------------|
| 001 | _______ | 🔴高/🟡中/🟢低 | 待解决/进行中/已解决 | ___ | ____ |
| 002 | _______ | 🔴高/🟡中/🟢低 | 待解决/进行中/已解决 | ___ | ____ |
| 003 | _______ | 🔴高/🟡中/🟢低 | 待解决/进行中/已解决 | ___ | ____ |

## 风险追踪表

| ID | 风险描述 | 可能性 | 影响 | 缓解措施 | 负责人 | 状态 |
|----|---------|--------|------|---------|--------|------|
| R01 | 性能不达标 | 低 | 高 | 提前压测、准备优化方案 | ___ | 监控中 |
| R02 | 数据迁移失败 | 中 | 高 | 充分测试、准备回滚方案 | ___ | 监控中 |
| R03 | 学习曲线陡峭 | 中 | 中 | 提前培训、文档完善 | ___ | 监控中 |
| R04 | LLM API不稳定 | 低 | 中 | 备用LLM、降级方案 | ___ | 监控中 |

## 待办事项（TODOs）

### 高优先级
- [ ] ________ （截止日期：____）
- [ ] ________ （截止日期：____）
- [ ] ________ （截止日期：____）

### 中优先级
- [ ] ________ （截止日期：____）
- [ ] ________ （截止日期：____）

### 低优先级
- [ ] ________ （截止日期：____）
- [ ] ________ （截止日期：____）

## 技术债务清单

| 债务描述 | 影响 | 计划偿还时间 | 负责人 |
|---------|------|-------------|--------|
| _______ | ____ | __________ | ______ |
| _______ | ____ | __________ | ______ |
```

---

# 四、性能优化方案

## 4.1 代码层优化

### **4.1.1 异步编程优化 ⚡**

```python
"""
异步编程最佳实践
"""

# ❌ 错误：串行执行
async def bad_example(user_id: str):
    user_info = await get_user_info(user_id)      # 100ms
    orders = await get_orders(user_id)             # 200ms
    preferences = await get_preferences(user_id)   # 150ms
    # 总耗时：450ms

# ✅ 正确：并行执行
async def good_example(user_id: str):
    user_info, orders, preferences = await asyncio.gather(
        get_user_info(user_id),
        get_orders(user_id),
        get_preferences(user_id)
    )
    # 总耗时：200ms（最慢的那个）

# ✅ 更好：使用 TaskGroup（Python 3.11+）
async def better_example(user_id: str):
    async with asyncio.TaskGroup() as tg:
        user_task = tg.create_task(get_user_info(user_id))
        orders_task = tg.create_task(get_orders(user_id))
        prefs_task = tg.create_task(get_preferences(user_id))

    return {
        "user": user_task.result(),
        "orders": orders_task.result(),
        "preferences": prefs_task.result()
    }

# ✅ 最佳：批量处理
async def batch_example(user_ids: list):
    """批量获取用户信息"""
    # 而不是循环调用API
    users = await get_users_batch(user_ids)  # 一次性获取
    return users
```

### **4.1.2 LLM调用优化 🤖**

```python
"""
LLM调用优化策略
"""

from functools import lru_cache
import hashlib
import json

class OptimizedLLMClient:
    """优化的LLM客户端"""

    def __init__(self):
        self.llm = ChatOpenAI()
        self.redis = Redis()

    async def invoke_with_cache(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """带缓存的LLM调用"""

        # 1. 生成缓存key
        cache_key = self._generate_cache_key(prompt, kwargs)

        # 2. 尝试从缓存获取
        cached = await self.redis.get(cache_key)
        if cached:
            logger.info("Cache hit for LLM request")
            return json.loads(cached)

        # 3. 调用LLM
        response = await self.llm.ainvoke(prompt, **kwargs)

        # 4. 缓存结果
        await self.redis.set(
            cache_key,
            json.dumps(response),
            ex=3600  # 1小时过期
        )

        return response

    def _generate_cache_key(self, prompt: str, kwargs: dict) -> str:
        """生成缓存key"""
        content = f"{prompt}:{json.dumps(kwargs, sort_keys=True)}"
        return f"llm:{hashlib.md5(content.encode()).hexdigest()}"

    async def invoke_with_timeout(
        self,
        prompt: str,
        timeout: int = 30,
        **kwargs
    ):
        """带超时的LLM调用"""
        try:
            return await asyncio.wait_for(
                self.llm.ainvoke(prompt, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"LLM request timeout after {timeout}s")
            raise TimeoutError("LLM request timeout")

    async def invoke_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        **kwargs
    ):
        """带重试的LLM调用"""
        for attempt in range(max_retries):
            try:
                return await self.llm.ainvoke(prompt, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"LLM request failed, retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(2 ** attempt)  # 指数退避

# Prompt优化
class PromptOptimizer:
    """Prompt优化器"""

    @staticmethod
    def compress_context(messages: list, max_tokens: int = 2000) -> list:
        """压缩上下文"""

        # 计算当前token数
        current_tokens = sum(len(m.content.split()) * 1.3 for m in messages)

        if current_tokens <= max_tokens:
            return messages

        # 保留最近的消息
        recent_messages = messages[-5:]

        # 对更早的消息进行摘要
        older_messages = messages[:-5]
        summary = summarize_messages(older_messages)

        return [
            {"role": "system", "content": f"对话摘要：{summary}"}
        ] + recent_messages

    @staticmethod
    def optimize_system_prompt(prompt: str) -> str:
        """优化系统提示词"""
        # 移除冗余
        # 使用更简洁的表达
        # 添加格式化指令
        return prompt.strip()

# 批量处理
async def batch_llm_requests(prompts: list) -> list:
    """批量处理LLM请求"""

    # 将多个请求合并
    combined_prompt = "\n\n---\n\n".join([
        f"Request {i+1}:\n{prompt}"
        for i, prompt in enumerate(prompts)
    ])

    response = await llm.ainvoke(combined_prompt)

    # 解析批量响应
    responses = parse_batch_response(response)

    return responses
```

### **4.1.3 数据库查询优化 🗄️**

```python
"""
数据库查询优化
"""

from sqlalchemy import select, join, and_, or_
from sqlalchemy.orm import joinedload, selectinload

class OptimizedQueries:
    """优化的查询"""

    # ❌ N+1查询问题
    async def bad_query(self, conversation_ids: list):
        conversations = await session.execute(
            select(Conversation).where(Conversation.id.in_(conversation_ids))
        )

        for conv in conversations:
            # 每次循环都查询一次数据库！
            messages = await session.execute(
                select(Message).where(Message.conversation_id == conv.id)
            )
            conv.messages = messages.scalars().all()

    # ✅ 使用JOIN避免N+1
    async def good_query(self, conversation_ids: list):
        result = await session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))  # 预加载关联数据
            .where(Conversation.id.in_(conversation_ids))
        )
        return result.scalars().all()

    # ✅ 使用索引优化查询
    async def optimized_query(self, user_id: str, start_date, end_date):
        # 确保有索引：idx_conversation_user_created
        result = await session.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.created_at.between(start_date, end_date)
                )
            )
            .order_by(Conversation.created_at.desc())
            .limit(100)
        )
        return result.scalars().all()

    # ✅ 批量插入优化
    async def bulk_insert(self, messages: list):
        # 使用bulk_insert_mappings而不是逐条插入
        await session.execute(
            insert(Message),
            [
                {
                    "conversation_id": msg.conversation_id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at
                }
                for msg in messages
            ]
        )
        await session.commit()

    # ✅ 使用物化视图
    async def use_materialized_view(self):
        """使用物化视图加速复杂查询"""
        # 创建物化视图
        await session.execute(text("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS conversation_stats_mv AS
            SELECT 
                c.id,
                c.user_id,
                COUNT(m.id) as message_count,
                MAX(m.created_at) as last_message_at
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id, c.user_id
        """))

        # 查询物化视图（非常快）
        result = await session.execute(
            text("SELECT * FROM conversation_stats_mv WHERE user_id = :user_id"),
            {"user_id": user_id}
        )

        return result.fetchall()

    # ✅ 分页优化
    async def efficient_pagination(self, page: int, page_size: int):
        """高效分页"""
        # 使用游标分页而不是OFFSET
        # OFFSET在大数据量时性能很差

        # ❌ 差的分页
        # SELECT * FROM messages OFFSET 10000 LIMIT 100

        # ✅ 好的分页（使用游标）
        last_id = request.args.get('last_id')

        query = select(Message).order_by(Message.id.desc()).limit(page_size)

        if last_id:
            query = query.where(Message.id < last_id)

        result = await session.execute(query)
        return result.scalars().all()

# 连接池配置优化
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    database_url,
    pool_size=20,              # 连接池大小
    max_overflow=40,           # 最大溢出连接
    pool_timeout=30,           # 连接超时
    pool_recycle=3600,         # 连接回收时间
    pool_pre_ping=True,        # 连接健康检查
    echo=False,                # 不打印SQL（生产环境）
    echo_pool=False,
)
```

---

## 4.2 缓存优化策略

### **4.2.1 多层缓存架构 📦**

```python
"""
多层缓存架构
"""

class MultiLevelCache:
    """多层缓存"""

    def __init__(self):
        self.l1_cache = {}  # 内存缓存（最快）
        self.l2_cache = Redis()  # Redis缓存（快）
        self.l3_cache = None  # 数据库（慢）

    async def get(self, key: str):
        """获取缓存（多层查找）"""

        # L1: 内存缓存
        if key in self.l1_cache:
            logger.debug(f"L1 cache hit: {key}")
            return self.l1_cache[key]

        # L2: Redis缓存
        value = await self.l2_cache.get(key)
        if value:
            logger.debug(f"L2 cache hit: {key}")
            # 回填到L1
            self.l1_cache[key] = value
            return value

        # L3: 数据库
        value = await self.fetch_from_database(key)
        if value:
            logger.debug(f"L3 cache hit: {key}")
            # 回填到L2和L1
            await self.l2_cache.set(key, value, ex=3600)
            self.l1_cache[key] = value
            return value

        return None

    async def set(self, key: str, value: any, ttl: int = 3600):
        """设置缓存（写入所有层）"""
        self.l1_cache[key] = value
        await self.l2_cache.set(key, value, ex=ttl)

    def invalidate(self, key: str):
        """失效缓存"""
        if key in self.l1_cache:
            del self.l1_cache[key]
        asyncio.create_task(self.l2_cache.delete(key))

# 智能缓存策略
class SmartCache:
    """智能缓存"""

    def __init__(self):
        self.cache = Redis()
        self.stats = {}  # 统计信息

    async def get_with_stats(self, key: str):
        """获取并记录统计"""
        value = await self.cache.get(key)

        # 记录访问
        if key not in self.stats:
            self.stats[key] = {"hits": 0, "misses": 0}

        if value:
            self.stats[key]["hits"] += 1
        else:
            self.stats[key]["misses"] += 1

        return value

    async def adaptive_ttl(self, key: str, value: any):
        """自适应TTL"""
        stats = self.stats.get(key, {})
        hit_rate = stats.get("hits", 0) / (stats.get("hits", 0) + stats.get("misses", 1))

        # 根据命中率调整TTL
        if hit_rate > 0.8:
            ttl = 7200  # 高命中率，延长缓存
        elif hit_rate > 0.5:
            ttl = 3600
        else:
            ttl = 1800  # 低命中率，缩短缓存

        await self.cache.set(key, value, ex=ttl)

    async def warm_up(self, keys: list):
        """缓存预热"""
        logger.info(f"Warming up cache for {len(keys)} keys")

        tasks = [self.fetch_and_cache(key) for key in keys]
        await asyncio.gather(*tasks)

    async def fetch_and_cache(self, key: str):
        """获取并缓存"""
        value = await fetch_from_source(key)
        if value:
            await self.cache.set(key, value, ex=3600)

# 缓存更新策略
class CacheUpdateStrategy:
    """缓存更新策略"""

    @staticmethod
    async def write_through(key: str, value: any):
        """写穿策略：同时写缓存和数据库"""
        await cache.set(key, value)
        await database.save(key, value)

    @staticmethod
    async def write_behind(key: str, value: any):
        """写回策略：先写缓存，异步写数据库"""
        await cache.set(key, value)

        # 异步写数据库
        asyncio.create_task(database.save(key, value))

    @staticmethod
    async def write_around(key: str, value: any):
        """绕写策略：只写数据库，不写缓存"""
        await database.save(key, value)
        # 不更新缓存，让它自然过期
```

### **4.2.2 缓存Key设计 🔑**

```python
"""
缓存Key设计最佳实践
"""

class CacheKeyDesign:
    """缓存Key设计"""

    # ✅ 好的Key设计
    GOOD_KEYS = {
        "user_info": "user:{user_id}:info",
        "conversation": "conv:{conv_id}:v1",  # 带版本号
        "orders": "user:{user_id}:orders:{year}:{month}",  # 分片
        "llm_response": "llm:{model}:{hash}",
    }

    # ❌ 差的Key设计
    BAD_KEYS = {
        "user": "user",  # 太通用
        "data": "data123",  # 无意义
        "temp": "temp",  # 不清晰
    }

    @staticmethod
    def generate_user_cache_key(user_id: str) -> str:
        """生成用户缓存key"""
        return f"user:{user_id}:info:v1"

    @staticmethod
    def generate_conversation_key(conv_id: str, version: int = 1) -> str:
        """生成对话缓存key（带版本）"""
        return f"conv:{conv_id}:v{version}"

    @staticmethod
    def generate_llm_cache_key(prompt: str, model: str) -> str:
        """生成LLM缓存key"""
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:16]
        return f"llm:{model}:{prompt_hash}"

    @staticmethod
    def generate_sharded_key(user_id: str, date: datetime) -> str:
        """生成分片key（按时间分片）"""
        return f"user:{user_id}:messages:{date.year}:{date.month}"

# 缓存失效模式
class CacheInvalidation:
    """缓存失效"""

    @staticmethod
    async def invalidate_pattern(pattern: str):
        """按模式失效缓存"""
        # 例如：user:123:* 失效该用户的所有缓存
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)

    @staticmethod
    async def invalidate_related(entity_type: str, entity_id: str):
        """失效相关缓存"""
        patterns = [
            f"{entity_type}:{entity_id}:*",
            f"*:{entity_type}:{entity_id}:*",
        ]

        for pattern in patterns:
            await CacheInvalidation.invalidate_pattern(pattern)

    @staticmethod
    async def tag_based_invalidation(tags: list):
        """基于标签的失效"""
        # 为缓存添加标签
        # 失效时只需要失效特定标签的缓存
        for tag in tags:
            keys = await redis.smembers(f"tag:{tag}")
            if keys:
                await redis.delete(*keys)
                await redis.delete(```python
                await redis.delete(f"tag:{tag}")
```

---

## 4.3 网络和I/O优化

### **4.3.1 连接池优化 🔌**

```python
"""
连接池优化
"""

# HTTP连接池配置
import aiohttp
from aiohttp import TCPConnector

class OptimizedHTTPClient:
    """优化的HTTP客户端"""

    def __init__(self):
        # 优化的连接器配置
        connector = TCPConnector(
            limit=100,              # 总连接数限制
            limit_per_host=30,      # 每个主机的连接数
            ttl_dns_cache=300,      # DNS缓存5分钟
            use_dns_cache=True,
            keepalive_timeout=30,   # 保活超时
            force_close=False,      # 重用连接
        )

        # 会话配置
        timeout = aiohttp.ClientTimeout(
            total=60,       # 总超时
            connect=10,     # 连接超时
            sock_read=30,   # 读超时
        )

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "AgentPlatform/1.0",
                "Accept-Encoding": "gzip, deflate",  # 启用压缩
            }
        )

    async def request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        **kwargs
    ):
        """带重试的请求"""
        for attempt in range(max_retries):
            try:
                async with self.session.request(method, url, **kwargs) as resp:
                    resp.raise_for_status()
                    return await resp.json()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == max_retries - 1:
                    raise

                wait_time = 2 ** attempt  # 指数退避
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)

    async def close(self):
        """关闭会话"""
        await self.session.close()

# WebSocket连接池
class WebSocketPool:
    """WebSocket连接池"""

    def __init__(self, max_connections: int = 1000):
        self.connections: Dict[str, WebSocket] = {}
        self.max_connections = max_connections
        self.semaphore = asyncio.Semaphore(max_connections)

    async def acquire(self, client_id: str, websocket: WebSocket):
        """获取连接"""
        async with self.semaphore:
            if len(self.connections) >= self.max_connections:
                # 移除最老的连接
                oldest = min(self.connections.items(), key=lambda x: x[1].created_at)
                await oldest[1].close()
                del self.connections[oldest[0]]

            self.connections[client_id] = websocket

    async def release(self, client_id: str):
        """释放连接"""
        if client_id in self.connections:
            del self.connections[client_id]

    async def broadcast(self, message: dict, exclude: list = None):
        """广播消息"""
        exclude = exclude or []
        tasks = []

        for client_id, ws in self.connections.items():
            if client_id not in exclude:
                tasks.append(ws.send_json(message))

        await asyncio.gather(*tasks, return_exceptions=True)
```

### **4.3.2 数据传输优化 📡**

```python
"""
数据传输优化
"""

import gzip
import json
from typing import Any

class DataTransferOptimizer:
    """数据传输优化"""

    @staticmethod
    def compress_response(data: dict) -> bytes:
        """压缩响应数据"""
        json_data = json.dumps(data, ensure_ascii=False)
        compressed = gzip.compress(json_data.encode('utf-8'))

        compression_ratio = len(compressed) / len(json_data)
        logger.debug(f"Compression ratio: {compression_ratio:.2%}")

        return compressed

    @staticmethod
    def decompress_request(compressed_data: bytes) -> dict:
        """解压请求数据"""
        decompressed = gzip.decompress(compressed_data)
        return json.loads(decompressed.decode('utf-8'))

    @staticmethod
    def serialize_efficiently(obj: Any) -> str:
        """高效序列化"""
        # 使用orjson代替标准json（更快）
        import orjson
        return orjson.dumps(obj).decode()

    @staticmethod
    def paginate_large_response(data: list, page_size: int = 100):
        """分页返回大数据"""
        for i in range(0, len(data), page_size):
            yield data[i:i + page_size]

    @staticmethod
    async def stream_large_data(data: list):
        """流式返回大数据"""
        async def generate():
            for item in data:
                yield json.dumps(item) + '\n'
                await asyncio.sleep(0)  # 让出控制权

        return generate()

# FastAPI响应优化
from fastapi import Response
from fastapi.responses import StreamingResponse, ORJSONResponse

@app.get("/api/v1/data")
async def get_data_optimized():
    """优化的数据端点"""
    data = await fetch_large_dataset()

    # 使用ORJSONResponse（比标准JSONResponse快）
    return ORJSONResponse(content=data)

@app.get("/api/v1/stream")
async def stream_data():
    """流式数据端点"""
    async def generate():
        async for chunk in fetch_data_stream():
            yield json.dumps(chunk) + '\n'

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"  # Newline Delimited JSON
    )

# 启用HTTP/2
# 在Nginx配置中：
"""
server {
    listen 443 ssl http2;
    server_name api.example.com;

    # HTTP/2推送
    http2_push_preload on;

    # 压缩
    gzip on;
    gzip_types application/json text/plain;
    gzip_min_length 1000;
}
"""
```

---

## 4.4 Agent执行优化

### **4.4.1 并行执行优化 ⚡**

```python
"""
Agent并行执行优化
"""

from langgraph.graph import StateGraph, END
from langgraph.constants import START

class ParallelAgent:
    """支持并行执行的Agent"""

    def create_parallel_graph(self):
        """创建支持并行的状态图"""
        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("understand", self.understand)
        workflow.add_node("query_user", self.query_user)
        workflow.add_node("query_orders", self.query_orders)
        workflow.add_node("query_preferences", self.query_preferences)
        workflow.add_node("synthesize", self.synthesize)

        # 设置入口
        workflow.set_entry_point("understand")

        # 理解后并行执行多个查询
        workflow.add_edge("understand", "query_user")
        workflow.add_edge("understand", "query_orders")
        workflow.add_edge("understand", "query_preferences")

        # 所有查询完成后合成
        workflow.add_edge("query_user", "synthesize")
        workflow.add_edge("query_orders", "synthesize")
        workflow.add_edge("query_preferences", "synthesize")

        workflow.add_edge("synthesize", END)

        return workflow.compile()

    async def understand(self, state: AgentState):
        """理解阶段"""
        # ... 理解逻辑
        return state

    async def query_user(self, state: AgentState):
        """查询用户信息（可并行）"""
        user_info = await get_user_info(state["user_id"])
        return {"user_info": user_info}

    async def query_orders(self, state: AgentState):
        """查询订单（可并行）"""
        orders = await get_orders(state["user_id"])
        return {"orders": orders}

    async def query_preferences(self, state: AgentState):
        """查询偏好（可并行）"""
        prefs = await get_preferences(state["user_id"])
        return {"preferences": prefs}

    async def synthesize(self, state: AgentState):
        """合成结果"""
        # 等待所有并行任务完成后执行
        response = self.generate_response(
            state["user_info"],
            state["orders"],
            state["preferences"]
        )
        return {"messages": [response]}

# 工具并行调用
class ParallelToolExecutor:
    """并行工具执行器"""

    async def execute_tools_parallel(
        self,
        tool_calls: list,
        max_concurrent: int = 5
    ):
        """并行执行多个工具"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(tool_call):
            async with semaphore:
                return await self.execute_tool(tool_call)

        tasks = [
            execute_with_semaphore(tc)
            for tc in tool_calls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Tool {tool_calls[i]['name']} failed: {result}")
                results[i] = {"error": str(result)}

        return results

    async def execute_tool(self, tool_call: dict):
        """执行单个工具"""
        tool_name = tool_call["name"]
        tool_input = tool_call["input"]

        start_time = time.time()

        try:
            result = await tool_executor.ainvoke({
                "tool": tool_name,
                "tool_input": tool_input
            })

            duration = time.time() - start_time
            logger.info(f"Tool {tool_name} completed in {duration:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            raise
```

### **4.4.2 执行计划优化 📋**

```python
"""
Agent执行计划优化
"""

class ExecutionPlanner:
    """执行计划优化器"""

    def __init__(self):
        self.execution_stats = {}  # 执行统计

    async def optimize_execution_order(self, tasks: list) -> list:
        """优化执行顺序"""

        # 1. 分析任务依赖
        dependencies = self.analyze_dependencies(tasks)

        # 2. 识别可并行任务
        parallel_groups = self.identify_parallel_groups(tasks, dependencies)

        # 3. 按优先级排序
        sorted_tasks = self.sort_by_priority(parallel_groups)

        return sorted_tasks

    def analyze_dependencies(self, tasks: list) -> dict:
        """分析任务依赖"""
        dependencies = {}

        for task in tasks:
            deps = []
            for other_task in tasks:
                if self.has_dependency(task, other_task):
                    deps.append(other_task["id"])

            dependencies[task["id"]] = deps

        return dependencies

    def identify_parallel_groups(self, tasks: list, dependencies: dict) -> list:
        """识别可并行的任务组"""
        groups = []
        remaining = set(t["id"] for t in tasks)

        while remaining:
            # 找出没有依赖的任务
            no_deps = [
                tid for tid in remaining
                if not dependencies[tid] or
                all(d not in remaining for d in dependencies[tid])
            ]

            if not no_deps:
                # 循环依赖，打破循环
                no_deps = [remaining.pop()]

            groups.append(no_deps)
            remaining -= set(no_deps)

        return groups

    def sort_by_priority(self, parallel_groups: list) -> list:
        """按优先级排序"""
        # 基于历史统计数据优化顺序
        for group in parallel_groups:
            group.sort(key=lambda tid: self.get_task_priority(tid), reverse=True)

        return parallel_groups

    def get_task_priority(self, task_id: str) -> float:
        """获取任务优先级"""
        stats = self.execution_stats.get(task_id, {})

        # 考虑因素：
        # 1. 执行时间（快的优先）
        # 2. 成功率（高的优先）
        # 3. 重要性（重要的优先）

        execution_time = stats.get("avg_time", 1.0)
        success_rate = stats.get("success_rate", 0.5)
        importance = stats.get("importance", 0.5)

        # 综合评分
        priority = (success_rate * 0.4 + importance * 0.4) / execution_time * 0.2

        return priority

    async def execute_optimized_plan(self, plan: list):
        """执行优化后的计划"""
        results = {}

        for group in plan:
            # 并行执行组内任务
            group_tasks = [self.execute_task(tid) for tid in group]
            group_results = await asyncio.gather(*group_tasks)

            # 记录结果
            for tid, result in zip(group, group_results):
                results[tid] = result

        return results

# 智能重试策略
class SmartRetry:
    """智能重试"""

    def __init__(self):
        self.failure_history = {}

    async def execute_with_smart_retry(
        self,
        func,
        *args,
        max_retries: int = 3,
        **kwargs
    ):
        """智能重试执行"""

        func_name = func.__name__

        # 根据历史失败情况调整策略
        if func_name in self.failure_history:
            recent_failures = self.failure_history[func_name][-10:]
            failure_rate = len([f for f in recent_failures if f]) / len(recent_failures)

            if failure_rate > 0.5:
                # 高失败率，增加重试间隔
                base_delay = 5
            else:
                base_delay = 2
        else:
            base_delay = 2

        for attempt in range(max_retries):
            try:
                result = await func(*args, **kwargs)

                # 记录成功
                self.record_attempt(func_name, success=True)

                return result

            except Exception as e:
                # 记录失败
                self.record_attempt(func_name, success=False)

                if attempt == max_retries - 1:
                    raise

                # 根据异常类型调整延迟
                if isinstance(e, asyncio.TimeoutError):
                    delay = base_delay * (2 ** attempt)  # 超时：指数退避
                elif isinstance(e, RateLimitError):
                    delay = 60  # 限流：固定延迟
                else:
                    delay = base_delay * (attempt + 1)  # 其他：线性增长

                logger.warning(
                    f"Attempt {attempt + 1} failed for {func_name}, "
                    f"retrying in {delay}s: {e}"
                )

                await asyncio.sleep(delay)

    def record_attempt(self, func_name: str, success: bool):
        """记录执行结果"""
        if func_name not in self.failure_history:
            self.failure_history[func_name] = []

        self.failure_history[func_name].append(not success)

        # 只保留最近100次记录
        self.failure_history[func_name] = self.failure_history[func_name][-100:]
```

---

## 4.5 监控和调优工具

### **4.5.1 性能分析工具 📊**

```python
"""
性能分析工具
"""

import cProfile
import pstats
from functools import wraps
import time

class PerformanceProfiler:
    """性能分析器"""

    @staticmethod
    def profile_function(func):
        """函数性能分析装饰器"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            profiler = cProfile.Profile()
            profiler.enable()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                profiler.disable()

                # 打印统计信息
                stats = pstats.Stats(profiler)
                stats.sort_stats('cumulative')
                stats.print_stats(20)  # 打印前20个

        return wrapper

    @staticmethod
    def time_function(func):
        """计时装饰器"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                logger.info(f"{func.__name__} took {duration:.3f}s")

        return wrapper

    @staticmethod
    def memory_profile(func):
        """内存分析装饰器"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import tracemalloc

            tracemalloc.start()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                logger.info(
                    f"{func.__name__} memory: "
                    f"current={current / 1024 / 1024:.2f}MB, "
                    f"peak={peak / 1024 / 1024:.2f}MB"
                )

        return wrapper

# 实时性能监控
class RealtimeMonitor:
    """实时性能监控"""

    def __init__(self):
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "total_time": 0.0,
            "active_requests": 0,
        }
        self.lock = asyncio.Lock()

    async def record_request(self, duration: float, error: bool = False):
        """记录请求"""
        async with self.lock:
            self.metrics["requests"] += 1
            self.metrics["total_time"] += duration

            if error:
                self.metrics["errors"] += 1

    async def start_request(self):
        """开始请求"""
        async with self.lock:
            self.metrics["active_requests"] += 1

    async def end_request(self):
        """结束请求"""
        async with self.lock:
            self.metrics["active_requests"] -= 1

    def get_stats(self) -> dict:
        """获取统计信息"""
        requests = self.metrics["requests"]

        if requests == 0:
            return {"qps": 0, "avg_time": 0, "error_rate": 0}

        return {
            "total_requests": requests,
            "qps": requests / (time.time() - self.start_time),
            "avg_time": self.metrics["total_time"] / requests,
            "error_rate": self.metrics["errors"] / requests,
            "active_requests": self.metrics["active_requests"]
        }

# 慢查询日志
class SlowQueryLogger:
    """慢查询日志"""

    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold  # 慢查询阈值（秒）

    async def log_query(self, query: str, duration: float, params: dict = None):
        """记录查询"""
        if duration > self.threshold:
            logger.warning(
                f"Slow query detected ({duration:.3f}s): {query}",
                extra={
                    "query": query,
                    "duration": duration,
                    "params": params,
                    "threshold": self.threshold
                }
            )

            # 发送到监控系统
            await self.send_to_monitoring({
                "type": "slow_query",
                "query": query,
                "duration": duration,
                "timestamp": datetime.now().isoformat()
            })

    async def send_to_monitoring(self, data: dict):
        """发送到监控系统"""
        # 发送到Prometheus/Grafana等
        pass

# APM集成
class APMIntegration:
    """APM（Application Performance Monitoring）集成"""

    def __init__(self):
        # 集成OpenTelemetry或其他APM
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # 配置tracer
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()

        # 配置exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint="http://localhost:4317"
        )

        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        self.tracer = trace.get_tracer(__name__)

    def trace_function(self, name: str = None):
        """追踪函数装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                span_name = name or func.__name__

                with self.tracer.start_as_current_span(span_name) as span:
                    # 添加属性
                    span.set_attribute("function", func.__name__)

                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("status", "success")
                        return result

                    except Exception as e:
                        span.set_attribute("status", "error")
                        span.record_exception(e)
                        raise

            return wrapper
        return decorator
```

---

### **4.5.2 自动化调优建议 🎯**

```python
"""
自动化性能调优建议
"""

class PerformanceAdvisor:
    """性能顾问"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()

    async def analyze_and_recommend(self) -> list:
        """分析并提供优化建议"""
        recommendations = []

        # 收集指标
        metrics = await self.metrics_collector.collect_all()

        # 分析数据库性能
        db_recommendations = self.analyze_database(metrics["database"])
        recommendations.extend(db_recommendations)

        # 分析API性能
        api_recommendations = self.analyze_api(metrics["api"])
        recommendations.extend(api_recommendations)

        # 分析Agent性能
        agent_recommendations = self.analyze_agent(metrics["agent"])
        recommendations.extend(agent_recommendations)

        # 分析缓存效率
        cache_recommendations = self.analyze_cache(metrics["cache"])
        recommendations.extend(cache_recommendations)

        return recommendations

    def analyze_database(self, metrics: dict) -> list:
        """分析数据库性能"""
        recommendations = []

        # 检查慢查询
        if metrics["slow_queries"] > 10:
            recommendations.append({
                "severity": "high",
                "category": "database",
                "issue": f"检测到{metrics['slow_queries']}个慢查询",
                "recommendation": "优化查询SQL，添加索引",
                "action": "review_slow_queries"
            })

        # 检查连接池
        if metrics["connection_pool_usage"] > 0.8:
            recommendations.append({
                "severity": "medium",
                "category": "database",
                "issue": f"连接池使用率{metrics['connection_pool_usage']:.1%}",
                "recommendation": "增加连接池大小",
                "action": "increase_pool_size"
            })

        # 检查N+1查询
        if metrics["queries_per_request"] > 10:
            recommendations.append({
                "severity": "high",
                "category": "database",
                "issue": f"平均每请求{metrics['queries_per_request']}次查询",
                "recommendation": "使用JOIN或预加载减少查询次数",
                "action": "optimize_n_plus_1"
            })

        return recommendations

    def analyze_api(self, metrics: dict) -> list:
        """分析API性能"""
        recommendations = []

        # 检查响应时间
        if metrics["p99_latency"] > 3000:
            recommendations.append({
                "severity": "critical",
                "category": "api",
                "issue": f"P99延迟{metrics['p99_latency']}ms",
                "recommendation": "识别瓶颈，优化慢端点",
                "action": "profile_slow_endpoints"
            })

        # 检查错误率
        if metrics["error_rate"] > 0.05:
            recommendations.append({
                "severity": "high",
                "category": "api",
                "issue": f"错误率{metrics['error_rate']:.1%}",
                "recommendation": "检查错误日志，修复常见错误",
                "action": "fix_errors"
            })

        return recommendations

    def analyze_agent(self, metrics: dict) -> list:
        """分析Agent性能"""
        recommendations = []

        # 检查LLM调用
        if metrics["llm_calls_per_conversation"] > 10:
            recommendations.append({
                "severity": "medium",
                "category": "agent",
                "issue": f"平均每对话{metrics['llm_calls_per_conversation']}次LLM调用",
                "recommendation": "优化Agent逻辑，减少不必要的LLM调用",
                "action": "optimize_llm_calls"
            })

        # 检查工具调用效率
        if metrics["tool_success_rate"] < 0.9:
            recommendations.append({
                "severity": "medium",
                "category": "agent",
                "issue": f"工具调用成功率{metrics['tool_success_rate']:.1%}",
                "recommendation": "改进工具错误处理，增加重试机制",
                "action": "improve_tool_reliability"
            })

        return recommendations

    def analyze_cache(self, metrics: dict) -> list:
        """分析缓存效率"""
        recommendations = []

        # 检查缓存命中率
        if metrics["cache_hit_rate"] < 0.7:
            recommendations.append({
                "severity": "medium",
                "category": "cache",
                "issue": f"缓存命中率{metrics['cache_hit_rate']:.1%}",
                "recommendation": "优化缓存策略，增加缓存覆盖",
                "action": "improve_cache_strategy"
            })

        # 检查缓存大小
        if metrics["cache_memory_usage"] > 0.9:
            recommendations.append({
                "severity": "high",
                "category": "cache",
                "issue": f"缓存内存使用{metrics['cache_memory_usage']:.1%}",
                "recommendation": "增加缓存容量或优化缓存失效策略",
                "action": "scale_cache"
            })

        return recommendations
```

---

# 五、团队培训材料

## 5.1 LangGraph快速入门指南

### **5.1.1 核心概念（30分钟）📚**

```markdown
# LangGraph核心概念

## 1. 什么是LangGraph？

LangGraph是一个用于构建**有状态**、**多步骤**Agent应用的框架。

### 关键特性：
- ✅ **状态管理**：所有节点共享和修改状态
- ✅ **图结构**：灵活的流程控制（循环、条件、并行）
- ✅ **持久化**：自动保存检查点，支持恢复
- ✅ **流式输出**：实时返回结果
- ✅ **人机协作**：支持人类介入

### vs 传统工作流（n8n）：

| 特性 | LangGraph | n8n |
|------|-----------|-----|
| 状态管理 | 强大 | 弱 |
| 动态路由 | ✅ | ❌ |
| 循环支持 | ✅ | 有限 |
| 流式输出 | ✅ | ❌ |
| 适用场景 | 智能Agent | 自动化工作流 |

## 2. 核心组件

### State（状态）
```python
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    """定义Agent的状态结构"""

    # 累加字段（每次添加，不覆盖）
    messages: Annotated[list, operator.add]

    # 覆盖字段（每次更新）
    current_intent: str
    user_id: str

    # 标志字段
    needs_human: bool
    resolved: bool
```

**重要概念：**

- 状态在所有节点间共享
- 使用`Annotated[list, operator.add]`实现累加
- 普通字段会被覆盖

### Node（节点）

```python
def my_node(state: AgentState) -> AgentState:
    """
    节点函数：
    - 输入：当前状态
    - 输出：状态更新（部分或全部）
    """

    # 读取状态
    user_message = state["messages"][-1]

    # 执行逻辑
    result = process(user_message)

    # 返回状态更新
    return {
        "messages": [AIMessage(content=result)],
        "current_intent": "query_complete"
    }
```

### Edge（边）

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)

# 1. 普通边（固定路径）
workflow.add_edge("node_a", "node_b")

# 2. 条件边（动态路由）
def router(state: AgentState) -> str:
    """根据状态决定下一步"""
    if state["needs_human"]:
        return "human_node"
    else:
        return "ai_node"

workflow.add_conditional_edges(
    "decision_node",
    router,
    {
        "human_node": "transfer_human",
        "ai_node": "continue_ai"
    }
)

# 3. 到结束的边
workflow.add_edge("final_node", END)
```

### Graph（图）

```python
# 创建图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("understand", understand_intent)
workflow.add_node("respond", generate_response)

# 设置入口
workflow.set_entry_point("understand")

# 添加边
workflow.add_edge("understand", "respond")
workflow.add_edge("respond", END)

# 编译
app = workflow.compile()

# 执行
result = app.invoke({"messages": ["Hello"]})
```

## 3. 状态更新机制

### 累加 vs 覆盖

```python
# 定义状态
class MyState(TypedDict):
    counter: Annotated[int, operator.add]  # 累加
    name: str  # 覆盖

# 节点A
def node_a(state: MyState):
    return {"counter": 1, "name": "A"}
# 结果：{"counter": 1, "name": "A"}

# 节点B
def node_b(state: MyState):
    return {"counter": 2, "name": "B"}
# 结果：{"counter": 3, "name": "B"}  # counter累加，name覆盖
```

## 4. 执行模式

### 同步执行

```python
result = app.invoke(initial_state)
print(result)
```

### 异步执行

```python
result = await app.ainvoke(initial_state)
```

### 流式执行

```python
async for event in app.astream_events(initial_state, version="v1"):
    if event["event"] == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="")
```

### 带检查点执行

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver(engine)
app = workflow.compile(checkpointer=checkpointer)

# 执行（自动保存检查点）
config = {"configurable": {"thread_id": "conversation_123"}}
result = await app.ainvoke(initial_state, config)

# 恢复（从检查点继续）
result = await app.ainvoke(new_input, config)
```

## 5. 常见模式

### 模式1：简单链式

```
用户输入 → 理解意图 → 生成响应 → 结束
```

### 模式2：条件分支

```
用户输入 → 理解意图 
            ├─→ [简单问题] → 直接回答 → 结束
            └─→ [复杂问题] → 调用工具 → 生成响应 → 结束
```

### 模式3：循环反思

```
用户输入 → 尝试解决 → 检查结果 
            ├─→ [成功] → 结束
            └─→ [失败] → 反思 → 重新尝试（循环）
```

### 模式4：并行执行

```
用户输入 → 理解意图 → ┬─→ 查询用户信息
                        ├─→ 查询订单
                        └─→ 查询偏好
                        ↓
                        合并结果 → 生成响应 → 结束
```

## 6. 调试技巧

### 打印状态

```python
def debug_node(state: AgentState):
    print("Current state:", state)
    return state

workflow.add_node("debug", debug_node)
```

### 查看执行历史

```python
# 获取所有检查点
checkpoints = checkpointer.list(config)
for checkpoint in checkpoints:
    print(checkpoint)
```

### 可视化图结构

```python
from IPython.display import Image, display

display(Image(app.get_graph().draw_mermaid_png()))
```

```
---

### **5.1.2 实战练习（2小时）💻**

```python
"""
练习1：构建一个简单的问答Agent（30分钟）
"""

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated
import operator

# 步骤1：定义状态
class QAState(TypedDict):
    messages: Annotated[list, operator.add]
    question_type: str  # "simple" or "complex"

# 步骤2：创建LLM
llm = ChatOpenAI(model="gpt-4o-mini")

# 步骤3：定义节点
def classify_question(state: QAState):
    """分类问题"""
    question = state["messages"][-1]

    # 简单判断（实际应用中用LLM分类）
    if len(question.split()) < 10:
        question_type = "simple"
    else:
        question_type = "complex"

    return {"question_type": question_type}

def answer_simple(state: QAState):
    """回答简单问题"""
    question = state["messages"][-1]
    response = llm.invoke(f"简短回答：{question}")
    return {"messages": [response]}

def answer_complex(state: QAState):
    """回答复杂问题"""
    question = state["messages"][-1]
    response = llm.invoke(f"详细回答：{question}")
    return {"messages": [response]}

# 步骤4：构建图
def create_qa_agent():
    workflow = StateGraph(QAState)

    # 添加节点
    workflow.add_node("classify", classify_question)
    workflow.add_node("simple", answer_simple)
    workflow.add_node("complex", answer_complex)

    # 设置入口
    workflow.set_entry_point("classify")

    # 添加条件边
    def route_by_type(state: QAState):
        return state["question_type"]

    workflow.add_conditional_edges(
        "classify",
        route_by_type,
        {
            "simple": "simple",
            "complex": "complex"
        }
    )

    # 添加结束边
    workflow.add_edge("simple", END)
    workflow.add_edge("complex", END)

    return workflow.compile()

# 步骤5：测试
app = create_qa_agent()

# 测试简单问题
result = app.invoke({
    "messages": ["What is 2+2?"],
    "question_type": ""
})
print("Simple Q:", result["messages"][-1].content)

# 测试复杂问题
result = app.invoke({
    "messages": ["Explain quantum computing in detail"],
    "question_type": ""
})
print("Complex Q:", result["messages"][-1].content)

"""
✅ 练习1完成标准：
- [ ] Agent能正确分类问题
- [ ] 简单问题得到简短回答
- [ ] 复杂问题得到详细回答
"""

# ========================================

"""
练习2：添加工具调用（45分钟）
"""

from langchain.tools import tool

# 步骤1：定义工具
@tool
def calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)

@tool
def get_weather(city: str) -> str:
    """获取天气（模拟）"""
    return f"{city}的天气：晴天，25°C"

# 步骤2：扩展状态
class AgentStateWithTools(TypedDict):
    messages: Annotated[list, operator.add]
    needs_tool: bool
    tool_result: str

# 步骤3：添加工具调用节点
def check_needs_tool(state: AgentStateWithTools):
    """检查是否需要工具"""
    question = state["messages"][-1]

    # 简单判断（实际用LLM判断）
    keywords = ["计算", "天气", "查询"]
    needs_tool = any(k in question for k in keywords)

    return {"needs_tool": needs_tool}

def call_tool(state: AgentStateWithTools):
    """调用工具"""
    question = state["messages"][-1]

    # 判断用哪个工具（实际用LLM选择）
    if "计算" in question or "+" in question:
        result = calculator.invoke({"expression": "2+2"})
    else:
        result = get_weather.invoke({"city": "北京"})

    return {"tool_result": result}

def generate_final_answer(state: AgentStateWithTools):
    """生成最终答案"""
    question = state["messages"][-1]
    tool_result = state.get("tool_result", "")

    if tool_result:
        prompt = f"问题：{question}\n工具结果：{tool_result}\n请基于工具结果回答。"
    else:
        prompt = question

    response = llm.invoke(prompt)
    return {"messages": [response]}

# 步骤4：构建带工具的图
def create_tool_agent():
    workflow = StateGraph(AgentStateWithTools)

    workflow.add_node("check", check_needs_tool)
    workflow.add_node("tool", call_tool)
    workflow.add_node("answer", generate_final_answer)

    workflow.set_entry_point("check")

    def route_by_tool_need(state):
        return "use_tool" if state["needs_tool"] else "direct_answer"

    workflow.add_conditional_edges(
        "check",
        route_by_tool_need,
        {
            "use_tool": "tool",
            "direct_answer": "answer"
        }
    )

    workflow.add_edge("tool", "answer")
    workflow.add_edge("answer", END)

    return workflow.compile()

# 步骤5：测试
tool_app = create_tool_agent()

result = tool_app.invoke({
    "messages": ["2+2等于多少？"],
    "needs_tool": False,
    "tool_result": ""
})
print(result["messages"][-1].content)

"""
✅ 练习2完成标准：
- [ ] Agent能识别何时需要工具
- [ ] 正确选择和调用工具
- [ ] 基于工具结果生成答案
"""

# ========================================

"""
练习3：添加状态持久化（45分钟）
"""

from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.ext.asyncio import create_async_engine

# 步骤1：配置数据库
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db"
)

# 步骤2：创建checkpointer
async def setup_checkpointer():
    checkpointer = PostgresSaver(engine)
    await checkpointer.setup()  # 创建表
    return checkpointer

# 步骤3：编译带检查点的图
async def create_stateful_agent():
    checkpointer = await setup_checkpointer()

    # 使用之前的工具Agent
    workflow = StateGraph(AgentStateWithTools)
    # ... 添加节点和边 ...

    # 编译时传入checkpointer
    app = workflow.compile(checkpointer=checkpointer)

    return app

# 步骤4：测试持久化
async def test_persistence():
    app = await create_stateful_agent()

    config = {"configurable": {"thread_id": "test_conversation"}}

    # 第一次对话
    result1 = await app.ainvoke({
        "messages": ["我叫张三"],
        "needs_tool": False,
        "tool_result": ""
    }, config)

    # 第二次对话（应该记住"张三"）
    result2 = await app.ainvoke({
        "messages": ["我叫什么名字？"],
        "needs_tool": False,
        "tool_result": ""
    }, config)

    print(result2["messages"][-1].content)
    # 期望输出：包含"张三"

# 运行
import asyncio
asyncio.run(test_persistence())

"""
✅ 练习3完成标准：
- [ ] 对话状态能正确保存到数据库
- [ ] 后续对话能恢复之前的上下文
- [ ] 可以查询历史检查点
"""
```

---

## 5.2 FastAPI + WebSocket实战

### **5.2.1 WebSocket基础（1小时）🔌**

```python
"""
FastAPI + WebSocket完整示例
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import asyncio
import json

app = FastAPI()

# ========================================
# 第1部分：连接管理（15分钟）
# ========================================

class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 存储活跃连接
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        """接受连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected. Total: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: dict, client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_json(message)

    async def broadcast(self, message: dict):
        """广播消息"""
        disconnected = []

        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except:
                disconnected.append(client_id)

        # 清理断开的连接
        for client_id in disconnected:
            self.disconnect(client_id)

manager = ConnectionManager()

# ========================================
# 第2部分：基础WebSocket端点（15分钟）
# ========================================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """基础WebSocket端点"""
    await manager.connect(client_id, websocket)

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            message = data.get("message", "")

            print(f"Received from {client_id}: {message}")

            # 回显消息
            await manager.send_personal_message({
                "type": "echo",
                "content": f"You said: {message}"
            }, client_id)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"Client {client_id} disconnected")

# ========================================
# 第3部分：聊天室示例（15分钟）
# ========================================

@app.websocket("/ws/chat/{room_id}/{client_id}")
async def chat_room(websocket: WebSocket, room_id: str, client_id: str):
    """聊天室"""
    await manager.connect(f"{room_id}:{client_id}", websocket)

    # 通知其他人
    await manager.broadcast({
        "type": "user_joined",
        "room": room_id,
        "user": client_id
    })

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            # 广播消息
            await manager.broadcast({
                "type": "message",
                "room": room_id,
                "user": client_id,
                "content": message
            })

    except WebSocketDisconnect:
        manager.disconnect(f"{room_id}:{client_id}")

        # 通知其他人
        await manager.broadcast({
            "type": "user_left",
            "room": room_id,
            "user": client_id
        })

# ========================================
# 第4部分：流式数据传输（15分钟）
# ========================================

@app.websocket("/ws/stream/{client_id}")
async def stream_data(websocket: WebSocket, client_id: str):
    """流式数据传输"""
    await manager.connect(client_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            prompt = data.get("prompt", "")

            # 模拟LLM流式输出
            full_response = f"这是对'{prompt}'的详细回答。" * 10

            # 逐字发送
            for i, char in enumerate(full_response):
                await manager.send_personal_message({
                    "type": "token",
                    "content": char,
                    "index": i
                }, client_id)

                await asyncio.sleep(0.01)  # 模拟延迟

            # 发送完成信号
            await manager.send_personal_message({
                "type": "complete"
            }, client_id)

    except WebSocketDisconnect:
        manager.disconnect(client_id)

# ========================================
# 测试HTML页面
# ========================================

@app.get("/")
async def get_test_page():
    """测试页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Test</title>
    </head>
    <body>
        <h1>WebSocket Test</h1>
        <div>
            <input id="clientId" placeholder="Your ID" value="user123"/>
            <button onclick="connect()">Connect</button>
            <button onclick="disconnect()">Disconnect</button>
        </div>
        <div>
            <input id="messageInput" placeholder="Type a message"/>
            <button onclick="sendMessage()">Send</button>
        </div>
        <div id="messages" style="border:1px solid #ccc; padding:10px; margin-top:10px; height:300px; overflow-y:auto;"></div>

        <script>
            let ws = null;

            function connect() {
                const clientId = document.getElementById('clientId').value;
                ws = new WebSocket(`ws://localhost:8000/ws/stream/${clientId}`);

                ws.onopen = () => {
                    addMessage('Connected!', 'system');
                };

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);

                    if (data.type === 'token') {
                        appendToken(data.content);
                    } else if (data.type === 'complete') {
                        addMessage('', 'complete');
                    } else {
                        addMessage(JSON.stringify(data), 'received');
                    }
                };

                ws.onclose = () => {
                    addMessage('Disconnected!', 'system');
                };

                ws.onerror = (error) => {
                    addMessage('Error: ' + error, 'error');
                };
            }

            function disconnect() {
                if (ws) {
                    ws.close();
                }
            }

            function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value;

                if (ws && message) {
                    ws.send(JSON.stringify({prompt: message}));
                    addMessage(message, 'sent');
                    input.value = '';
                }
            }

            let currentMessage = null;

            function addMessage(text, type) {
                const messages = document.getElementById('messages');
                const div = document.createElement('div');
                div.style.marginBottom = '5px';
                div.style.padding = '5px';

                if (type === 'sent') {
                    div.style.backgroundColor = '#e3f2fd';
                    div.textContent = 'You: ' + text;
                } else if (type === 'received') {
                    div.style.backgroundColor = '#f1f8e9';
                    div.textContent = 'Server: ' + text;
                } else if (type === 'system') {
                    div.style.backgroundColor = '#fff3e0';
                    div.textContent = text;
                } else if (type === 'complete') {
                    currentMessage = null;
                    return;
                }

                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;

                if (type === 'received') {
                    currentMessage = div;
                }
            }

            function appendToken(token) {
                const messages = document.getElementById('messages');

                if (!currentMessage) {
                    currentMessage = document.createElement('div');
                    currentMessage.style.marginBottom = '5px';
                    currentMessage.style.padding = '5px';
                    currentMessage.style.backgroundColor = '#f1f8e9';
                    currentMessage.textContent = 'Server: ';
                    messages.appendChild(currentMessage);
                }

                currentMessage.textContent += token;
                messages.scrollTop = messages.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

# ========================================
# 练习任务
# ========================================

"""
✅ 练习1：基础连接（15分钟）
- [ ] 启动服务器：uvicorn main:app --reload
- [ ] 打开浏览器访问 http://localhost:8000
- [ ] 测试连接和断开
- [ ] 测试发送消息

✅ 练习2：多客户端（15分钟）
- [ ] 打开多个浏览器标签
- [ ] 使用不同的client_id
- [ ] 测试消息是否正确发送到对应客户端

✅ 练习3：流式输出（15分钟）
- [ ] 测试流式endpoint
- [ ] 观察消息是否逐字显示
- [ ] 检查是否收到完成信号

✅ 练习4：错误处理（15分钟）
- [ ] 模拟网络断开
- [ ] 观察reconnection行为
- [ ] 添加心跳机制
"""
```

---

## 5.3 数据库优化实战

### **5.3.1 PostgreSQL性能优化（1.5小时）⚡**

```sql
-- ========================================
-- 第1部分：索引优化（30分钟）
-- ========================================

-- 练习1：分析慢查询
-- 开启慢查询日志
ALTER SYSTEM SET log_min_duration_statement = 1000; -- 记录>1秒的查询
SELECT pg_reload_conf();

-- 查看慢查询
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 练习2：创建合适的索引
-- ❌ 没有索引的查询（慢）
EXPLAIN ANALYZE
SELECT * FROM messages
WHERE conversation_id = 'xxx'
AND created_at > '2024-01-01'
ORDER BY created_at DESC
LIMIT 100;

-- ✅ 创建复合索引
CREATE INDEX idx_messages_conv_created 
ON messages(conversation_id, created_at DESC);

-- 再次执行查询（快）
EXPLAIN ANALYZE
SELECT * FROM messages
WHERE conversation_id = 'xxx'
AND created_at > '2024-01-01'
ORDER BY created_at DESC
LIMIT 100;

-- 练习3：JSONB索引
-- 为JSONB字段创建GIN索引
CREATE INDEX idx_messages_metadata 
ON messages USING GIN(metadata);

-- 快速查询JSON
SELECT * FROM messages
WHERE metadata @> '{"tool_name": "calculator"}';

-- 练习4：部分索引
-- 只为active状态创建索引（节省空间）
CREATE INDEX idx_conversations_active 
ON conversations(user_id, created_at)
WHERE status = 'active';

-- ========================================
-- 第2部分：查询优化（30分钟）
-- ========================================

-- 练习1：避免N+1查询
-- ❌ N+1查询（差）
SELECT * FROM conversations WHERE user_id = 'user123';
-- 然后对每个conversation：
SELECT * FROM messages WHERE conversation_id = ?;

-- ✅ 使用JOIN（好）
SELECT 
    c.*,
    json_agg(m.*) as messages
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.user_id = 'user123'
GROUP BY c.id;

-- 练习2：使用CTE优化复杂查询
WITH recent_conversations AS (
    SELECT id, user_id
    FROM conversations
    WHERE created_at > NOW() - INTERVAL '30 days'
    AND status = 'active'
),
conversation_stats AS (
    SELECT 
        conversation_id,
        COUNT(*) as message_count,
        MAX(created_at) as last_message
    FROM messages
    WHERE conversation_id IN (SELECT id FROM recent_conversations)
    GROUP BY conversation_id
)
SELECT 
    rc.*,
    cs.message_count,
    cs.last_message
FROM recent_conversations rc
LEFT JOIN conversation_stats cs ON rc.id = cs.conversation_id;

-- 练习3：使用窗口函数
-- 获取每个用户的最近3条对话
SELECT *
FROM (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY user_id 
            ORDER BY created_at DESC
        ) as rn
    FROM conversations
) sub
WHERE rn <= 3;

-- ========================================
-- 第3部分：表分区（30分钟）
-- ========================================

-- 练习1：创建分区表
CREATE TABLE messages_partitioned (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- 创建月度分区
CREATE TABLE messages_2024_01 PARTITION OF messages_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE messages_2024_02 PARTITION OF messages_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- 插入数据（自动路由到正确分区）
INSERT INTO messages_partitioned (conversation_id, role, content, created_at)
VALUES ('xxx', 'user', 'Hello', '2024-01-15');

-- 查询（只扫描相关分区）```sql
EXPLAIN ANALYZE
SELECT * FROM messages_partitioned
WHERE created_at BETWEEN '2024-01-01' AND '2024-01-31';
-- 只扫描 messages_2024_01 分区

-- 练习2：自动创建分区函数
CREATE OR REPLACE FUNCTION create_monthly_partition(
    target_date DATE
)
RETURNS void AS $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    partition_name := 'messages_' || TO_CHAR(target_date, 'YYYY_MM');
    start_date := DATE_TRUNC('month', target_date);
    end_date := start_date + INTERVAL '1 month';

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF messages_partitioned
         FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        start_date,
        end_date
    );

    RAISE NOTICE 'Created partition %', partition_name;
END;
$$ LANGUAGE plpgsql;

-- 创建未来6个月的分区
SELECT create_monthly_partition(CURRENT_DATE + (n || ' months')::INTERVAL)
FROM generate_series(0, 5) n;

-- 练习3：分区维护
-- 删除旧分区（归档数据）
DROP TABLE IF EXISTS messages_2023_01;

-- 分离分区（保留数据但不再作为分区）
ALTER TABLE messages_partitioned 
DETACH PARTITION messages_2023_12;

-- ========================================
-- 实战任务清单
-- ========================================

/*
✅ 任务1：索引优化（30分钟）
1. [ ] 运行 EXPLAIN ANALYZE 分析3个慢查询
2. [ ] 为每个慢查询创建合适的索引
3. [ ] 对比优化前后的执行时间
4. [ ] 记录索引大小和查询改善比例

✅ 任务2：查询重写（30分钟）
1. [ ] 找出项目中的N+1查询
2. [ ] 用JOIN重写
3. [ ] 测试性能改善
4. [ ] 更新代码

✅ 任务3：分区实施（30分钟）
1. [ ] 为messages表创建分区
2. [ ] 迁移历史数据
3. [ ] 配置自动分区创建
4. [ ] 测试查询性能
*/
```

---

## 5.4 监控和调试

### **5.4.1 Prometheus + Grafana实战（1小时）📊**

```python
"""
Prometheus指标采集实战
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps

# ========================================
# 第1部分：定义指标（15分钟）
# ========================================

# Counter：只增不减的计数器
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Histogram：观察值的分布
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]  # 自定义桶
)

# Gauge：可增可减的仪表
active_connections = Gauge(
    'active_websocket_connections',
    'Number of active WebSocket connections'
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'type']  # type: input/output
)

agent_execution_duration = Histogram(
    'agent_execution_duration_seconds',
    'Agent execution duration',
    ['agent_type', 'status']
)

tool_calls_total = Counter(
    'tool_calls_total',
    'Total tool calls',
    ['tool_name', 'status']
)

# Info：元数据
app_info = Info(
    'app_info',
    'Application information'
)
app_info.info({
    'version': '1.0.0',
    'environment': 'production'
})

# ========================================
# 第2部分：指标装饰器（15分钟）
# ========================================

def monitor_http_request(func):
    """HTTP请求监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request') or args[0]

        method = request.method
        endpoint = request.url.path

        # 开始计时
        start_time = time.time()

        try:
            response = await func(*args, **kwargs)
            status = response.status_code

            # 记录成功
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()

            return response

        except Exception as e:
            # 记录错误
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=500
            ).inc()
            raise

        finally:
            # 记录耗时
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

    return wrapper

def monitor_agent_execution(func):
    """Agent执行监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        agent_type = kwargs.get('agent_type', 'unknown')

        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            status = 'success'
            return result

        except Exception as e:
            status = 'error'
            raise

        finally:
            duration = time.time() - start_time
            agent_execution_duration.labels(
                agent_type=agent_type,
                status=status
            ).observe(duration)

    return wrapper

def monitor_tool_call(tool_name: str):
    """工具调用监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)

                tool_calls_total.labels(
                    tool_name=tool_name,
                    status='success'
                ).inc()

                return result

            except Exception as e:
                tool_calls_total.labels(
                    tool_name=tool_name,
                    status='error'
                ).inc()
                raise

        return wrapper
    return decorator

# ========================================
# 第3部分：使用示例（15分钟）
# ========================================

from fastapi import FastAPI, Request
from prometheus_client import make_asgi_app

app = FastAPI()

# 挂载Prometheus指标端点
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def add_prometheus_middleware(request: Request, call_next):
    """添加Prometheus中间件"""
    method = request.method
    endpoint = request.url.path

    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time

    # 记录指标
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()

    http_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)

    return response

@app.get("/api/data")
@monitor_http_request
async def get_data(request: Request):
    """示例API"""
    # 模拟处理
    await asyncio.sleep(0.5)
    return {"data": "example"}

@app.post("/api/agent/run")
@monitor_agent_execution
async def run_agent(agent_type: str = "customer_service"):
    """运行Agent"""
    # 模拟Agent执行
    await asyncio.sleep(2)

    # 记录LLM使用
    llm_tokens_total.labels(
        model='gpt-4',
        type='input'
    ).inc(100)

    llm_tokens_total.labels(
        model='gpt-4',
        type='output'
    ).inc(200)

    return {"status": "success"}

# WebSocket连接监控
@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()

    # 增加活跃连接
    active_connections.inc()

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(data)
    finally:
        # 减少活跃连接
        active_connections.dec()

# ========================================
# 第4部分：Grafana仪表板配置（15分钟）
# ========================================

"""
Grafana Dashboard JSON配置（保存为dashboard.json）

{
  "dashboard": {
    "title": "Agent Platform Monitoring",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate (QPS)",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Response Time (P50, P95, P99)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P99"
          }
        ]
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      },
      {
        "id": 4,
        "title": "Active WebSocket Connections",
        "type": "stat",
        "targets": [
          {
            "expr": "active_websocket_connections"
          }
        ]
      },
      {
        "id": 5,
        "title": "Agent Execution Time",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(agent_execution_duration_seconds_bucket[5m])",
            "legendFormat": "{{agent_type}}"
          }
        ]
      },
      {
        "id": 6,
        "title": "LLM Token Usage (Last Hour)",
        "type": "piechart",
        "targets": [
          {
            "expr": "increase(llm_tokens_total[1h])",
            "legendFormat": "{{model}} - {{type}}"
          }
        ]
      },
      {
        "id": 7,
        "title": "Tool Call Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(tool_calls_total{status=\"success\"}[5m]) / rate(tool_calls_total[5m])",
            "legendFormat": "{{tool_name}}"
          }
        ]
      }
    ]
  }
}
"""

# ========================================
# 练习任务
# ========================================

"""
✅ 任务1：部署Prometheus（15分钟）
1. [ ] 安装Prometheus
   docker run -d -p 9090:9090 -v ./prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus

2. [ ] 配置prometheus.yml
   scrape_configs:
     - job_name: 'agent-api'
       static_configs:
         - targets: ['host.docker.internal:8000']

3. [ ] 访问 http://localhost:9090
4. [ ] 查询指标：http_requests_total

✅ 任务2：部署Grafana（15分钟）
1. [ ] 安装Grafana
   docker run -d -p 3000:3000 grafana/grafana

2. [ ] 访问 http://localhost:3000 (admin/admin)
3. [ ] 添加Prometheus数据源
4. [ ] 导入dashboard.json

✅ 任务3：创建自定义仪表板（15分钟）
1. [ ] 创建新仪表板
2. [ ] 添加以下Panel：
   - Request Rate by Endpoint
   - Average Response Time
   - Top 5 Slowest Endpoints
3. [ ] 配置刷新间隔（5s）

✅ 任务4：设置告警（15分钟）
1. [ ] 在Grafana中配置告警
2. [ ] 设置条件：P99 > 3s
3. [ ] 配置通知渠道（Slack/Email）
4. [ ] 测试告警
"""
```

---

## 5.5 最佳实践和注意事项

### **5.5.1 代码规范检查清单 ✅**

```python
"""
代码质量检查清单
"""

# ========================================
# 1. 类型提示
# ========================================

# ❌ 没有类型提示
def process_data(data):
    return data.upper()

# ✅ 有类型提示
def process_data(data: str) -> str:
    """处理数据"""
    return data.upper()

# ✅ 复杂类型提示
from typing import Dict, List, Optional, Union

async def fetch_user_data(
    user_id: str,
    include_orders: bool = False
) -> Dict[str, Union[str, List[dict]]]:
    """获取用户数据"""
    data: Dict[str, Union[str, List[dict]]] = {
        "user_id": user_id,
        "name": "John"
    }

    if include_orders:
        data["orders"] = []

    return data

# ========================================
# 2. 文档字符串
# ========================================

# ❌ 没有文档
def calculate_total(items):
    return sum(item.price for item in items)

# ✅ 有文档
def calculate_total(items: List[Item]) -> float:
    """
    计算订单总价

    Args:
        items: 订单项列表

    Returns:
        总价（浮点数）

    Raises:
        ValueError: 如果items为空

    Example:
        >>> items = [Item(price=10.0), Item(price=20.0)]
        >>> calculate_total(items)
        30.0
    """
    if not items:
        raise ValueError("Items cannot be empty")

    return sum(item.price for item in items)

# ========================================
# 3. 错误处理
# ========================================

# ❌ 忽略错误
async def fetch_data():
    result = await api_call()
    return result

# ✅ 适当的错误处理
async def fetch_data() -> Optional[dict]:
    """获取数据（带错误处理）"""
    try:
        result = await api_call()
        return result

    except asyncio.TimeoutError:
        logger.error("API call timeout")
        return None

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise

# ========================================
# 4. 资源管理
# ========================================

# ❌ 不释放资源
async def bad_example():
    conn = await create_connection()
    data = await conn.fetch()
    return data

# ✅ 使用上下文管理器
async def good_example():
    async with create_connection() as conn:
        data = await conn.fetch()
        return data

# ========================================
# 5. 配置管理
# ========================================

# ❌ 硬编码配置
API_KEY = "sk-xxxxx"
DATABASE_URL = "postgresql://localhost/db"

# ✅ 使用配置类
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str
    database_url: str

    class Config:
        env_file = ".env"

settings = Settings()

# ========================================
# 6. 日志记录
# ========================================

# ❌ 使用print
def process():
    print("Processing...")
    result = do_something()
    print(f"Result: {result}")

# ✅ 使用logger
import logging

logger = logging.getLogger(__name__)

def process():
    logger.info("Processing started")
    result = do_something()
    logger.info(f"Processing completed", extra={"result": result})

# ========================================
# 7. 测试覆盖
# ========================================

# ✅ 为关键函数编写测试
import pytest

@pytest.mark.asyncio
async def test_fetch_user_data():
    """测试用户数据获取"""
    # Arrange
    user_id = "test_user"

    # Act
    result = await fetch_user_data(user_id)

    # Assert
    assert result["user_id"] == user_id
    assert "name" in result

@pytest.mark.asyncio
async def test_fetch_user_data_with_orders():
    """测试带订单的用户数据获取"""
    result = await fetch_user_data("test_user", include_orders=True)
    assert "orders" in result

# ========================================
# 检查清单
# ========================================

"""
✅ 代码质量检查清单

【类型和文档】
- [ ] 所有公共函数都有类型提示
- [ ] 所有公共函数都有文档字符串
- [ ] 复杂逻辑有内联注释

【错误处理】
- [ ] 所有外部调用都有错误处理
- [ ] 使用具体的异常类型
- [ ] 记录错误日志

【资源管理】
- [ ] 数据库连接使用上下文管理器
- [ ] 文件操作使用上下文管理器
- [ ] HTTP会话正确关闭

【配置和安全】
- [ ] 没有硬编码的密钥
- [ ] 敏感信息使用环境变量
- [ ] 配置使用pydantic验证

【测试】
- [ ] 关键函数有单元测试
- [ ] 测试覆盖率 > 80%
- [ ] 有集成测试

【性能】
- [ ] 使用异步I/O
- [ ] 避免N+1查询
- [ ] 合理使用缓存

【监控】
- [ ] 关键路径有指标埋点
- [ ] 错误有日志记录
- [ ] 性能数据可监控
"""
```

---

### **5.5.2 常见问题排查手册 🔍**

```markdown
# 常见问题排查手册

## 问题1：WebSocket连接频繁断开

### 症状
- WebSocket每隔几分钟就断开
- 客户端需要频繁重连

### 排查步骤
1. 检查心跳机制
   ```python
   # 添加心跳
   async def heartbeat():
       while True:
           await websocket.send_json({"type": "ping"})
           await asyncio.sleep(30)
```

2. 检查Nginx配置
   
   ```nginx
   # 增加超时时间
   proxy_read_timeout 3600s;
   proxy_send_timeout 3600s;
   ```

3. 检查防火墙设置

### 解决方案

- 实现心跳机制
- 配置合理的超时时间
- 客户端实现自动重连

## 问题2：数据库连接池耗尽

### 症状

- 错误：`TimeoutError: QueuePool limit exceeded`
- 新请求无法获取数据库连接

### 排查步骤

1. 检查连接泄漏
   
   ```python
   # 查看活跃连接
   SELECT count(*) FROM pg_stat_activity;
   
   # 查看长时间运行的查询
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query
   FROM pg_stat_activity
   WHERE state = 'active'
   ORDER BY duration DESC;
   ```

2. 检查连接池配置
   
   ```python
   engine = create_async_engine(
       url,
       pool_size=20,  # 增加
       max_overflow=40,  # 增加
       pool_recycle=3600
   )
   ```

3. 检查代码是否正确释放连接
   
   ```python
   # ✅ 使用上下文管理器
   async with session_maker() as session:
       result = await session.execute(query)
   ```

### 解决方案

- 修复连接泄漏
- 增加连接池大小
- 使用连接池监控

## 问题3：LLM响应超时

### 症状

- Agent执行时间过长
- 频繁出现timeout错误

### 排查步骤

1. 检查prompt长度
   
   ```python
   prompt_length = len(prompt.split())
   if prompt_length > 3000:
       logger.warning(f"Prompt too long: {prompt_length} words")
   ```

2. 检查LLM配置
   
   ```python
   llm = ChatOpenAI(
       model="gpt-4o-mini",  # 使用更快的模型
       temperature=0.7,
       max_tokens=500,  # 限制输出长度
       request_timeout=30
   )
   ```

3. 检查网络连接

### 解决方案

- 压缩prompt（使用摘要）
- 使用更快的模型
- 实现超时和重试机制
- 考虑使用缓存

## 问题4：内存使用持续增长

### 症状

- 应用内存占用不断增加
- 最终导致OOM

### 排查步骤

1. 使用memory_profiler
   
   ```python
   from memory_profiler import profile
   
   @profile
   def my_function():
       # 查看内存使用
       pass
   ```

2. 检查对象引用
   
   ```python
   import gc
   import objgraph
   
   # 查看最多的对象
   objgraph.show_most_common_types()
   ```

3. 检查是否有循环引用

### 解决方案

- 及时清理不用的对象
- 使用弱引用
- 定期执行`gc.collect()`
- 限制缓存大小

## 问题5：API响应时间慢

### 排查步骤

1. 使用cProfile分析
   
   ```bash
   python -m cProfile -o output.prof main.py
   ```

2. 使用Prometheus查看指标
   
   ```promql
   histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
   ```

3. 检查数据库慢查询
   
   ```sql
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC;
   ```

### 解决方案

- 优化慢查询
- 添加缓存
- 使用异步并行
- 优化算法复杂度

## 问题6：Agent执行结果不稳定

### 症状

- 相同输入得到不同输出
- 工具调用不准确

### 排查步骤

1. 检查temperature设置
   
   ```python
   llm = ChatOpenAI(temperature=0.0)  # 降低随机性
   ```

2. 检查prompt质量
   
   - 是否足够明确？
   - 是否有歧义？
   - 是否有足够的示例？

3. 检查状态管理
   
   - 状态是否正确传递？
   - 是否有状态污染？

### 解决方案

- 优化prompt
- 降低temperature
- 添加输出验证
- 增加重试逻辑

## 快速排查命令

```bash
# 查看日志
tail -f logs/app.log | grep ERROR

# 查看资源使用
htop

# 查看网络连接
netstat -an | grep 8000

# 查看数据库连接
psql -c "SELECT * FROM pg_stat_activity;"

# 查看Redis状态
redis-cli INFO

# 查看进程状态
ps aux | grep python

# 查看文件句柄
lsof -p <PID>
```

```
---

## 5.6 培训总结和考核

### **5.6.1 知识点总结 📝**

```markdown
# 培训知识点总结

## 第一天：基础知识（4小时）

### 上午：LangGraph核心概念（2小时）
- [x] State, Node, Edge, Graph
- [x] 状态更新机制（累加vs覆盖）
- [x] 条件路由和循环
- [x] 检查点和持久化

### 下午：实战练习（2小时）
- [x] 构建简单问答Agent
- [x] 添加工具调用
- [x] 实现状态持久化

## 第二天：进阶技能（4小时）

### 上午：FastAPI + WebSocket（2小时）
- [x] WebSocket基础
- [x] 连接管理
- [x] 流式数据传输
- [x] 错误处理

### 下午：数据库优化（2小时）
- [x] 索引优化
- [x] 查询优化
- [x] 表分区
- [x] 连接池配置

## 第三天：生产实践（4小时）

### 上午：监控和调试（2小时）
- [x] Prometheus指标
- [x] Grafana仪表板
- [x] 告警配置
- [x] 性能分析

### 下午：最佳实践（2小时）
- [x] 代码规范
- [x] 错误处理
- [x] 测试策略
- [x] 部署流程
```

---

### **5.6.2 考核题目 📋**

```python
"""
技术考核题目（2小时，满分100分）
"""

# ========================================
# 第1题：LangGraph基础（20分）
# ========================================

"""
任务：构建一个客服Agent，要求：
1. 能理解用户意图（问候/查询订单/投诉）（5分）
2. 根据意图调用不同的处理函数（5分）
3. 支持多轮对话（5分）
4. 状态能正确保存和恢复（5分）

提示：
- 定义合适的State
- 实现条件路由
- 使用PostgreSQL作为checkpointer
"""

# 你的答案：


# ========================================
# 第2题：WebSocket实现（20分）
# ========================================

"""
任务：实现一个WebSocket聊天服务，要求：
1. 支持多客户端连接（5分）
2. 实现流式消息传输（5分）
3. 添加心跳机制（5分）
4. 处理断线重连（5分）

提示：
- 使用ConnectionManager管理连接
- 实现ping/pong机制
- 捕获WebSocketDisconnect异常
"""

# 你的答案：


# ========================================
# 第3题：性能优化（20分）
# ========================================

"""
任务：优化以下代码的性能

# 原始代码（慢）
async def get_user_dashboard(user_id: str):
    user = await get_user(user_id)
    orders = await get_orders(user_id)
    preferences = await get_preferences(user_id)
    recommendations = await get_recommendations(user_id)

    return {
        "user": user,
        "orders": orders,
        "preferences": preferences,
        "recommendations": recommendations
    }

要求：
1. 使用并行执行优化（10分）
2. 添加缓存机制（5分）
3. 添加性能监控（5分）
"""

# 你的答案：


# ========================================
# 第4题：数据库优化（20分）
# ========================================

"""
任务：为以下查询优化性能

-- 原始查询（慢）
SELECT c.*, u.username, COUNT(m.id) as message_count
FROM conversations c
JOIN users u ON c.user_id = u.user_id
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.created_at > NOW() - INTERVAL '30 days'
GROUP BY c.id, u.username
ORDER BY c.created_at DESC
LIMIT 100;

要求：
1. 分析查询计划（5分）
2. 创建合适的索引（10分）
3. 重写查询提升性能（5分）
"""

# 你的答案：


# ========================================
# 第5题：监控和告警（20分）
# ========================================

"""
任务：为Agent平台添加监控

要求：
1. 定义5个关键指标（5分）
2. 为API端点添加监控装饰器（5分）
3. 编写Prometheus查询语句（5分）
4. 设计Grafana告警规则（5分）

指标示例：
- Request rate
- Response time
- Error rate
- Agent execution time
- LLM token usage
"""

# 你的答案：


# ========================================
# 评分标准
# ========================================

"""
评分标准：

90-100分：优秀
- 所有题目完成
- 代码质量高
- 有优化思考
- 有错误处理

80-89分：良好
- 主要题目完成
- 代码基本正确
- 有基本优化

70-79分：及格
- 完成一半以上题目
- 代码能运行
- 基本功能实现

< 70分：需要加强
- 完成题目少于一半
- 或代码有明显错误
"""
```

---

### **5.6.3 实战项目（团队作业）🎯**

```markdown
# 团队实战项目：构建一个完整的智能客服系统

## 项目要求

### 功能要求
1. **基础对话**
   - 支持问候、闲聊
   - 支持FAQ自动回答
   - 支持多轮对话

2. **订单管理**
   - 查询订单状态
   - 查询物流信息
   - 订单投诉处理

3. **智能路由**
   - 自动识别用户意图
   - 复杂问题转人工
   - 紧急问题优先处理

4. **数据分析**
   - 生成对话统计报告
   - 用户满意度分析
   - 常见问题挖掘

### 技术要求
1. **后端**
   - 使用LangGraph构建Agent
   - FastAPI提供API
   - PostgreSQL存储数据
   - Redis缓存

2. **前端**
   - 基于OpenWebUI修改
   - 支持流式显示
   - 显示工具调用状态

3. **监控**
   - Prometheus采集指标
   - Grafana可视化
   - 告警配置

4. **部署**
   - Docker容器化
   - Kubernetes编排
   - CI/CD自动化

### 质量要求
1. 代码质量
   - 测试覆盖率 > 80%
   - 通过Flake8检查
   - 有完整文档

2. 性能要求
   - P99响应时间 < 3s
   - 支持100并发
   - 可用性 > 99%

3. 安全要求
   - 输入验证
   - SQL注入防护
   - 敏感数据加密

## 项目分工

### 团队角色（4-5人）
- **组长（1人）**
  - 架构设计
  - 任务分配
  - 代码审查

- **后端开发（2人）**
  - Agent开发
  - API开发
  - 数据库设计

- **前端开发（1人）**
  - UI开发
  - WebSocket集成
  - 用户体验优化

- **DevOps（1人）**
  - 部署配置
  - 监控搭建
  - CI/CD

## 时间计划（2周）

### Week 1: 核心功能开发
- Day 1-2: 架构设计和环境搭建
- Day 3-4: Agent核心功能开发
- Day 5: 数据库和API开发

### Week 2: 集成和优化
- Day 1: 前端集成
- Day 2: 监控和日志
- Day 3: 性能优化
- Day 4: 测试和修复
- Day 5: 部署和演示

## 交付物

1. **代码仓库**
   - 完整的源代码
   - README文档
   - API文档

2. **部署包**
   - Docker镜像
   - Kubernetes配置
   - 部署文档

3. **演示视频**
   - 功能演示（10分钟）
   - 技术讲解（10分钟）

4. **项目报告**
   - 架构设计
   - 技术选型
   - 遇到的问题和解决方案
   - 性能测试结果

## 评分标准（100分）

### 功能完整性（30分）
- [ ] 基础对话功能（10分）
- [ ] 订单管理功能（10分）
- [ ] 智能路由功能（10分）

### 技术实现（30分）
- [ ] Agent设计合理（10分）
- [ ] API设计规范（5分）
- [ ] 数据库设计优化（5分）
- [ ] 前端交互流畅（5分）
- [ ] 监控完善（5分）

### 代码质量（20分）
- [ ] 测试覆盖率达标（5分）
- [ ] 代码规范（5分）
- [ ] 文档完整（5分）
- [ ] 错误处理（5分）

### 性能和稳定性（10分）
- [ ] 性能达标（5分）
- [ ] 稳定性测试通过（5分）

### 创新和亮点（10分）
- [ ] 技术创新（5分）
- [ ] 用户体验优化（5分）

## 示例项目结构
```

intelligent-customer-service/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── customer_service_agent.py
│   │   │   ├── order_agent.py
│   │   │   └── routing_agent.py
│   │   ├── api/
│   │   │   ├── chat.py
│   │   │   ├── orders.py
│   │   │   └── analytics.py
│   │   ├── models/
│   │   ├── tools/
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── lib/
│   │   └── App.svelte
│   └── package.json
├── deployment/
│   ├── docker-compose.yml
│   ├── k8s/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   └── prometheus.yml
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── deployment.md
└── README.md

```
## 参考资源

### 文档
- LangGraph: https://langchain-ai.github.io/langgraph/
- FastAPI: https://fastapi.tiangolo.com/
- PostgreSQL: https://www.postgresql.org/docs/

### 示例代码
- 本培训材料中的所有代码示例
- LangGraph官方示例

### 工具
- GitHub: 代码托管
- Postman: API测试
- k6: 性能测试
- pytest: 单元测试
```

---

## 5.7 学习资源和持续学习

### **5.7.1 推荐学习资源 📚**

```markdown
# 推荐学习资源

## 官方文档

### LangChain生态
1. **LangGraph文档**
   - 官网：https://langchain-ai.github.io/langgraph/
   - GitHub：https://github.com/langchain-ai/langgraph
   - 重点学习：
     - Tutorials（教程）
     - How-to Guides（操作指南）
     - Conceptual Guides（概念指南）

2. **LangChain文档**
   - 官网：https://python.langchain.com/
   - 重点学习：
     - Agent Types
     - Memory
     - Tools
     - Retrieval

### FastAPI
3. **FastAPI官方文档**
   - 官网：https://fastapi.tiangolo.com/
   - 重点学习：
     - WebSocket
     - Background Tasks
     - Dependency Injection
     - Testing

### 数据库
4. **PostgreSQL文档**
   - 官网：https://www.postgresql.org/docs/
   - 重点学习：
     - Performance Tips
     - Indexing
     - Partitioning

5. **SQLAlchemy文档**
   - 官网：https://docs.sqlalchemy.org/
   - 重点学习：
     - Async ORM
     - Performance
     - Best Practices

## 视频教程

### YouTube频道
1. **LangChain官方频道**
   - LangChain基础教程系列
   - LangGraph深入讲解

2. **ArjanCodes**
   - Python最佳实践
   - 软件架构设计

3. **TechWorld with Nana**
   - Kubernetes教程
   - DevOps实践

## 在线课程

### 推荐课程
1. **Udemy**
   - "Building LLM Applications with LangChain"
   - "FastAPI - The Complete Course"

2. **Coursera**
   - "Machine Learning Specialization"（Andrew Ng）

3. **DeepLearning.AI**
   - "LangChain for LLM Application Development"
   - "Building Systems with ChatGPT API"

## 书籍

### 技术书籍
1. **《Designing Data-Intensive Applications》**
   - 作者：Martin Kleppmann
   - 主题：分布式系统、数据库

2. **《Clean Architecture》**
   - 作者：Robert C. Martin
   - 主题：软件架构设计

3. **《Python Concurrency with asyncio》**
   - 作者：Matthew Fowler
   - 主题：Python异步编程

## 社区和论坛

### 活跃社区
1. **LangChain Discord**
   - 链接：https://discord.gg/langchain
   - 活跃度：非常高
   - 特点：官方支持，快速响应

2. **Reddit**
   - r/LangChain
   - r/MachineLearning
   - r/Python

3. **Stack Overflow**
   - 标签：langchain, langgraph, fastapi

## 博客和文章

### 优质博客
1. **LangChain Blog**
   - https://blog.langchain.dev/

2. **OpenAI Blog**
   - https://openai.com/blog/

3. **Real Python**
   - https://realpython.com/

## GitHub项目

### 值得学习的项目
1. **LangChain Templates**
   - https://github.com/langchain-ai/langchain/tree/master/templates
   - 各种应用模板

2. **Awesome LangChain**
   - https://github.com/kyrolabs/awesome-langchain
   - LangChain资源合集

3. **FastAPI Best Practices**
   - https://github.com/zhanymkanov/fastapi-best-practices

## 持续学习计划

### 每周学习计划
- **周一**：阅读官方文档（1小时）
- **周二**：观看技术视频（1小时）
- **周三**：实践编码（2小时）
- **周四**：阅读技术博客（1小时）
- **周五**：总结和分享（1小时）

### 月度目标
- 完成1个小项目
- 阅读1篇深度技术文章
- 贡献1个开源PR

### 季度目标
- 掌握1个新技术栈
- 完成1个中型项目
- 写1篇技术博客

## 技术社区活动

### 推荐参加
1. **线上会议**
   - LangChain Webinars
   - FastAPI Town Halls

2. **技术大会**
   - PyCon
   - AI/ML Conferences

3. **本地Meetup**
   - Python User Groups
   - AI/ML Meetups


### **5.7.2 团队知识分享机制 🤝**

```markdown
# 团队知识分享机制

## 1. 每周技术分享会（1小时）

### 形式
- 时间：每周五下午
- 时长：45分钟分享 + 15分钟讨论
- 轮流主讲

### 主题示例
- Week 1: LangGraph高级特性
- Week 2: PostgreSQL性能优化实战
- Week 3: 监控系统搭建经验
- Week 4: 生产问题案例分析

### 分享模板
```

1. 主题介绍（5分钟）

2. 背景和问题（10分钟）

3. 解决方案（20分钟）

4. 经验总结（10分钟）

5. Q&A（15分钟）

## 2. 代码审查（Code Review）

### 规则

- 所有PR必须经过至少1人审查
- 重要功能需要2人审查
- 24小时内必须响应

### 审查清单

- [ ] 代码符合规范
- [ ] 有单元测试
- [ ] 有文档注释
- [ ] 性能合理
- [ ] 安全性考虑

## 3. 技术文档维护

### 文档类型

1. **架构文档**
   
   - 系统架构图
   - 数据流图
   - 技术选型说明

2. **操作手册**
   
   - 部署指南
   - 故障排查手册
   - 监控告警手册

3. **最佳实践**
   
   - 编码规范
   - 性能优化技巧
   - 常见陷阱

### 更新频率

- 架构变更：立即更新
- 操作手册：遇到新问题时更新
- 最佳实践：每月review

## 4. 技术博客

### 鼓励分享

- 项目经验
- 问题解决过程
- 技术调研结果
- 学习笔记

### 奖励机制

- 优质博客内部表彰
- 外部发表额外奖励

## 5. 内部培训

### 新人培训

- 第1周：环境搭建和代码导读
- 第2周：核心技术栈培训
- 第3周：实战项目演练
- 第4周：独立完成小需求

### 进阶培训

- 按需组织专题培训
- 邀请外部专家分享

---

## 结语

```markdown
# 恭喜你完成了培训！🎉

你已经掌握了：
✅ LangGraph核心概念和实战
✅ FastAPI + WebSocket开发
✅ 数据库性能优化
✅ 监控和调试技能
✅ 生产环境最佳实践

## 下一步

1. **实践项目**
   - 完成团队实战项目
   - 在真实场景中应用所学

2. **持续学习**
   - 关注LangChain生态更新
   - 学习相关技术栈
   - 参与社区讨论

3. **分享贡献**
   - 写技术博客
   - 参与开源贡献
   - 帮助团队新人

## 联系和支持

- 技术问题：团队技术群
- 文档更新：提交PR到文档仓库
- 建议反馈：联系培训负责人

## 资源链接

- 培训材料仓库：[链接]
- 项目代码仓库：[链接]
- 团队Wiki：[链接]

记住：
💡 学习是一个持续的过程
🚀 实践是最好的老师
🤝 分享让知识传播

祝你在新系统开发中取得成功！
```

---

**完整指导手册到此结束！**

这份手册涵盖了：

1. ✅ 完整的代码示例（1.1-1.2）
2. ✅ 详细的技术方案文档（2.1-2.2）
3. ✅ 迁移检查清单（3.1-3.4）
4. ✅ 性能优化方案（4.1-4.5）
5. ✅ 团队培训材料（5.1-5.7）
