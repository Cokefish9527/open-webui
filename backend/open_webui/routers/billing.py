import datetime
import logging
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field

from open_webui.models.billing_config import (
    BillingConfigs,
    BillingConfigForm,
    BillingConfigUpdateForm,
    BillingConfigResponse,
    PaginationData,
    PaginatedBillingConfigResponse
)

from open_webui.models.api_usage_log import (
    APIUsageLogs,
    APIUsageLogForm,
    APIUsageLogResponse,
    APIUsageLogPaginationData,
    PaginatedAPIUsageLogResponse
)

from open_webui.models.credits import Credits
from open_webui.models.hsai_companies import Companies
from open_webui.models.hsai_coupons import (
    Coupons,
    CouponBatchCreateForm,
    CouponBatchCreateResponse,
    CouponRedeemForm,
    CouponRedeemResponse,
    CouponRedeemItem,
    CouponUpdateForm,
    CouponDestroyForm,
    CouponData,
    _parse_coupon_codes,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter(prefix="/billing", tags=["计费管理"])


############################
# 用户公司积分
############################


class UserCompanyCreditResponse(BaseModel):
    user_id: str = Field(description="用户ID")
    company_id: Optional[str] = Field(default=None, description="公司ID")
    company_name: Optional[str] = Field(default=None, description="公司名称")
    credit_balance: Decimal = Field(description="当前积分余额")
    last_updated: Optional[str] = Field(default=None, description="最后更新时间（UTC ISO8601）")


@router.get("/user/credit", response_model=UserCompanyCreditResponse, summary="获取用户所属公司的积分余额")
async def get_user_company_credit(user=Depends(get_verified_user)) -> UserCompanyCreditResponse:
    """
    返回当前登录用户所属公司（若有）的积分余额信息。
    """
    credit = Credits.init_credit_by_user_id(user.id)
    company_id = credit.company_id or getattr(user, "company_id", None)
    company_name: Optional[str] = None

    if company_id:
        company = Companies.get_company_by_id(company_id)
        if company:
            company_name = company.name
    last_updated_iso: Optional[str] = None
    if getattr(credit, "updated_at", None):
        try:
            last_updated_iso = (
                datetime.datetime.utcfromtimestamp(int(credit.updated_at))
                .replace(tzinfo=datetime.timezone.utc)
                .isoformat()
            )
        except (TypeError, ValueError):
            last_updated_iso = None

    return UserCompanyCreditResponse(
        user_id=user.id,
        company_id=company_id,
        company_name=company_name,
        credit_balance=credit.credit,
        last_updated=last_updated_iso,
    )


############################
# 计费配置管理
############################


@router.get("/configs", response_model=PaginatedBillingConfigResponse, summary="获取计费配置列表")
async def get_billing_configs(
    config_type: Optional[str] = Query(None, description="配置类型过滤"),
    is_active: Optional[bool] = Query(None, description="是否启用过滤"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_admin_user)
):
    """
    获取计费配置列表（分页）。
    
    Args:
        config_type (Optional[str]): 配置类型过滤
        is_active (Optional[bool]): 是否启用过滤
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的管理员用户对象
        
    Returns:
        PaginatedBillingConfigResponse: 分页的计费配置列表
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        configs = BillingConfigs.get_configs(
            config_type=config_type,
            is_active=is_active,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = BillingConfigs.get_configs_count(
            config_type=config_type,
            is_active=is_active
        )
        
        responses = [BillingConfigResponse(**config.model_dump()) for config in configs]
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedBillingConfigResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting billing configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/configs", response_model=BillingConfigResponse, summary="创建计费配置")
async def create_billing_config(
    form_data: BillingConfigForm,
    user=Depends(get_admin_user)
):
    """
    创建新的计费配置。
    
    Args:
        form_data (BillingConfigForm): 计费配置创建表单
        user: 已认证的管理员用户对象
        
    Returns:
        BillingConfigResponse: 创建的计费配置信息
    """
    try:
        config = BillingConfigs.insert_new_config(form_data)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create billing config"
            )
        
        return BillingConfigResponse(**config.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating billing config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/configs/{config_id}", response_model=BillingConfigResponse, summary="获取计费配置详情")
async def get_billing_config(
    config_id: str,
    user=Depends(get_admin_user)
):
    """获取单个计费配置详情"""
    try:
        config = BillingConfigs.get_config_by_id(config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Billing config not found"
            )
        
        return BillingConfigResponse(**config.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting billing config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.put("/configs/{config_id}", response_model=BillingConfigResponse, summary="更新计费配置")
async def update_billing_config(
    config_id: str,
    form_data: BillingConfigUpdateForm,
    user=Depends(get_admin_user)
):
    """更新计费配置"""
    try:
        config = BillingConfigs.update_config_by_id(config_id, form_data)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Billing config not found"
            )
        
        return BillingConfigResponse(**config.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating billing config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.delete("/configs/{config_id}", response_model=bool, summary="删除计费配置")
async def delete_billing_config(
    config_id: str,
    user=Depends(get_admin_user)
):
    """删除计费配置"""
    try:
        result = BillingConfigs.delete_config_by_id(config_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Billing config not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error deleting billing config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# API使用记录管理
############################


@router.get("/usage-logs", response_model=PaginatedAPIUsageLogResponse, summary="获取API使用记录列表")
async def get_api_usage_logs(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取API使用记录列表（分页）。
    
    Args:
        user_id (Optional[str]): 用户ID过滤
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedAPIUsageLogResponse: 分页的API使用记录列表
    """
    try:
        # 计算offset
        offset = (pi - 1) * ps
        
        # 如果不是管理员用户，只能查看自己的记录
        target_user_id = user.id
        if user_id:
            try:
                # 检查是否是管理员
                get_admin_user(user)
                # 如果是管理员，可以查看指定用户的记录
                target_user_id = user_id
            except HTTPException:
                # 如果不是管理员，只能查看自己的记录
                target_user_id = user.id
        else:
            target_user_id = user.id
        
        logs = APIUsageLogs.get_logs_by_user_id(
            user_id=target_user_id,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = APIUsageLogs.get_logs_count_by_user_id(target_user_id)
        
        responses = [APIUsageLogResponse(**log.model_dump()) for log in logs]
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        pagination = APIUsageLogPaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedAPIUsageLogResponse(
            data=responses,
            pagination=pagination
        )
        
    except Exception as e:
        log.exception(f"Error getting API usage logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/usage-logs", response_model=APIUsageLogResponse, summary="创建API使用记录")
async def create_api_usage_log(
    form_data: APIUsageLogForm,
    user=Depends(get_admin_user)
):
    """
    创建新的API使用记录。
    
    Args:
        form_data (APIUsageLogForm): API使用记录创建表单
        user: 已认证的管理员用户对象
        
    Returns:
        APIUsageLogResponse: 创建的API使用记录信息
    """
    try:
        log_entry = APIUsageLogs.insert_new_log(form_data)
        if not log_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create API usage log"
            )
        
        return APIUsageLogResponse(**log_entry.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating API usage log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/usage-logs/session/{session_id}", response_model=List[APIUsageLogResponse], summary="根据会话ID获取API使用记录")
async def get_api_usage_logs_by_session(
    session_id: str,
    user=Depends(get_verified_user)
):
    """根据会话ID获取API使用记录"""
    try:
        logs = APIUsageLogs.get_logs_by_session_id(session_id)
        
        # 检查用户权限 - 用户只能查看自己的记录
        if logs:
            first_log = logs[0]
            if first_log.user_id != user.id:
                # 检查是否是管理员
                try:
                    get_admin_user(user)
                except:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to view these logs"
                    )
        
        return [APIUsageLogResponse(**log.model_dump()) for log in logs]
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting API usage logs by session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/usage-logs/session/{session_id}/total", response_model=Decimal, summary="根据会话ID获取总消耗积分")
async def get_total_credits_consumed_by_session(
    session_id: str,
    user=Depends(get_verified_user)
):
    """根据会话ID获取总消耗积分"""
    try:
        logs = APIUsageLogs.get_logs_by_session_id(session_id)
        
        # 检查用户权限 - 用户只能查看自己的记录
        if logs:
            first_log = logs[0]
            if first_log.user_id != user.id:
                # 检查是否是管理员
                try:
                    get_admin_user(user)
                except:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to view these logs"
                    )
        
        total = APIUsageLogs.get_total_credits_consumed_by_session(session_id)
        return total
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting total credits consumed by session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# 卡券充值（用户侧）
############################


@router.post(
    "/coupons/redeem",
    response_model=CouponRedeemResponse,
    # Use unicode escapes to avoid any editor/encoding issues leaking into OpenAPI.
    summary="\u9a8c\u5238\u5145\u503c\uff08\u652f\u6301\u591a\u5238\u7801\uff0c\\n \u6362\u884c\u5206\u9694\uff09",
)
async def redeem_coupons(
    form_data: CouponRedeemForm,
    request: Request,
    user=Depends(get_verified_user),
) -> CouponRedeemResponse:
    deduped, duplicates, submitted = _parse_coupon_codes(form_data.coupons)
    if submitted == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="coupons is empty")
    if submitted > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="too many coupons (max=100)")

    # 先把“请求内重复”的结果写入 items，再处理去重后的券码实际兑换
    duplicate_items: List[CouponRedeemItem] = []
    for code, dup_count in duplicates.items():
        for _ in range(dup_count):
            duplicate_items.append(
                CouponRedeemItem(code=code, status="FAILED", reason="DUPLICATED_IN_REQUEST")
            )

    client_ip = request.client.host if request.client else None
    resp = Coupons.redeem(user_id=user.id, codes=deduped, client_ip=client_ip)

    # 调整统计口径：submitted/deduped 以解析结果为准；items 要包含重复券码的失败项
    resp.total_submitted = submitted
    resp.total_deduped = len(deduped)
    if duplicate_items:
        resp.items.extend(duplicate_items)
        resp.total_failed += len(duplicate_items)
    return resp


