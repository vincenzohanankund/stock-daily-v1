# -*- coding: utf-8 -*-
"""
===================================
股票数据相关模型
===================================

职责：
1. 定义股票实时行情模型
2. 定义历史 K 线数据模型
"""

from typing import Optional, List

from pydantic import BaseModel, Field


class StockQuote(BaseModel):
    """股票实时行情"""
    
    stock_code: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    current_price: float = Field(..., description="当前价格")
    change: Optional[float] = Field(None, description="涨跌额")
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    prev_close: Optional[float] = Field(None, description="昨收价")
    volume: Optional[float] = Field(None, description="成交量（股）")
    amount: Optional[float] = Field(None, description="成交额（元）")
    update_time: Optional[str] = Field(None, description="更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "current_price": 1800.00,
                "change": 15.00,
                "change_percent": 0.84,
                "open": 1785.00,
                "high": 1810.00,
                "low": 1780.00,
                "prev_close": 1785.00,
                "volume": 10000000,
                "amount": 18000000000,
                "update_time": "2024-01-01T15:00:00"
            }
        }


class KLineData(BaseModel):
    """K 线数据点"""
    
    date: str = Field(..., description="日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: Optional[float] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-01",
                "open": 1785.00,
                "high": 1810.00,
                "low": 1780.00,
                "close": 1800.00,
                "volume": 10000000,
                "amount": 18000000000,
                "change_percent": 0.84
            }
        }


class StockHistoryResponse(BaseModel):
    """股票历史行情响应"""
    
    stock_code: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    period: str = Field(..., description="K 线周期")
    data: List[KLineData] = Field(default_factory=list, description="K 线数据列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "period": "daily",
                "data": []
            }
        }


class WatchlistItem(BaseModel):
    """Watchlist item."""

    stock_code: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    last_analysis_time: Optional[str] = Field(None, description="最近分析时间")
    last_price: Optional[float] = Field(None, description="最近价格")
    change_pct: Optional[float] = Field(None, description="最近涨跌幅(%)")
    trend_prediction: Optional[str] = Field(None, description="趋势预测")
    operation_advice: Optional[str] = Field(None, description="操作建议")


class WatchlistRefreshTask(BaseModel):
    """Watchlist refresh task state."""

    task_id: Optional[str] = Field(None, description="刷新任务 ID")
    status: str = Field(..., description="任务状态: idle/processing/completed/failed")
    completed: bool = Field(False, description="任务是否已结束")
    is_new_task: bool = Field(False, description="是否本次请求新建任务")
    progress_total: int = Field(0, description="任务总进度")
    progress_done: int = Field(0, description="已完成进度")
    started_at: Optional[str] = Field(None, description="开始时间")
    finished_at: Optional[str] = Field(None, description="结束时间")
    error: Optional[str] = Field(None, description="失败原因")


class WatchlistResponse(BaseModel):
    """Watchlist response."""

    total: int = Field(..., description="总数")
    items: List[WatchlistItem] = Field(default_factory=list, description="关注股票列表")
    refresh_mode: Optional[str] = Field(None, description="行情刷新模式: blocking/async")
    refresh_task: Optional[WatchlistRefreshTask] = Field(None, description="异步刷新任务状态")


class WatchlistAddRequest(BaseModel):
    """Add watchlist stock request."""

    stock_code: str = Field(..., description="股票代码", examples=["600519"])


class WatchlistReplaceRequest(BaseModel):
    """Replace watchlist request."""

    stock_codes: List[str] = Field(default_factory=list, description="股票代码列表")


class WatchlistMutationResponse(BaseModel):
    """Watchlist mutation response."""

    success: bool = Field(True, description="是否成功")
    stock_code: Optional[str] = Field(None, description="变更的股票代码")
    added: Optional[bool] = Field(None, description="新增动作是否生效")
    removed: Optional[bool] = Field(None, description="删除动作是否生效")
    total: Optional[int] = Field(None, description="当前总数")
    stock_list: List[str] = Field(default_factory=list, description="最新股票列表")
