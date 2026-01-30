# -*- coding: utf-8 -*-
"""
===================================
定时调度模块
===================================

职责：
1. 支持每日定时执行股票分析
2. 支持定时执行大盘复盘
3. 优雅处理信号，确保可靠退出

依赖：
- schedule: 轻量级定时任务库
"""

import logging
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    优雅退出处理器
    
    捕获 SIGTERM/SIGINT 信号，确保任务完成后再退出
    """
    
    def __init__(self):
        self.shutdown_requested = False
        self._lock = threading.Lock()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        with self._lock:
            if not self.shutdown_requested:
                logger.info(f"收到退出信号 ({signum})，等待当前任务完成...")
                self.shutdown_requested = True
    
    @property
    def should_shutdown(self) -> bool:
        """检查是否应该退出"""
        with self._lock:
            return self.shutdown_requested


class Scheduler:
    """
    定时任务调度器
    
    基于 schedule 库实现，支持：
    - 每日定时执行
    - 启动时立即执行
    - 优雅退出
    """
    
    def __init__(self, schedule_time: str = "18:00"):
        """
        初始化调度器
        
        Args:
            schedule_time: 每日执行时间，格式 "HH:MM"
        """
        try:
            import schedule
            self.schedule = schedule
        except ImportError:
            logger.error("schedule 库未安装，请执行: pip install schedule")
            raise ImportError("请安装 schedule 库: pip install schedule")
        
        self.schedule_time = schedule_time
        self.shutdown_handler = GracefulShutdown()
        self._task_callback: Optional[Callable] = None
        self._running = False
        
    def set_daily_task(self, task: Callable, run_immediately: bool = True):
        """
        设置每日定时任务

        Args:
            task: 要执行的任务函数（无参数）
            run_immediately: 是否在设置后立即执行一次
        """
        self._task_callback = task

        # 设置每日定时任务
        self.schedule.every().day.at(self.schedule_time).do(self._safe_run_task)
        logger.info(f"已设置每日定时任务，执行时间: {self.schedule_time}")

        if run_immediately:
            logger.info("立即执行一次任务...")
            self._safe_run_task()

    def set_stock_name_refresh_task(self, refresh_time: str = "09:00"):
        """
        设置股票名称刷新任务（每日开盘前刷新，检测新股上市）

        Args:
            refresh_time: 刷新时间，默认每日 09:00（开盘前）
        """
        self.schedule.every().day.at(refresh_time).do(self._refresh_stock_names)
        logger.info(f"已设置股票名称刷新任务，执行时间: {refresh_time}")

    def _refresh_stock_names(self):
        """
        刷新股票名称缓存并检测新股上市

        执行逻辑：
        1. 调用 stock_name_service 刷新所有股票列表
        2. 检测新股上市并记录日志
        """
        try:
            logger.info("[定时任务] 开始刷新股票名称缓存...")

            from src.stock_name_service import get_stock_name_service
            service = get_stock_name_service()

            # 检测新股并刷新
            new_stocks = service.check_new_stocks()

            # 统计
            total_new = sum(len(v) for v in new_stocks.values())
            if total_new > 0:
                logger.info(f"[定时任务] 检测到 {total_new} 只新股上市")

                # 记录新股详情
                for market, stocks in new_stocks.items():
                    if stocks:
                        market_name = {'a_stocks': 'A股', 'hk_stocks': '港股', 'us_stocks': '美股'}.get(market, market)
                        logger.info(f"[新股上市] {market_name}:")
                        for code, name in stocks[:5]:
                            logger.info(f"  - {code}: {name}")
                        if len(stocks) > 5:
                            logger.info(f"  ... 还有 {len(stocks) - 5} 只")
            else:
                logger.info("[定时任务] 股票名称缓存刷新完成，未检测到新股")

            # 输出统计
            stats = service.get_statistics()
            logger.info(f"[定时任务] 当前缓存: A股 {stats['a_stocks_count']}, "
                       f"港股 {stats['hk_stocks_count']}, 美股 {stats['us_stocks_count']}")

        except ImportError as e:
            logger.warning(f"[定时任务] stock_name_service 模块未安装: {e}")
        except Exception as e:
            logger.exception(f"[定时任务] 刷新股票名称失败: {e}")
    
    def _safe_run_task(self):
        """安全执行任务（带异常捕获）"""
        if self._task_callback is None:
            return
        
        try:
            logger.info("=" * 50)
            logger.info(f"定时任务开始执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 50)
            
            self._task_callback()
            
            logger.info(f"定时任务执行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            logger.exception(f"定时任务执行失败: {e}")
    
    def run(self):
        """
        运行调度器主循环
        
        阻塞运行，直到收到退出信号
        """
        self._running = True
        logger.info("调度器开始运行...")
        logger.info(f"下次执行时间: {self._get_next_run_time()}")
        
        while self._running and not self.shutdown_handler.should_shutdown:
            self.schedule.run_pending()
            time.sleep(30)  # 每30秒检查一次
            
            # 每小时打印一次心跳
            if datetime.now().minute == 0 and datetime.now().second < 30:
                logger.info(f"调度器运行中... 下次执行: {self._get_next_run_time()}")
        
        logger.info("调度器已停止")
    
    def _get_next_run_time(self) -> str:
        """获取下次执行时间"""
        jobs = self.schedule.get_jobs()
        if jobs:
            next_run = min(job.next_run for job in jobs)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        return "未设置"
    
    def stop(self):
        """停止调度器"""
        self._running = False


def run_with_schedule(
    task: Callable,
    schedule_time: str = "18:00",
    run_immediately: bool = True,
    enable_stock_name_refresh: bool = True,
    stock_name_refresh_time: str = "09:00"
):
    """
    便捷函数：使用定时调度运行任务

    Args:
        task: 要执行的任务函数
        schedule_time: 每日执行时间
        run_immediately: 是否立即执行一次
        enable_stock_name_refresh: 是否启用股票名称刷新任务（检测新股上市）
        stock_name_refresh_time: 股票名称刷新时间
    """
    scheduler = Scheduler(schedule_time=schedule_time)
    scheduler.set_daily_task(task, run_immediately=run_immediately)

    # 启用股票名称刷新任务（每日检测新股上市）
    if enable_stock_name_refresh:
        scheduler.set_stock_name_refresh_task(refresh_time=stock_name_refresh_time)

    scheduler.run()


if __name__ == "__main__":
    # 测试定时调度
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )
    
    def test_task():
        print(f"任务执行中... {datetime.now()}")
        time.sleep(2)
        print("任务完成!")
    
    print("启动测试调度器（按 Ctrl+C 退出）")
    run_with_schedule(test_task, schedule_time="23:59", run_immediately=True)
