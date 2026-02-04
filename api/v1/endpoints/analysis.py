# -*- coding: utf-8 -*-
"""
===================================
股票分析接口
===================================

职责：
1. 提供 POST /api/v1/analysis/analyze 触发分析接口
2. 提供 GET /api/v1/analysis/status/{task_id} 查询任务状态接口
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from api.deps import get_config_dep
from api.v1.schemas.analysis import (
    AnalyzeRequest,
    AnalysisResultResponse,
    TaskStatus,
)
from api.v1.schemas.common import ErrorResponse
from src.config import Config
from src.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalysisResultResponse,
    responses={
        200: {"description": "分析完成（同步模式）"},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        501: {"description": "异步模式未实现", "model": ErrorResponse},
        500: {"description": "分析失败", "model": ErrorResponse},
    }
)
async def trigger_analysis(
    request: AnalyzeRequest,
    config: Config = Depends(get_config_dep)
) -> AnalysisResultResponse:
    """
    触发股票分析
    
    启动 AI 智能分析任务，支持单只或多只股票批量分析
    
    Args:
        request: 分析请求参数
        config: 配置依赖
        
    Returns:
        AnalysisResultResponse: 分析结果
        
    Raises:
        HTTPException: 400 - 请求参数错误
        HTTPException: 500 - 分析失败
    """
    # 校验请求参数
    stock_codes = []
    if request.stock_code:
        stock_codes.append(request.stock_code)
    if request.stock_codes:
        stock_codes.extend(request.stock_codes)
    
    if not stock_codes:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": "必须提供 stock_code 或 stock_codes 参数"
            }
        )
    
    # 去重
    stock_codes = list(dict.fromkeys(stock_codes))
    
    # 生成 query_id
    query_id = uuid.uuid4().hex
    
    # 目前只支持同步模式，异步模式返回 501
    if request.async_mode:
        raise HTTPException(
            status_code=501,
            detail={
                "error": "not_implemented",
                "message": "异步模式暂未实现，请使用 async_mode=false 或省略该参数"
            }
        )
    
    try:
        # 调用分析服务
        service = AnalysisService()
        
        # 执行分析（取第一个股票代码）
        result = service.analyze_stock(
            stock_code=stock_codes[0],
            report_type=request.report_type,
            force_refresh=request.force_refresh,
            query_id=query_id
        )
        
        if result is None:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "analysis_failed",
                    "message": f"分析股票 {stock_codes[0]} 失败"
                }
            )
        
        # 构建响应
        return AnalysisResultResponse(
            query_id=query_id,
            stock_code=result.get("stock_code", stock_codes[0]),
            stock_name=result.get("stock_name"),
            report=result.get("report"),
            created_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"分析过程发生错误: {str(e)}"
            }
        )


@router.get(
    "/status/{task_id}",
    response_model=TaskStatus,
    responses={
        200: {"description": "任务状态"},
        404: {"description": "任务不存在", "model": ErrorResponse},
        501: {"description": "异步模式未实现", "model": ErrorResponse},
    }
)
async def get_analysis_status(task_id: str) -> TaskStatus:
    """
    查询分析任务状态
    
    用于异步模式下轮询任务完成状态
    
    Args:
        task_id: 任务 ID
        
    Returns:
        TaskStatus: 任务状态信息
        
    Raises:
        HTTPException: 404 - 任务不存在
        HTTPException: 501 - 异步模式未实现
    """
    # 异步任务队列尚未实现，返回 501
    raise HTTPException(
        status_code=501,
        detail={
            "error": "not_implemented",
            "message": "异步任务状态查询暂未实现，请使用同步模式分析"
        }
    )