############################
# 卡券管理（后台/管理员）
############################


class PaginatedCouponResponse(BaseModel):
    data: List[CouponData]
    pagination: PaginationData


@router.post(
    "/admin/coupons/batch",
    response_model=CouponBatchCreateResponse,
    summary="[\u540e\u53f0] \u6279\u91cf\u521b\u5efa\u5361\u5238",
)
async def admin_create_coupon_batch(
    form_data: CouponBatchCreateForm,
    user=Depends(get_admin_user),
) -> CouponBatchCreateResponse:
    return Coupons.create_batch(form=form_data, created_by_user_id=getattr(user, "id", None))


@router.get(
    "/admin/coupons",
    response_model=PaginatedCouponResponse,
    summary="[\u540e\u53f0] \u5361\u5238\u5217\u8868\uff08\u5206\u9875/\u7b5b\u9009\uff09",
)
async def admin_list_coupons(
    channel: Optional[str] = Query(None, description="\u6295\u653e\u6e20\u9053\u7b5b\u9009"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="\u72b6\u6001\u7b5b\u9009\uff08UNUSED|USED|DESTROYED\uff09",
    ),
    q: Optional[str] = Query(None, description="\u5238\u7801\u5173\u952e\u5b57\uff08\u6a21\u7cca\u5339\u914d\uff09"),
    expires_from: Optional[int] = Query(
        None, description="\u5230\u671f\u65f6\u95f4\u8d77\uff08UTC epoch seconds\uff09"
    ),
    expires_to: Optional[int] = Query(
        None, description="\u5230\u671f\u65f6\u95f4\u6b62\uff08UTC epoch seconds\uff09"
    ),
    ps: int = Query(20, description="\u5206\u9875\u5927\u5c0f", ge=1, le=100),
    pi: int = Query(1, description="\u5206\u9875\u7d22\u5f15\uff08\u4ece1\u5f00\u59cb\uff09", ge=1),
    user=Depends(get_admin_user),
):
    offset = (pi - 1) * ps
    total, data = Coupons.list_coupons(
        channel=channel,
        status=status_filter,
        q=q,
        expires_from=expires_from,
        expires_to=expires_to,
        limit=ps,
        offset=offset,
    )
    total_pages = (total + ps - 1) // ps
    return PaginatedCouponResponse(
        data=data,
        pagination=PaginationData(total=total, page=pi, size=ps, total_pages=total_pages),
    )


@router.get(
    "/admin/coupons/lookup",
    response_model=Optional[CouponData],
    summary="[\u540e\u53f0] \u5238\u7801\u67e5\u8be2\uff08\u7cbe\u786e\uff09",
)
async def admin_lookup_coupon_by_code(
    code: str = Query(..., min_length=1, description="券码"),
    user=Depends(get_admin_user),
):
    return Coupons.lookup_by_code(code=code)


@router.put(
    "/admin/coupons/{coupon_id}",
    response_model=CouponData,
    summary="[\u540e\u53f0] \u4fee\u6539\u5361\u5238\u4fe1\u606f\uff08\u4ec5\u672a\u4f7f\u7528\u4e14\u672a\u8fc7\u671f\uff09",
)
async def admin_update_coupon(
    coupon_id: str,
    form_data: CouponUpdateForm,
    user=Depends(get_admin_user),
):
    updated = Coupons.update_coupon(coupon_id=coupon_id, form=form_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    return updated


@router.post(
    "/admin/coupons/{coupon_id}/destroy",
    response_model=bool,
    summary="[\u540e\u53f0] \u5f3a\u5236\u9500\u6bc1\u5361\u5238",
)
async def admin_destroy_coupon(
    coupon_id: str,
    form_data: CouponDestroyForm,
    user=Depends(get_admin_user),
):
    ok = Coupons.destroy_coupon(
        coupon_id=coupon_id,
        destroyed_by_user_id=getattr(user, "id", None),
        reason=form_data.reason,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    return ok
