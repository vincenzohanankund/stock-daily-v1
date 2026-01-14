# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta

from config import get_config
from storage import get_db, StockDaily
from data_provider.akshare_fetcher import AkshareFetcher
from main import StockAnalysisPipeline
from core.analyzer import STOCK_NAME_MAP

router = APIRouter()

@router.get("/list")
async def get_stock_list():
    """获取自选股列表及最新状态"""
    config = get_config()
    db = get_db()
    fetcher = AkshareFetcher()
    
    stock_codes = config.stock_list
    result = []
    
    for code in stock_codes:
        # 获取名称
        name = STOCK_NAME_MAP.get(code, f"股票{code}")
        
        # 获取最新数据（从数据库）
        latest_data = db.get_latest_data(code, days=1)
        
        stock_info = {
            "code": code,
            "name": name,
            "price": 0.0,
            "pct_chg": 0.0,
            "volume_ratio": 0.0,
            "ma_status": "未知",
            "updated_at": ""
        }
        
        if latest_data:
            data = latest_data[0]
            stock_info.update({
                "price": data.close,
                "pct_chg": data.pct_chg,
                "volume_ratio": data.volume_ratio,
                "updated_at": data.date.isoformat()
            })
            
            # 简单的均线状态判断
            if data.ma5 and data.ma10 and data.ma20:
                if data.close > data.ma5 > data.ma10 > data.ma20:
                    stock_info["ma_status"] = "多头排列"
                elif data.close < data.ma5 < data.ma10 < data.ma20:
                    stock_info["ma_status"] = "空头排列"
                else:
                    stock_info["ma_status"] = "震荡"
        
        # 仅返回数据库中的数据，不进行实时抓取，避免阻塞
        result.append(stock_info)
        
    return result

@router.get("/kline/{code}")
async def get_stock_kline(code: str, days: int = 60):
    """获取K线数据"""
    db = get_db()
    
    # 获取最近 N 天数据
    end_date = date.today()
    start_date = end_date - timedelta(days=days * 1.5) # 多取一些以防非交易日
    
    data_list = db.get_data_range(code, start_date, end_date)
    
    # 格式化为 ECharts 格式
    # 数据顺序：[date, open, close, low, high, volume]
    category_data = []
    values = []
    volumes = []
    
    for d in data_list:
        date_str = d.date.isoformat()
        category_data.append(date_str)
        values.append([d.open, d.close, d.low, d.high])
        volumes.append([len(category_data)-1, d.volume, 1 if d.close > d.open else -1])
        
    return {
        "categoryData": category_data,
        "values": values,
        "volumes": volumes,
        "ma5": [d.ma5 for d in data_list],
        "ma10": [d.ma10 for d in data_list],
        "ma20": [d.ma20 for d in data_list],
    }

@router.get("/analysis/{code}")
async def get_stock_analysis(code: str):
    """获取最新分析结果"""
    db = get_db()
    analysis = db.get_latest_analysis(code)
    
    if analysis:
        return analysis
        
    # 如果没有分析结果，返回空或默认提示
    return {
        "sentiment_score": 50,
        "trend_prediction": "暂无分析",
        "operation_advice": "待更新",
        "analysis_summary": "暂无 AI 分析报告，请点击右上角“更新数据”进行分析。",
        "dashboard": None
    }

def fetch_stock_task(code: str):
    """后台任务：仅抓取数据"""
    pipeline = StockAnalysisPipeline()
    pipeline.fetch_and_save_stock_data(code, force_refresh=True)
    print(f"[{code}] 数据抓取完成")

def analyze_stock_task(code: str):
    """后台任务：执行 AI 分析（包含必要的数据检查）"""
    import logging
    logger = logging.getLogger("web.api.stock")
    
    pipeline = StockAnalysisPipeline()
    db = get_db()
    
    logger.info(f"[{code}] 开始 AI 分析任务...")
    print(f"[{code}] 开始 AI 分析...")
    
    # 分析前先检查今日数据是否存在，不存在则补充抓取
    # force_refresh=False 表示只有数据不存在时才抓取，避免频繁请求
    logger.info(f"[{code}] 检查数据完整性...")
    print(f"[{code}] 检查数据完整性...")
    
    try:
        success, error = pipeline.fetch_and_save_stock_data(code, force_refresh=False)
        if not success:
            logger.warning(f"[{code}] 数据检查/获取失败: {error}")
            print(f"[{code}] 数据检查/获取失败: {error}")
            # 继续尝试分析，可能使用历史数据
        else:
            logger.info(f"[{code}] 数据检查通过")
            
        result = pipeline.analyze_stock(code)
        
        if result:
            db.save_analysis_result(result.to_dict())
            logger.info(f"[{code}] AI 分析完成并保存")
            print(f"[{code}] AI 分析完成并保存")
        else:
            logger.error(f"[{code}] AI 分析失败")
            print(f"[{code}] AI 分析失败")
            
    except Exception as e:
        logger.exception(f"[{code}] 分析任务发生异常: {e}")
        print(f"[{code}] 分析任务发生异常: {e}")

@router.post("/fetch/{code}")
async def fetch_stock_data(code: str, background_tasks: BackgroundTasks):
    """触发后台数据抓取任务（不包含 AI 分析）"""
    background_tasks.add_task(fetch_stock_task, code)
    return {"message": f"已触发 {code} 的数据抓取任务"}

@router.post("/analyze/{code}")
async def analyze_stock_data(code: str, background_tasks: BackgroundTasks):
    """触发后台 AI 分析任务"""
    background_tasks.add_task(analyze_stock_task, code)
    return {"message": f"已触发 {code} 的 AI 分析任务"}