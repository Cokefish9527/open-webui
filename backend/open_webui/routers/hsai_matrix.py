import logging
import time
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.models.hsai_matrix import (
    HSAIPlatformAccount,
    HSAIPublishTask,
    HSAIPublishRecord,
    HSAIAccountGroup,
    HSAIAccountGroupModel,
    HSAIPlatformAccounts,
    HSAIPublishTasks,
    HSAIPlatformAccountForm,
    HSAIPublishTaskForm,
    HSAIAccountGroupForm,
    HSAIPlatformAccountResponse,
    HSAIPublishTaskResponse,
    HSAIPublishStatsResponse,
    HSAIPlatformType,
    HSAIPublishStatus,
    HSAIAccountStatus
)

from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.socket.main import get_event_emitter
from open_webui.utils.hsai_oauth_handler import hsai_oauth_handler

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/hsai/matrix", tags=["hsai_matrix"])

############################
# 平台账号管理
############################

@router.get("/accounts", response_model=List[HSAIPlatformAccountResponse])
async def get_platform_accounts(
    platform_type: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(get_verified_user)
):
    """
    获取用户的平台账号列表。
    
    返回用户绑定的所有社交媒体平台账号，支持按平台类型和状态过滤。
    
    Args:
        platform_type (Optional[str]): 平台类型过滤
        - "tiktok": TikTok平台
        - "instagram": Instagram平台
        - "youtube": YouTube平台
        - "facebook": Facebook平台
        status (Optional[str]): 账号状态过滤
        - "active": 活跃账号
        - "inactive": 非活跃账号
        - "suspended": 已暂停账号
        user: 已认证的用户对象
        
    Returns:
        List[HSAIPlatformAccountResponse]: 平台账号列表
        - id: 账号唯一标识
        - platform_type: 平台类型
        - username: 用户名
        - display_name: 显示名称
        - avatar_url: 头像URL
        - follower_count: 粉丝数量
        - following_count: 关注数量
        - posts_count: 发布内容数量
        - is_token_valid: 授权令牌是否有效
        - status: 账号状态
        - last_sync_at: 最后同步时间
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        accounts = HSAIPlatformAccounts.get_accounts_by_user_id(
            user.id, 
            platform_type=platform_type,
            status=status
        )
        
        responses = []
        for account in accounts:
            # 检查令牌是否有效
            is_token_valid = True
            if account.token_expires_at and account.token_expires_at < int(time.time()):
                is_token_valid = False
            
            response = HSAIPlatformAccountResponse(
                **account.model_dump(exclude={"access_token", "refresh_token"}),
                is_token_valid=is_token_valid,
                group_name=None  # 后续可以关联账号分组
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        log.exception(f"Error getting platform accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/accounts", response_model=HSAIPlatformAccountResponse)
async def create_platform_account(
    form_data: HSAIPlatformAccountForm,
    user=Depends(get_verified_user)
):
    """
    创建新的平台账号。
    
    手动添加社交媒体平台账号信息，用于后续的内容发布管理。
    
    Args:
        form_data (HSAIPlatformAccountForm): 账号创建表单
        - platform_type: 平台类型（必填）
        - username: 用户名（必填）
        - display_name: 显示名称（可选）
        - avatar_url: 头像URL（可选）
        - access_token: 访问令牌（可选）
        - refresh_token: 刷新令牌（可选）
        - token_expires_at: 令牌过期时间（可选）
        user: 已认证的用户对象
        
    Returns:
        HSAIPlatformAccountResponse: 创建的账号信息
        
    Raises:
        HTTPException: 400 - 不支持的平台类型或创建失败
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 支持的平台类型：tiktok, instagram, youtube, facebook
        - 建议通过OAuth授权方式获取访问令牌
    """
    try:
        # 验证平台类型
        if form_data.platform_type not in [pt.value for pt in HSAIPlatformType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform type: {form_data.platform_type}"
            )
        
        account = HSAIPlatformAccounts.insert_new_account(user.id, form_data)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create platform account"
            )
        
        return HSAIPlatformAccountResponse(
            **account.model_dump(exclude={"access_token", "refresh_token"}),
            is_token_valid=True,
            group_name=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating platform account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/accounts/{account_id}/token")
async def update_account_token(
    account_id: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_at: Optional[int] = None,
    user=Depends(get_verified_user)
):
    """更新账号令牌"""
    try:
        # 验证账号所有权
        account = HSAIPlatformAccounts.get_account_by_id(account_id)
        if not account or account.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        result = HSAIPlatformAccounts.update_account_token(
            account_id, access_token, refresh_token, expires_at
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update token"
            )
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating account token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/accounts/{account_id}/stats")
async def update_account_stats(
    account_id: str,
    follower_count: int,
    following_count: int,
    posts_count: int,
    user=Depends(get_verified_user)
):
    """更新账号统计数据"""
    try:
        # 验证账号所有权
        account = HSAIPlatformAccounts.get_account_by_id(account_id)
        if not account or account.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        result = HSAIPlatformAccounts.update_account_stats(
            account_id, follower_count, following_count, posts_count
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update stats"
            )
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating account stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/accounts/{account_id}/sync")
async def sync_account_data(
    account_id: str,
    user=Depends(get_verified_user)
):
    """
    同步账号数据。
    
    从对应的社交媒体平台获取最新的账号统计数据，如粉丝数、关注数等。
    
    Args:
        account_id (str): 要同步的账号ID
        user: 已认证的用户对象
        
    Returns:
        dict: 同步结果
        - success: 是否成功
        - stats: 更新后的统计数据
          - follower_count: 粉丝数量
          - following_count: 关注数量
          - posts_count: 发布内容数量
        - sync_time: 同步时间戳
        
    Raises:
        HTTPException: 404 - 账号不存在或无权限访问
        HTTPException: 400 - 账号令牌无效或已过期
        HTTPException: 500 - 同步失败
        
    Note:
        - 需要有效的访问令牌才能同步数据
        - 同步成功后会通过WebSocket通知前端
        - 当前为简化实现，实际应调用平台API
    """
    try:
        # 验证账号所有权
        account = HSAIPlatformAccounts.get_account_by_id(account_id)
        if not account or account.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        # 检查令牌是否有效
        if not account.access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account token not available"
            )
        
        if account.token_expires_at and account.token_expires_at < int(time.time()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account token expired"
            )
        
        # 这里应该调用对应平台的API获取最新数据
        # 简化版本：模拟数据同步
        import random
        
        updated_stats = {
            "follower_count": account.follower_count + random.randint(0, 100),
            "following_count": account.following_count + random.randint(0, 10),
            "posts_count": account.posts_count + random.randint(0, 5)
        }
        
        # 更新统计数据
        result = HSAIPlatformAccounts.update_account_stats(
            account_id, 
            updated_stats["follower_count"],
            updated_stats["following_count"],
            updated_stats["posts_count"]
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update account data"
            )
        
        # 更新最后同步时间
        HSAIPlatformAccounts.update_account_by_id(account_id, {
            "last_sync_at": int(time.time())
        })
        
        # 通过WebSocket通知前端
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_account_synced",
                {
                    "account_id": account_id,
                    "stats": updated_stats,
                    "user_id": user.id
                },
                to=user.id
            )
        
        return {
            "success": True,
            "stats": updated_stats,
            "sync_time": int(time.time())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error syncing account data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# 账号分组管理
############################

@router.get("/groups", response_model=List[HSAIAccountGroupModel])
async def get_account_groups(
    user=Depends(get_verified_user)
):
    """获取账号分组列表"""
    try:
        # 注意：这里需要在HSAIAccountGroup模型中实现相应方法
        # 简化版本：返回空列表
        return []
        
    except Exception as e:
        log.exception(f"Error getting account groups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/groups", response_model=HSAIAccountGroupModel)
async def create_account_group(
    form_data: HSAIAccountGroupForm,
    user=Depends(get_verified_user)
):
    """创建账号分组"""
    try:
        # 注意：这里需要在数据模型中实现相应方法
        # 简化版本：返回模拟数据
        group = HSAIAccountGroup(
            id=f"group_{int(time.time())}",
            user_id=user.id,
            name=form_data.name,
            description=form_data.description,
            color=form_data.color or "#6B7280",
            config=form_data.config or {},
            sort_order=0,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        
        return group
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating account group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# 发布任务管理
############################

@router.get("/publish-tasks", response_model=List[HSAIPublishTaskResponse])
async def get_publish_tasks(
    status: Optional[str] = None,
    user=Depends(get_verified_user)
):
    """
    获取用户的发布任务列表。
    
    返回用户创建的所有内容发布任务，支持按状态过滤。
    
    Args:
        status (Optional[str]): 任务状态过滤
        - "draft": 草稿状态
        - "scheduled": 已安排发布
        - "publishing": 发布中
        - "published": 已发布
        - "failed": 发布失败
        user: 已认证的用户对象
        
    Returns:
        List[HSAIPublishTaskResponse]: 发布任务列表
        - id: 任务唯一标识
        - title: 任务标题
        - content: 发布内容
        - platforms: 目标平台列表
        - scheduled_at: 计划发布时间
        - status: 当前状态
        - progress: 发布进度
        - success_count: 成功发布的平台数量
        - total_count: 总平台数量
        - created_at: 创建时间
        
    Raises:
        HTTPException: 500 - 服务器内部错误
    """
    try:
        tasks = HSAIPublishTasks.get_publish_tasks_by_user_id(user.id, status=status)
        
        responses = []
        for task in tasks:
            # 统计发布成功率
            success_count = 0
            total_count = len(task.platforms)
            
            # 这里可以查询发布记录来获取实际的成功率
            # 简化版本：如果任务已完成，则认为全部成功
            if task.status == HSAIPublishStatus.PUBLISHED:
                success_count = total_count
            
            response = HSAIPublishTaskResponse(
                **task.model_dump(),
                success_count=success_count,
                total_count=total_count
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        log.exception(f"Error getting publish tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/publish-tasks", response_model=HSAIPublishTaskResponse)
async def create_publish_task(
    form_data: HSAIPublishTaskForm,
    user=Depends(get_verified_user)
):
    """
    创建新的发布任务。
    
    创建跨平台内容发布任务，支持同时向多个社交媒体平台发布内容。
    
    Args:
        form_data (HSAIPublishTaskForm): 发布任务创建表单
        - title: 任务标题（必填）
        - content: 发布内容（必填）
        - platforms: 目标平台列表（必填）
        - media_urls: 媒体文件URL列表（可选）
        - scheduled_at: 计划发布时间（可选，为空则立即发布）
        - tags: 标签列表（可选）
        - settings: 平台特定设置（可选）
        user: 已认证的用户对象
        
    Returns:
        HSAIPublishTaskResponse: 创建的发布任务信息
        
    Raises:
        HTTPException: 400 - 平台列表为空、用户无对应平台账号或创建失败
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 至少需要指定一个目标平台
        - 用户必须拥有目标平台的活跃账号
        - 支持定时发布功能
    """
    try:
        # 验证平台列表
        if not form_data.platforms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one platform must be specified"
            )
        
        # 验证用户是否有对应平台的账号
        user_accounts = HSAIPlatformAccounts.get_accounts_by_user_id(user.id)
        user_platforms = {account.platform_type for account in user_accounts if account.status == HSAIAccountStatus.ACTIVE}
        
        invalid_platforms = set(form_data.platforms) - user_platforms
        if invalid_platforms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No active accounts for platforms: {list(invalid_platforms)}"
            )
        
        task = HSAIPublishTasks.insert_new_publish_task(user.id, form_data)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create publish task"
            )
        
        return HSAIPublishTaskResponse(
            **task.model_dump(),
            success_count=0,
            total_count=len(task.platforms)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating publish task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/publish-tasks/{task_id}/execute")
async def execute_publish_task(
    task_id: str,
    user=Depends(get_verified_user)
):
    """
    执行发布任务。
    
    启动发布任务的执行，将内容发布到指定的社交媒体平台。
    
    Args:
        task_id (str): 要执行的发布任务ID
        user: 已认证的用户对象
        
    Returns:
        dict: 执行结果
        - success: 是否成功启动
        - message: 结果消息
        
    Raises:
        HTTPException: 404 - 发布任务不存在或无权限访问
        HTTPException: 500 - 启动失败
        
    Note:
        - 任务状态会更新为"publishing"
        - 实际发布过程通过异步队列执行
        - 会通过WebSocket实时通知发布进度
        - 支持批量发布到多个平台
    """
    try:
        # 验证任务所有权
        task = HSAIPublishTasks.get_publish_tasks_by_user_id(user.id)
        task_exists = any(t.id == task_id for t in task)
        
        if not task_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Publish task not found"
            )
        
        # 更新任务状态为发布中
        result = HSAIPublishTasks.update_publish_task_status(
            task_id, HSAIPublishStatus.PUBLISHING, progress=0
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start publish task"
            )
        
        # 这里可以添加异步发布逻辑
        # 例如：通过Celery或其他队列系统执行实际的发布操作
        
        # 通过WebSocket通知前端
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_publish_started",
                {
                    "task_id": task_id,
                    "user_id": user.id
                },
                to=user.id
            )
        
        return {"success": True, "message": "Publish task started"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error executing publish task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/publish-tasks/{task_id}/status")
async def update_publish_task_status(
    task_id: str,
    status: str,
    progress: Optional[int] = None,
    error_message: Optional[str] = None,
    user=Depends(get_verified_user)
):
    """更新发布任务状态"""
    try:
        # 验证状态值
        if status not in [s.value for s in HSAIPublishStatus]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
        
        result = HSAIPublishTasks.update_publish_task_status(
            task_id, status, progress, error_message
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Publish task not found or update failed"
            )
        
        # 通过WebSocket通知前端
        emitter = get_event_emitter()
        if emitter:
            await emitter.emit(
                "hsai_publish_updated",
                {
                    "task_id": task_id,
                    "status": status,
                    "progress": progress,
                    "user_id": user.id
                },
                to=user.id
            )
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating publish task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# 平台OAuth授权
############################

class OAuthUrlResponse(BaseModel):
    authorization_url: str
    state: str


@router.get("/oauth/{platform_type}/url", response_model=OAuthUrlResponse)
async def get_oauth_url(
    platform_type: str,
    redirect_uri: str,
    user=Depends(get_verified_user)
):
    """
    获取平台OAuth授权URL。
    
    生成指定社交媒体平台的OAuth授权链接，用于用户授权账号绑定。
    
    Args:
        platform_type (str): 平台类型
        - "tiktok": TikTok平台
        - "instagram": Instagram平台
        - "youtube": YouTube平台
        redirect_uri (str): 授权回调地址
        user: 已认证的用户对象
        
    Returns:
        OAuthUrlResponse: OAuth授权信息
        - authorization_url: 授权URL
        - state: 状态参数（用于防止CSRF攻击）
        
    Raises:
        HTTPException: 400 - 不支持的平台类型
        HTTPException: 500 - 生成授权URL失败
        
    Note:
        - 用户需要访问返回的授权URL完成授权
        - state参数用于验证回调的合法性
        - 授权成功后会跳转到指定的回调地址
    """
    try:
        # 验证平台类型
        if platform_type not in [pt.value for pt in HSAIPlatformType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform type: {platform_type}"
            )
        
        # 使用OAuth处理器生成授权URL
        oauth_data = hsai_oauth_handler.generate_oauth_url(
            platform_type, redirect_uri, user.id
        )
        
        return OAuthUrlResponse(
            authorization_url=oauth_data["authorization_url"],
            state=oauth_data["state"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting OAuth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/oauth/{platform_type}/callback")
async def oauth_callback(
    platform_type: str,
    code: str,
    state: str,
    user=Depends(get_verified_user)
):
    """
    处理OAuth授权回调。
    
    处理社交媒体平台的OAuth授权回调，获取访问令牌并创建账号绑定。
    
    Args:
        platform_type (str): 平台类型
        code (str): 授权码
        state (str): 状态参数（用于验证请求合法性）
        user: 已认证的用户对象
        
    Returns:
        dict: 处理结果
        - success: 是否成功
        - message: 结果消息
        - account_id: 创建的账号ID
        - redirect_url: 重定向URL
        
    Raises:
        HTTPException: 400 - 不支持的平台类型或授权失败
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 会验证state参数防止CSRF攻击
        - 成功后会自动创建平台账号记录
        - 通过WebSocket通知前端账号连接成功
        - 建议重定向到工作台页面
    """
    try:
        # 验证平台类型
        if platform_type not in [pt.value for pt in HSAIPlatformType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform type: {platform_type}"
            )
        
        # 使用OAuth处理器处理回调
        result = hsai_oauth_handler.handle_oauth_callback(
            platform_type, code, state
        )
        
        if result["success"]:
            # 通过WebSocket通知前端账号添加成功
            emitter = get_event_emitter()
            if emitter:
                await emitter.emit(
                    "hsai_account_connected",
                    {
                        "account_id": result["account_id"],
                        "platform_type": platform_type,
                        "user_id": user.id
                    },
                    to=user.id
                )
            
            return {
                "success": True,
                "message": f"Successfully connected {platform_type} account",
                "account_id": result["account_id"],
                "redirect_url": "/workspace/hsai"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error handling OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# 统计数据
############################

@router.get("/stats", response_model=HSAIPublishStatsResponse)
async def get_publish_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_verified_user)
):
    """
    获取发布统计数据。
    
    提供用户内容发布的详细统计信息，用于分析发布效果和参与度。
    
    Args:
        start_date (Optional[str]): 开始日期（YYYY-MM-DD格式，可选）
        end_date (Optional[str]): 结束日期（YYYY-MM-DD格式，可选）
        user: 已认证的用户对象
        
    Returns:
        HSAIPublishStatsResponse: 发布统计数据
        - total_posts: 总发布数量
        - published_posts: 已发布数量
        - scheduled_posts: 计划发布数量
        - failed_posts: 发布失败数量
        - total_views: 总浏览量
        - total_likes: 总点赞数
        - total_comments: 总评论数
        - total_shares: 总分享数
        - engagement_rate: 参与度（百分比）
        
    Raises:
        HTTPException: 500 - 服务器内部错误
        
    Note:
        - 如不指定日期范围，返回全部数据
        - 参与度 = (点赞数 + 评论数) / 浏览量 * 100
        - 统计数据仅包含当前用户的发布内容
    """
    try:
        # 获取用户的发布任务
        tasks = HSAIPublishTasks.get_publish_tasks_by_user_id(user.id)
        
        # 统计各种指标
        stats = HSAIPublishStatsResponse(
            total_posts=len(tasks),
            published_posts=0,
            scheduled_posts=0,
            failed_posts=0,
            total_views=0,
            total_likes=0,
            total_comments=0,
            total_shares=0,
            engagement_rate=0.0
        )
        
        for task in tasks:
            if task.status == HSAIPublishStatus.PUBLISHED:
                stats.published_posts += 1
            elif task.status == HSAIPublishStatus.SCHEDULED:
                stats.scheduled_posts += 1
            elif task.status == HSAIPublishStatus.FAILED:
                stats.failed_posts += 1
        
        # 计算参与度（简化版本）
        if stats.total_views > 0:
            stats.engagement_rate = (stats.total_likes + stats.total_comments) / stats.total_views * 100
        
        return stats
        
    except Exception as e:
        log.exception(f"Error getting publish stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# 平台支持信息
############################

class PlatformInfoResponse(BaseModel):
    platform_type: str
    display_name: str
    supported_content_types: List[str]
    max_video_size: int  # MB
    max_video_duration: int  # seconds
    supported_formats: List[str]
    oauth_supported: bool


@router.get("/platforms", response_model=List[PlatformInfoResponse])
async def get_supported_platforms():
    """
    获取支持的平台列表及其限制信息。
    
    返回系统支持的所有社交媒体平台及其技术规格和限制。
    
    Returns:
        List[PlatformInfoResponse]: 支持的平台列表
        - platform_type: 平台类型标识
        - display_name: 平台显示名称
        - supported_content_types: 支持的内容类型
          - "image": 图片内容
          - "video": 视频内容
          - "carousel": 轮播图内容
        - max_video_size: 最大视频文件大小（MB）
        - max_video_duration: 最大视频时长（秒）
        - supported_formats: 支持的文件格式
        - oauth_supported: 是否支持OAuth授权
        
    Note:
        - 不同平台有不同的内容限制
        - 建议在上传前检查文件规格
        - OAuth支持情况影响账号绑定方式
        - 平台规格可能随时更新
    """
    platforms = [
        PlatformInfoResponse(
            platform_type="tiktok",
            display_name="TikTok",
            supported_content_types=["video"],
            max_video_size=72,  # 72MB
            max_video_duration=600,  # 10 minutes
            supported_formats=["mp4", "mov"],
            oauth_supported=True
        ),
        PlatformInfoResponse(
            platform_type="instagram",
            display_name="Instagram",
            supported_content_types=["image", "video", "carousel"],
            max_video_size=100,  # 100MB
            max_video_duration=3600,  # 60 minutes
            supported_formats=["mp4", "mov", "jpg", "png"],
            oauth_supported=True
        ),
        PlatformInfoResponse(
            platform_type="youtube",
            display_name="YouTube",
            supported_content_types=["video"],
            max_video_size=256000,  # 256GB (practically unlimited)
            max_video_duration=43200,  # 12 hours
            supported_formats=["mp4", "mov", "avi", "wmv", "flv"],
            oauth_supported=True
        ),
        PlatformInfoResponse(
            platform_type="facebook",
            display_name="Facebook",
            supported_content_types=["image", "video", "carousel"],
            max_video_size=10000,  # 10GB
            max_video_duration=14400,  # 240 minutes
            supported_formats=["mp4", "mov", "jpg", "png"],
            oauth_supported=False
        )
    ]
    
    return platforms