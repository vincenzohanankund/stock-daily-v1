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
import time
from datetime import datetime
from typing import Callable, Dict, List, Union
import threading

import schedule

logger = logging.getLogger(__name__)

# 只使用数字映射（1=周一, 7=周日）
WEEKDAY_MAP = {
    '1': 'monday',
    '2': 'tuesday',
    '3': 'wednesday',
    '4': 'thursday',
    '5': 'friday',
    '6': 'saturday',
    '7': 'sunday',
}

# 用于按序获取短名顺序索引（数字字符串）
WEEK_ORDER = ['1', '2', '3', '4', '5', '6', '7']


class Scheduler:
    """
    简单的定时调度器，已移除英文短名支持（仅接受数字 1-7）。
    支持：
      - schedule_time 传入单个时间字符串 (e.g. "18:00") 或逗号分隔多时间 ("09:30,13:30") -> 每天这些时间触发
      - 或传入更复杂的字符串，支持按星期数字配置，例如:
            "1-5@09:30,13:30;6@10:00"
      - 或直接传入 dict: {"1": ["09:30"], "7": ["11:00"], "every": ["18:00"]}
    备注：数字 1-7 对应 周一-周日（1=周一,7=周日）。
    """

    def __init__(self, schedule_time: Union[str, List[str], Dict[str, List[str]]] = "18:00"):
        self._task_callback: Callable = None
        self._running = False
        # 简单占位，用于外部可能设置的关闭标志
        self.shutdown_handler = type("H", (), {"should_shutdown": False})()
        self._lock = threading.Lock()  # 用于防止任务重入

        # 统一解析成 weekday -> List[time_str] 结构
        self.schedule_map = self._parse_schedule_time(schedule_time)

    def _parse_schedule_time(self, spec: Union[str, List[str], Dict[str, List[str]]]) -> Dict[str, List[str]]:
        """
        规范化 schedule_time 为字典：
          keys: 'every' (表示每天) 或 weekday 名称 'monday'...'sunday'
          values: 时间字符串列表 ["09:30", "13:30"]
        支持输入格式：
          - "18:00"
          - "09:30,13:30"
          - "1-5@09:30,13:30;6@10:00"
          - ["09:30", "13:30"]
          - {"1": ["09:30"], "7": ["11:00"]}
        重要：不再支持英文短名如 mon/tue。
        """
        result: Dict[str, List[str]] = {}

        if isinstance(spec, dict):
            # 直接映射：键必须是 'every' 或 '1'..'7'
            for k, v in spec.items():
                key = str(k).strip().lower()
                if key == 'every':
                    wk = 'every'
                elif key in WEEKDAY_MAP:
                    wk = WEEKDAY_MAP[key]
                elif key in WEEKDAY_MAP.values():
                    wk = key
                else:
                    raise ValueError(f"未知的 weekday key: {k}，请使用数字 1-7 或 'every'")
                result.setdefault(wk, []).extend([t.strip() for t in v])
            return {k: list(dict.fromkeys(v)) for k, v in result.items()}

        if isinstance(spec, list):
            times = [t.strip() for t in spec]
            return {"every": times}

        if isinstance(spec, str):
            s = spec.strip()
            # 如果只含时间或逗号分隔时间 -> 每天
            if '@' not in s and ';' not in s and all(self._looks_like_time(t) for t in s.split(',')):
                times = [t.strip() for t in s.split(',') if t.strip()]
                return {"every": times}

            # 否则支持分号分隔多个规则： rule1;rule2;...
            # 每个规则形如: weekday_spec@time1,time2, weekday_spec 只接受数字/范围/逗号，例如： "1-5" 或 "1,3,5"
            entries = [e.strip() for e in s.split(';') if e.strip()]
            for entry in entries:
                if '@' in entry:
                    day_part, times_part = entry.split('@', 1)
                    day_part = day_part.strip()
                    times = [t.strip() for t in times_part.split(',') if t.strip()]
                    # day_part 可能是范围 1-5 或 列表 1,3,5
                    day_tokens = [d.strip() for d in day_part.split(',') if d.strip()]
                    weekdays: List[str] = []
                    for tok in day_tokens:
                        if '-' in tok:
                            a_raw, b_raw = [x.strip() for x in tok.split('-', 1)]
                            if not (a_raw.isdigit() and b_raw.isdigit()):
                                raise ValueError(f"非法星期范围: {tok}。范围只能使用数字 1-7")
                            a_short = a_raw
                            b_short = b_raw
                            try:
                                ia = WEEK_ORDER.index(a_short)
                                ib = WEEK_ORDER.index(b_short)
                            except ValueError:
                                raise ValueError(f"非法星期数字: {tok}，请使用 1-7")
                            if ia <= ib:
                                rng = WEEK_ORDER[ia:ib+1]
                            else:
                                # 跨周，如 5-2 表示 周五->周二
                                rng = WEEK_ORDER[ia:] + WEEK_ORDER[:ib+1]
                            weekdays.extend(rng)
                        else:
                            # 单个 token，必须是数字 1-7
                            if not tok.isdigit() or tok not in WEEKDAY_MAP:
                                raise ValueError(f"未知的星期 token: {tok}，请使用数字 1-7")
                            weekdays.append(tok)

                    # 将数字短名转换为 weekday full-name 并加入 result
                    for num_short in weekdays:
                        wk_name = WEEKDAY_MAP.get(num_short)
                        if not wk_name:
                            raise ValueError(f"无法映射星期: {num_short}")
                        result.setdefault(wk_name, []).extend(times)
                else:
                    # 没有 '@' 的情况下，如果是单纯时间则前面已处理，否则视作每天的时间（兼容性）
                    if all(self._looks_like_time(t) for t in entry.split(',')):
                        times = [t.strip() for t in entry.split(',') if t.strip()]
                        result.setdefault("every", []).extend(times)
                    else:
                        raise ValueError(f"无法解析 schedule 规则: {entry}")

            # 去重时间
            for k in list(result.keys()):
                uniq = []
                for t in result[k]:
                    if t not in uniq:
                        uniq.append(t)
                result[k] = uniq

            return result

        raise ValueError("Unsupported schedule_time type")

    def _looks_like_time(self, s: str) -> bool:
        s = s.strip()
        if len(s) != 5 or s[2] != ':':
            return False
        hh, mm = s.split(':')
        try:
            h = int(hh); m = int(mm)
            return 0 <= h < 24 and 0 <= m < 60
        except:
            return False

    def set_daily_task(self, task: Callable, run_immediately: bool = True):
        """
        将任务注册到 schedule 库。
        支持每天多时间点，以及按星期的多时间点（仅数字 1-7 表示法）。
        """
        self._task_callback = task

        # 每天的时间
        if 'every' in self.schedule_map:
            for t in self.schedule_map['every']:
                try:
                    schedule.every().day.at(t).do(self._safe_run_task)
                    logger.info(f"已设置每日定时任务，执行时间: {t}")
                except Exception as exc:
                    logger.error(f"设置每日定时任务 {t} 失败: {exc}")

        # 按星期设置
        for wk_name, times in self.schedule_map.items():
            if wk_name == 'every':
                continue
            for t in times:
                try:
                    # schedule.every().monday.at("09:30")...
                    job_creator = getattr(schedule.every(), wk_name)
                    job_creator.at(t).do(self._safe_run_task)
                    logger.info(f"已设置 {wk_name} 定时任务，执行时间: {t}")
                except Exception as exc:
                    logger.error(f"设置 {wk_name} 定时任务 {t} 失败: {exc}")

        if run_immediately:
            logger.info("立即执行一次任务...")
            self._safe_run_task()

    def _safe_run_task(self):
        """安全执行任务（带异常捕获和互斥，避免重入）"""
        if self._task_callback is None:
            return

        locked = self._lock.acquire(blocking=False)
        if not locked:
            logger.warning("上一次定时任务仍在运行，跳过本次触发以避免重入。")
            return

        try:
            logger.info("=" * 50)
            logger.info(f"定时任务开始执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 50)

            try:
                self._task_callback()
            except Exception as e:
                logger.exception(f"定时任务执行失败: {e}")

            logger.info(f"定时任务执行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        finally:
            self._lock.release()

    def run(self):
        """
        运行调度器主循环（阻塞）
        """
        self._running = True
        logger.info("调度器开始运行...")
        logger.info(f"下次执行时间: {self._get_next_run_time()}")

        while self._running and not self.shutdown_handler.should_shutdown:
            schedule.run_pending()
            time.sleep(30)  # 每30秒检查一次

            # 每小时打印一次心跳
            if datetime.now().minute == 0 and datetime.now().second < 30:
                logger.info(f"调度器运行中... 下次执行: {self._get_next_run_time()}")

        logger.info("调度器已停止")

    def _get_next_run_time(self) -> str:
        """获取下次执行时间"""
        jobs = schedule.get_jobs()
        if jobs:
            next_run = min(job.next_run for job in jobs)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        return "未设置"

    def stop(self):
        """停止调度器"""
        self._running = False


def run_with_schedule(
    task: Callable,
    schedule_time: Union[str, List[str], Dict[str, List[str]]] = "18:00",
    run_immediately: bool = True
):
    """
    便捷函数：使用定时调度运行任务。
    schedule_time 支持字符串（含周规则、数字表示）、列表或字典（见 Scheduler 文档）。
    """
    scheduler = Scheduler(schedule_time=schedule_time)
    scheduler.set_daily_task(task, run_immediately=run_immediately)
    scheduler.run()


if __name__ == "__main__":
    # 测试用例
    logging.basicConfig(level=logging.INFO)
    def test_task():
        logger.info("Task running...")
        time.sleep(2)
        logger.info("Task finished.")
    # 示例：周一到周五 (1-5) 09:30 和 13:30，周末 (6-7) 10:00
    spec = "1-5@09:30,13:30;6-7@10:00"
    run_with_schedule(test_task, schedule_time=spec, run_immediately=True)
