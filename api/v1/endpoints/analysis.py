# -*- coding: utf-8 -*-
"""
===================================
股票分析接口
===================================

职责：
1. 提供 POST /api/v1/analysis/analyze 触发分析接口
2. 提供 GET /api/v1/analysis/status/{task_id} 查询任务状态接口

注意：
- 同步阻塞操作使用 def（非 async def），FastAPI 会自动放到线程池执行
- 这样不会阻塞事件循环，其他请求可以正常处理
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Union, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from api.deps import get_config_dep
from api.v1.schemas.analysis import (
    AnalyzeRequest,
    AnalysisResultResponse,
    TaskAccepted,
    TaskStatus,
)
from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.history import (
    AnalysisReport,
    ReportMeta,
    ReportSummary,
    ReportStrategy,
    ReportDetails,
)
from src.config import Config
from src.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalysisResultResponse,
    responses={
        200: {"description": "分析完成（同步模式）", "model": AnalysisResultResponse},
        202: {"description": "分析任务已接受（异步模式）", "model": TaskAccepted},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        500: {"description": "分析失败", "model": ErrorResponse},
    },
    summary="触发股票分析",
    description="启动 AI 智能分析任务，支持单只或多只股票批量分析"
)
def trigger_analysis(
        request: AnalyzeRequest,
        config: Config = Depends(get_config_dep)
) -> Union[AnalysisResultResponse, JSONResponse]:
    """
    触发股票分析
    
    启动 AI 智能分析任务，支持单只或多只股票批量分析
    
    注意：使用 def 而非 async def，FastAPI 会自动将其放到线程池执行，
    不会阻塞事件循环，其他请求可以正常处理。
    
    Args:
        request: 分析请求参数
        config: 配置依赖
        
    Returns:
        AnalysisResultResponse: 分析结果（同步模式）
        TaskAccepted: 任务已接受（异步模式，返回 202）
        
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

    # 生成 query_id / task_id
    query_id = uuid.uuid4().hex

    # 异步模式：返回 202 并在后台处理
    if request.async_mode:
        # 当前异步任务队列尚未实现，返回 202 表示接受任务
        # TODO: 实现真正的异步任务队列（如 Celery、Redis Queue）
        task_accepted = TaskAccepted(
            task_id=query_id,
            status="pending",
            message="Analysis task accepted. Async mode is not fully implemented yet."
        )
        return JSONResponse(
            status_code=202,
            content=task_accepted.model_dump()
        )

    try:
        # 调用分析服务
        # 注意：因为使用 def，FastAPI 自动在线程池中执行，不会阻塞
        service = AnalysisService()
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

        # 构建报告结构
        report_data = result.get("report", {})
        report = _build_analysis_report(report_data, query_id, stock_codes[0], result.get("stock_name"))

        # 构建响应
        return AnalysisResultResponse(
            query_id=query_id,
            stock_code=result.get("stock_code", stock_codes[0]),
            stock_name=result.get("stock_name"),
            report=report.model_dump() if report else None,
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
    },
    summary="查询分析任务状态",
    description="用于异步模式下轮询任务完成状态"
)
def get_analysis_status(task_id: str) -> TaskStatus:
    """
    查询分析任务状态
    
    用于异步模式下轮询任务完成状态
    
    Args:
        task_id: 任务 ID
        
    Returns:
        TaskStatus: 任务状态信息
        
    Raises:
        HTTPException: 404 - 任务不存在
    """
    try:
        # 查询是否有对应的分析记录（通过 query_id）
        from src.storage import DatabaseManager
        db = DatabaseManager.get_instance()
        records = db.get_analysis_history(query_id=task_id, limit=1)

        if records:
            # 已完成的任务
            record = records[0]
            return TaskStatus(
                task_id=task_id,
                status="completed",
                progress=100,
                result=AnalysisResultResponse(
                    query_id=task_id,
                    stock_code=record.code,
                    stock_name=record.name,
                    report=None,  # 可根据需要填充完整报告
                    created_at=record.created_at.isoformat() if record.created_at else datetime.now().isoformat()
                ),
                error=None
            )

        # 任务不存在或尚未完成
        # TODO: 实现任务队列状态查询
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"任务 {task_id} 不存在或已过期"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"查询任务状态失败: {str(e)}"
            }
        )


def _build_analysis_report(
        report_data: Dict[str, Any],
        query_id: str,
        stock_code: str,
        stock_name: Optional[str] = None
) -> AnalysisReport:
    """
    构建符合 API 规范的分析报告
    
    Args:
        report_data: 原始报告数据
        query_id: 查询 ID
        stock_code: 股票代码
        stock_name: 股票名称
        
    Returns:
        AnalysisReport: 结构化的分析报告
    """
    meta_data = report_data.get("meta", {})
    summary_data = report_data.get("summary", {})
    strategy_data = report_data.get("strategy", {})
    details_data = report_data.get("details", {})

    meta = ReportMeta(
        query_id=meta_data.get("query_id", query_id),
        stock_code=meta_data.get("stock_code", stock_code),
        stock_name=meta_data.get("stock_name", stock_name),
        report_type=meta_data.get("report_type", "detailed"),
        created_at=meta_data.get("created_at", datetime.now().isoformat())
    )

    summary = ReportSummary(
        analysis_summary=summary_data.get("analysis_summary"),
        operation_advice=summary_data.get("operation_advice"),
        trend_prediction=summary_data.get("trend_prediction"),
        sentiment_score=summary_data.get("sentiment_score"),
        sentiment_label=summary_data.get("sentiment_label")
    )

    strategy = None
    if strategy_data:
        strategy = ReportStrategy(
            ideal_buy=strategy_data.get("ideal_buy"),
            secondary_buy=strategy_data.get("secondary_buy"),
            stop_loss=strategy_data.get("stop_loss"),
            take_profit=strategy_data.get("take_profit")
        )

    details = None
    if details_data:
        details = ReportDetails(
            news_content=details_data.get("news_summary") or details_data.get("news_content"),
            raw_result=details_data,
            context_snapshot=None
        )

    return AnalysisReport(
        meta=meta,
        summary=summary,
        strategy=strategy,
        details=details
    )
