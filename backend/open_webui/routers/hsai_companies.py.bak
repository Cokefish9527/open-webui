@router.get("/{company_id}/projects", response_model=PaginatedHSAIProjectResponse, summary="获取公司项目列表")
async def get_company_projects(
    company_id: str,
    status: Optional[str] = Query(None, description="项目状态过滤"),
    ps: int = Query(20, description="分页大小", ge=1, le=100),
    pi: int = Query(1, description="分页索引，从1开始", ge=1),
    user=Depends(get_verified_user)
):
    """
    获取指定公司的项目列表（分页）。
    
    Args:
        company_id (str): 公司ID
        status (Optional[str]): 项目状态过滤
        ps (int): 分页大小，范围1-100
        pi (int): 分页索引，从1开始
        user: 已认证的用户对象
        
    Returns:
        PaginatedHSAIProjectResponse: 分页的项目列表
    """
    try:
        # 验证公司所有权
        company = Companies.get_company_by_id(company_id)
        if not company or company.owner_user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        # 计算offset
        offset = (pi - 1) * ps
        
        projects = HSAIProjects.get_projects_by_company_id(
            company_id,
            status=status,
            limit=ps,
            offset=offset
        )
        
        # 获取总数
        total = HSAIProjects.get_projects_count_by_company_id(
            company_id,
            status=status
        )
        
        responses = [HSAIProjectResponse(**project.model_dump()) for project in projects]
        
        # 计算分页数据
        total_pages = (total + ps - 1) // ps  # 向上取整
        
        # 使用项目模块中的PaginationData
        pagination = PaginationData(
            total=total,
            page=pi,
            size=ps,
            total_pages=total_pages
        )
        
        return PaginatedHSAIProjectResponse(
            data=responses,
            pagination=pagination
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting company projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )