# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from datetime import date

from storage import get_db
from core.market_analyzer import MarketAnalyzer
from core.search_service import get_search_service
from core.analyzer import get_analyzer

router = APIRouter()

@router.get("/latest")
async def get_latest_market_review():
    """获取最新大盘复盘"""
    db = get_db()
    review = db.get_market_review()
    
    if review:
        # 如果数据库返回的数据没有 news 字段（旧数据），补充为空列表
        if 'news' not in review:
            review['news'] = []
        return review
        
    return {
        "date": date.today().isoformat(),
        "report_content": "暂无大盘复盘报告，请点击“立即分析”进行生成。",
        "overview": None,
        "news": []
    }

def analyze_market_task():
    """后台任务：执行大盘复盘分析"""
    import logging
    logger = logging.getLogger("web.api.market")
    
    logger.info("开始大盘复盘分析任务...")
    
    try:
        # 初始化服务
        # 使用 get_search_service() 单例获取服务，确保从 config 加载了 API Key
        search_service = get_search_service()
        ai_analyzer = get_analyzer()
        market_analyzer = MarketAnalyzer(search_service, ai_analyzer)
        
        # 1. 获取市场概览
        overview = market_analyzer.get_market_overview()
        
        # 2. 搜索市场新闻
        news = market_analyzer.search_market_news()
        
        # 3. 生成复盘报告
        # 注意：MarketAnalyzer.run_daily_review 已经修改为返回字典 {'report': str, 'news': list}
        # 但这里我们是分别调用的，所以 generate_market_review 依然返回字符串
        report = market_analyzer.generate_market_review(overview, news)
        
        # 4. 保存结果
        db = get_db()
        
        # 转换 MarketIndex 对象为字典
        overview_dict = {
            'date': overview.date,
            'indices': [idx.to_dict() for idx in overview.indices],
            'up_count': overview.up_count,
            'down_count': overview.down_count,
            'flat_count': overview.flat_count,
            'limit_up_count': overview.limit_up_count,
            'limit_down_count': overview.limit_down_count,
            'total_amount': overview.total_amount,
            'north_flow': overview.north_flow,
            'top_sectors': overview.top_sectors,
            'bottom_sectors': overview.bottom_sectors
        }
        
        # 转换新闻对象为字典 (如果是 SearchResult 对象)
        news_list = []
        for item in news:
            if hasattr(item, 'to_text'):  # SearchResult 对象
                news_list.append({
                    'title': item.title,
                    'snippet': item.snippet,
                    'url': item.url,
                    'source': item.source,
                    'published_date': item.published_date
                })
            else:  # 已经是字典
                news_list.append(item)
        
        if db.save_market_review(overview.date, report, overview_dict, news_list):
            logger.info(f"大盘复盘保存成功: {overview.date}")
        else:
            logger.error("大盘复盘保存失败")
            
    except Exception as e:
        logger.exception(f"大盘复盘任务失败: {e}")

@router.post("/analyze")
async def analyze_market(background_tasks: BackgroundTasks):
    """触发大盘复盘分析任务"""
    background_tasks.add_task(analyze_market_task)
    return {"message": "已触发大盘复盘分析任务"}