# -*- coding: utf-8 -*-
"""
===================================
股票数据接口
===================================

职责：
1. 提供 GET /api/v1/stocks/{code}/quote 实时行情接口
2. 提供 GET /api/v1/stocks/{code}/history 历史行情接口
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from api.v1.schemas.stocks import (
    StockQuote,
    StockHistoryResponse,
    KLineData,
    WatchlistResponse,
    WatchlistItem,
    WatchlistAddRequest,
    WatchlistReplaceRequest,
    WatchlistMutationResponse,
    WatchlistRefreshTask,
)
from api.v1.schemas.common import ErrorResponse
from src.services.stock_service import StockService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/watchlist",
    response_model=WatchlistResponse,
    responses={
        200: {"description": "关注股票列表"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取关注股票列表",
    description="获取当前关注股票列表（基于 STOCK_LIST），支持阻塞刷新和异步刷新模式"
)
@router.get("/watchlist/", include_in_schema=False)
def get_watchlist(
    include_quote: bool = Query(True, description="是否包含实时行情，默认 true"),
    refresh_async: bool = Query(False, description="是否异步刷新行情，默认 false"),
    force_refresh: bool = Query(False, description="异步模式下是否强制新建刷新任务"),
) -> WatchlistResponse:
    """Get watchlist items."""
    try:
        service = StockService()

        if include_quote and refresh_async:
            result = service.get_watchlist_cached_snapshot(include_quote=True)
            refresh_task = service.start_watchlist_refresh(force=force_refresh)
            items = [WatchlistItem(**item) for item in result.get('items', [])]
            return WatchlistResponse(
                total=result.get('total', len(items)),
                items=items,
                refresh_mode='async',
                refresh_task=WatchlistRefreshTask(**refresh_task),
            )

        result = service.get_watchlist(include_quote=include_quote)
        items = [WatchlistItem(**item) for item in result.get('items', [])]
        return WatchlistResponse(
            total=result.get('total', len(items)),
            items=items,
            refresh_mode='blocking',
        )
    except Exception as e:
        logger.error(f"获取关注列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"获取关注列表失败: {str(e)}"
            }
        )


@router.post(
    "/watchlist/refresh",
    response_model=WatchlistRefreshTask,
    responses={
        200: {"description": "刷新任务状态"},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="触发行情异步刷新",
    description="启动（或复用）自选股行情异步刷新任务，适合前端轮询模式"
)
@router.post("/watchlist/refresh/", include_in_schema=False)
def trigger_watchlist_refresh(
    force: bool = Query(False, description="是否强制新建刷新任务")
) -> WatchlistRefreshTask:
    """Trigger a watchlist quote refresh task."""
    try:
        service = StockService()
        status = service.start_watchlist_refresh(force=force)
        return WatchlistRefreshTask(**status)
    except Exception as e:
        logger.error(f"触发行情刷新失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"触发行情刷新失败: {str(e)}"
            }
        )


@router.get(
    "/watchlist/refresh",
    response_model=WatchlistRefreshTask,
    responses={
        200: {"description": "刷新任务状态"},
        404: {"description": "任务不存在", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="查询行情刷新状态",
    description="查询当前或指定 task_id 的自选股行情刷新状态"
)
@router.get("/watchlist/refresh/", include_in_schema=False)
def get_watchlist_refresh_status(
    task_id: str | None = Query(None, description="刷新任务 ID，不传则返回当前任务")
) -> WatchlistRefreshTask:
    """Get watchlist refresh task status."""
    try:
        service = StockService()
        status = service.get_watchlist_refresh_status(task_id=task_id)
        if status.get('status') == 'not_found':
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": "刷新任务不存在或已过期"
                }
            )
        return WatchlistRefreshTask(**status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询行情刷新状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"查询行情刷新状态失败: {str(e)}"
            }
        )


@router.post(
    "/watchlist",
    response_model=WatchlistMutationResponse,
    responses={
        200: {"description": "新增成功"},
        400: {"description": "参数错误", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="新增关注股票",
    description="新增关注股票并同步更新 STOCK_LIST 配置"
)
@router.post("/watchlist/", include_in_schema=False)
def add_watchlist_stock(request: WatchlistAddRequest) -> WatchlistMutationResponse:
    """Add a stock into watchlist."""
    try:
        service = StockService()
        result = service.add_watchlist_stock(request.stock_code)
        return WatchlistMutationResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"新增关注股票失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"新增关注股票失败: {str(e)}"
            }
        )


@router.put(
    "/watchlist",
    response_model=WatchlistMutationResponse,
    responses={
        200: {"description": "覆盖成功"},
        400: {"description": "参数错误", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="覆盖关注股票列表",
    description="批量覆盖关注股票并同步更新 STOCK_LIST 配置"
)
@router.put("/watchlist/", include_in_schema=False)
def replace_watchlist(request: WatchlistReplaceRequest) -> WatchlistMutationResponse:
    """Replace watchlist in batch."""
    try:
        service = StockService()
        result = service.replace_watchlist(request.stock_codes)
        return WatchlistMutationResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"覆盖关注列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"覆盖关注列表失败: {str(e)}"
            }
        )


@router.delete(
    "/watchlist/{stock_code}",
    response_model=WatchlistMutationResponse,
    responses={
        200: {"description": "删除成功"},
        400: {"description": "参数错误", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="删除关注股票",
    description="删除关注股票并同步更新 STOCK_LIST 配置"
)
@router.delete("/watchlist/{stock_code}/", include_in_schema=False)
def remove_watchlist_stock(stock_code: str) -> WatchlistMutationResponse:
    """Remove a stock from watchlist."""
    try:
        service = StockService()
        result = service.remove_watchlist_stock(stock_code)
        return WatchlistMutationResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"删除关注股票失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"删除关注股票失败: {str(e)}"
            }
        )


@router.delete(
    "/watchlist",
    response_model=WatchlistMutationResponse,
    include_in_schema=False,
)
@router.delete(
    "/watchlist/",
    response_model=WatchlistMutationResponse,
    include_in_schema=False,
)
def remove_watchlist_stock_by_query(
    stock_code: str = Query(..., description="股票代码")
) -> WatchlistMutationResponse:
    """Remove a stock from watchlist by query parameter."""
    return remove_watchlist_stock(stock_code)


@router.get(
    "/{stock_code}/quote",
    response_model=StockQuote,
    responses={
        200: {"description": "行情数据"},
        404: {"description": "股票不存在", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取股票实时行情",
    description="获取指定股票的最新行情数据"
)
def get_stock_quote(stock_code: str) -> StockQuote:
    """
    获取股票实时行情
    
    获取指定股票的最新行情数据
    
    Args:
        stock_code: 股票代码（如 600519、00700、AAPL）
        
    Returns:
        StockQuote: 实时行情数据
        
    Raises:
        HTTPException: 404 - 股票不存在
    """
    try:
        service = StockService()
        
        # 使用 def 而非 async def，FastAPI 自动在线程池中执行
        result = service.get_realtime_quote(stock_code)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"未找到股票 {stock_code} 的行情数据"
                }
            )
        
        return StockQuote(
            stock_code=result.get("stock_code", stock_code),
            stock_name=result.get("stock_name"),
            current_price=result.get("current_price", 0.0),
            change=result.get("change"),
            change_percent=result.get("change_percent"),
            open=result.get("open"),
            high=result.get("high"),
            low=result.get("low"),
            prev_close=result.get("prev_close"),
            volume=result.get("volume"),
            amount=result.get("amount"),
            update_time=result.get("update_time")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实时行情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"获取实时行情失败: {str(e)}"
            }
        )


@router.get(
    "/{stock_code}/history",
    response_model=StockHistoryResponse,
    responses={
        200: {"description": "历史行情数据"},
        422: {"description": "不支持的周期参数", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="获取股票历史行情",
    description="获取指定股票的历史 K 线数据"
)
def get_stock_history(
    stock_code: str,
    period: str = Query("daily", description="K 线周期", pattern="^(daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365, description="获取天数")
) -> StockHistoryResponse:
    """
    获取股票历史行情
    
    获取指定股票的历史 K 线数据
    
    Args:
        stock_code: 股票代码
        period: K 线周期 (daily/weekly/monthly)
        days: 获取天数
        
    Returns:
        StockHistoryResponse: 历史行情数据
    """
    try:
        service = StockService()
        
        # 使用 def 而非 async def，FastAPI 自动在线程池中执行
        result = service.get_history_data(
            stock_code=stock_code,
            period=period,
            days=days
        )
        
        # 转换为响应模型
        data = [
            KLineData(
                date=item.get("date"),
                open=item.get("open"),
                high=item.get("high"),
                low=item.get("low"),
                close=item.get("close"),
                volume=item.get("volume"),
                amount=item.get("amount"),
                change_percent=item.get("change_percent")
            )
            for item in result.get("data", [])
        ]
        
        return StockHistoryResponse(
            stock_code=stock_code,
            stock_name=result.get("stock_name"),
            period=period,
            data=data
        )
    
    except ValueError as e:
        # period 参数不支持的错误（如 weekly/monthly）
        raise HTTPException(
            status_code=422,
            detail={
                "error": "unsupported_period",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"获取历史行情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"获取历史行情失败: {str(e)}"
            }
        )
