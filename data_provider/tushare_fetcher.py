# -*- coding: utf-8 -*-
"""
===================================
TushareFetcher - 备用数据源 1 (Priority 2)
===================================

数据来源：Tushare Pro API（挖地兔）
特点：需要 Token、有请求配额限制
优点：数据质量高、接口稳定

流控策略：
1. 实现"每分钟调用计数器"
2. 超过免费配额（80次/分）时，强制休眠到下一分钟
3. 使用 tenacity 实现指数退避重试
"""

import logging
import time
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .base import BaseFetcher, DataFetchError, RateLimitError, STANDARD_COLUMNS
from src.config import get_config
from .realtime_types import ChipDistribution, safe_float  # 导入ChipDistribution和安全转换函数

logger = logging.getLogger(__name__)


class TushareFetcher(BaseFetcher):
    """
    Tushare Pro 数据源实现
    
    优先级：2
    数据来源：Tushare Pro API
    
    关键策略：
    - 每分钟调用计数器，防止超出配额
    - 超过 80 次/分钟时强制等待
    - 失败后指数退避重试
    
    配额说明（Tushare 免费用户）：
    - 每分钟最多 80 次请求
    - 每天最多 500 次请求
    """
    
    name = "TushareFetcher"
    priority = 2  # 默认优先级，会在 __init__ 中根据配置动态调整

    def __init__(self, rate_limit_per_minute: int = 80):
        """
        初始化 TushareFetcher

        Args:
            rate_limit_per_minute: 每分钟最大请求数（默认80，Tushare免费配额）
        """
        self.rate_limit_per_minute = rate_limit_per_minute
        self._call_count = 0  # 当前分钟内的调用次数
        self._minute_start: Optional[float] = None  # 当前计数周期开始时间
        self._api: Optional[object] = None  # Tushare API 实例

        # 尝试初始化 API
        self._init_api()

        # 根据 API 初始化结果动态调整优先级
        self.priority = self._determine_priority()
    
    def _init_api(self) -> None:
        """
        初始化 Tushare API
        
        如果 Token 未配置，此数据源将不可用
        """
        config = get_config()
        
        if not config.tushare_token:
            logger.warning("Tushare Token 未配置，此数据源不可用")
            return
        
        try:
            import tushare as ts
            
            # 设置 Token
            ts.set_token(config.tushare_token)
            
            # 获取 API 实例
            self._api = ts.pro_api()
            
            logger.info("Tushare API 初始化成功")
            
        except Exception as e:
            logger.error(f"Tushare API 初始化失败: {e}")
            self._api = None

    def _determine_priority(self) -> int:
        """
        根据 Token 配置和 API 初始化状态确定优先级

        策略：
        - Token 配置且 API 初始化成功：优先级 0（最高）
        - 其他情况：优先级 2（默认）

        Returns:
            优先级数字（0=最高，数字越大优先级越低）
        """
        config = get_config()

        if config.tushare_token and self._api is not None:
            # Token 配置且 API 初始化成功，提升为最高优先级
            logger.info("✅ 检测到 TUSHARE_TOKEN 且 API 初始化成功，Tushare 数据源优先级提升为最高 (Priority 0)")
            return 0

        # Token 未配置或 API 初始化失败，保持默认优先级
        return 2

    def is_available(self) -> bool:
        """
        检查数据源是否可用

        Returns:
            True 表示可用，False 表示不可用
        """
        return self._api is not None

    def _check_rate_limit(self) -> None:
        """
        检查并执行速率限制
        
        流控策略：
        1. 检查是否进入新的一分钟
        2. 如果是，重置计数器
        3. 如果当前分钟调用次数超过限制，强制休眠
        """
        current_time = time.time()
        
        # 检查是否需要重置计数器（新的一分钟）
        if self._minute_start is None:
            self._minute_start = current_time
            self._call_count = 0
        elif current_time - self._minute_start >= 60:
            # 已经过了一分钟，重置计数器
            self._minute_start = current_time
            self._call_count = 0
            logger.debug("速率限制计数器已重置")
        
        # 检查是否超过配额
        if self._call_count >= self.rate_limit_per_minute:
            # 计算需要等待的时间（到下一分钟）
            elapsed = current_time - self._minute_start
            sleep_time = max(0, 60 - elapsed) + 1  # +1 秒缓冲
            
            logger.warning(
                f"Tushare 达到速率限制 ({self._call_count}/{self.rate_limit_per_minute} 次/分钟)，"
                f"等待 {sleep_time:.1f} 秒..."
            )
            
            time.sleep(sleep_time)
            
            # 重置计数器
            self._minute_start = time.time()
            self._call_count = 0
        
        # 增加调用计数
        self._call_count += 1
        logger.debug(f"Tushare 当前分钟调用次数: {self._call_count}/{self.rate_limit_per_minute}")
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """
        转换股票代码为 Tushare 格式
        
        Tushare 要求的格式：
        - 沪市：600519.SH
        - 深市：000001.SZ
        
        Args:
            stock_code: 原始代码，如 '600519', '000001'
            
        Returns:
            Tushare 格式代码，如 '600519.SH', '000001.SZ'
        """
        code = stock_code.strip()
        
        # 已经包含后缀的情况
        if '.' in code:
            return code.upper()
        
        # 根据代码前缀判断市场
        # 沪市：600xxx, 601xxx, 603xxx, 688xxx (科创板)
        # 深市：000xxx, 002xxx, 300xxx (创业板)
        if code.startswith(('600', '601', '603', '688')):
            return f"{code}.SH"
        elif code.startswith(('000', '002', '300')):
            return f"{code}.SZ"
        else:
            # 默认尝试深市
            logger.warning(f"无法确定股票 {code} 的市场，默认使用深市")
            return f"{code}.SZ"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def get_chip_distribution(self, stock_code: str, trade_date: str = None, start_date: str = None, end_date: str = None) -> Optional[ChipDistribution]:
        """
        获取股票筹码分布数据（使用cyq_perf接口）
        
        Args:
            stock_code: 股票代码，如 '600519'
            trade_date: 指定交易日期（YYYY-MM-DD），优先级高于start_date和end_date
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            
        Returns:
            ChipDistribution 对象，包含筹码分布相关信息，获取失败返回 None
        """
        if self._api is None:
            raise DataFetchError("Tushare API 未初始化，请检查 Token 配置")

        # 速率限制检查
        self._check_rate_limit()

        # 转换代码格式
        ts_code = self._convert_stock_code(stock_code)

        # 准备参数
        params = {'ts_code': ts_code}

        if trade_date:
            # 如果指定具体交易日，则使用该日期
            params['trade_date'] = trade_date.replace('-', '')
        else:
            # 否则使用开始和结束日期范围
            if start_date:
                params['start_date'] = start_date.replace('-', '')
            if end_date:
                params['end_date'] = end_date.replace('-', '')

        logger.debug(f"调用 Tushare cyq_perf({params})")

        try:
            # 调用 cyq_perf 接口获取筹码分布数据
            df = self._api.cyq_perf(**params)

            if df is None or df.empty:
                logger.warning(f"未获取到 {stock_code} 在指定日期的筹码分布数据")
                return None

            # 取最新一天的数据
            latest = df.iloc[-1]
            
            # 使用计算函数从Tushare数据转换为AKShare格式
            calculated_data = self._calculate_akshare_fields_from_tushare(latest)
            
            # 创建ChipDistribution对象
            chip = ChipDistribution(
                code=stock_code,
                date=latest.get('trade_date', ''),
                source="tushare",
                profit_ratio=calculated_data['profit_ratio'],
                avg_cost=calculated_data['avg_cost'],
                cost_90_low=calculated_data['cost_90_low'],
                cost_90_high=calculated_data['cost_90_high'],
                concentration_90=calculated_data['concentration_90'],
                cost_70_low=calculated_data['cost_70_low'],
                cost_70_high=calculated_data['cost_70_high'],
                concentration_70=calculated_data['concentration_70'],
            )
            
            logger.info(f"[筹码分布-Tushare] {stock_code} 日期={chip.date}: "
                       f"获利比例={chip.profit_ratio:.1%}, 平均成本={chip.avg_cost}, "
                       f"90%集中度={chip.concentration_90:.2f}%, 70%集中度={chip.concentration_70:.2f}%")
            return chip

        except Exception as e:
            error_msg = str(e).lower()

            # 检测配额超限
            if any(keyword in error_msg for keyword in ['quota', '配额', 'limit', '权限']):
                logger.warning(f"Tushare 配额可能超限: {e}")
                raise RateLimitError(f"Tushare 配额超限: {e}") from e

            logger.error(f"Tushare 获取筹码分布数据失败: {e}")
            return None

    def _calculate_akshare_fields_from_tushare(self, row):
        """
        根据Tushare的cyq_perf数据，计算AKShare的区间和集中度
        """
        # 获取Tushare提供的分位成本数据
        cost_5 = safe_float(row.get('cost_5pct'))
        cost_15 = safe_float(row.get('cost_15pct'))
        cost_85 = safe_float(row.get('cost_85pct'))
        cost_95 = safe_float(row.get('cost_95pct'))
        
        # 计算90%成本区间和集中度 (5% ~ 95%)
        high_90 = cost_95
        low_90 = cost_5
        concentration_90 = (high_90 - low_90) / (high_90 + low_90) * 100 if (high_90 + low_90) > 0 else 0
        
        # 计算70%成本区间和集中度 (15% ~ 85%)
        high_70 = cost_85
        low_70 = cost_15
        concentration_70 = (high_70 - low_70) / (high_70 + low_70) * 100 if (high_70 + low_70) > 0 else 0
        
        return {
            'profit_ratio': safe_float(row.get('winner_rate')) / 100,  # 转换为0-1之间的比例
            'avg_cost': safe_float(row.get('weight_avg')),  # 加权平均成本
            'cost_90_low': low_90,
            'cost_90_high': high_90,
            'concentration_90': round(concentration_90, 2),
            'cost_70_low': low_70,
            'cost_70_high': high_70,
            'concentration_70': round(concentration_70, 2),
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从 Tushare 获取原始数据
        
        使用 daily() 接口获取日线数据
        
        流程：
        1. 检查 API 是否可用
        2. 执行速率限制检查
        3. 转换股票代码格式
        4. 调用 API 获取数据
        """
        if self._api is None:
            raise DataFetchError("Tushare API 未初始化，请检查 Token 配置")
        
        # 速率限制检查
        self._check_rate_limit()
        
        # 转换代码格式
        ts_code = self._convert_stock_code(stock_code)
        
        # 转换日期格式（Tushare 要求 YYYYMMDD）
        ts_start = start_date.replace('-', '')
        ts_end = end_date.replace('-', '')
        
        logger.debug(f"调用 Tushare daily({ts_code}, {ts_start}, {ts_end})")
        
        try:
            # 调用 daily 接口获取日线数据
            df = self._api.daily(
                ts_code=ts_code,
                start_date=ts_start,
                end_date=ts_end,
            )
            
            return df
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 检测配额超限
            if any(keyword in error_msg for keyword in ['quota', '配额', 'limit', '权限']):
                logger.warning(f"Tushare 配额可能超限: {e}")
                raise RateLimitError(f"Tushare 配额超限: {e}") from e
            
            raise DataFetchError(f"Tushare 获取数据失败: {e}") from e
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        标准化 Tushare 数据
        
        Tushare daily 返回的列名：
        ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
        
        需要映射到标准列名：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()
        
        # 列名映射
        column_mapping = {
            'trade_date': 'date',
            'vol': 'volume',
            # open, high, low, close, amount, pct_chg 列名相同
        }
        
        df = df.rename(columns=column_mapping)
        
        # 转换日期格式（YYYYMMDD -> YYYY-MM-DD）
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        # 成交量单位转换（Tushare 的 vol 单位是手，需要转换为股）
        if 'volume' in df.columns:
            df['volume'] = df['volume'] * 100
        
        # 成交额单位转换（Tushare 的 amount 单位是千元，转换为元）
        if 'amount' in df.columns:
            df['amount'] = df['amount'] * 1000
        
        # 添加股票代码列
        df['code'] = stock_code
        
        # 只保留需要的列
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]
        
        return df

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        获取股票名称
        
        使用 Tushare 的 stock_basic 接口获取股票基本信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票名称，失败返回 None
        """
        if self._api is None:
            logger.warning("Tushare API 未初始化，无法获取股票名称")
            return None
        
        # 检查缓存
        if hasattr(self, '_stock_name_cache') and stock_code in self._stock_name_cache:
            return self._stock_name_cache[stock_code]
        
        # 初始化缓存
        if not hasattr(self, '_stock_name_cache'):
            self._stock_name_cache = {}
        
        try:
            # 速率限制检查
            self._check_rate_limit()
            
            # 转换代码格式
            ts_code = self._convert_stock_code(stock_code)
            
            # 调用 stock_basic 接口
            df = self._api.stock_basic(
                ts_code=ts_code,
                fields='ts_code,name'
            )
            
            if df is not None and not df.empty:
                name = df.iloc[0]['name']
                self._stock_name_cache[stock_code] = name
                logger.debug(f"Tushare 获取股票名称成功: {stock_code} -> {name}")
                return name
            
        except Exception as e:
            logger.warning(f"Tushare 获取股票名称失败 {stock_code}: {e}")
        
        return None
    
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取股票列表
        
        使用 Tushare 的 stock_basic 接口获取全部股票列表
        
        Returns:
            包含 code, name 列的 DataFrame，失败返回 None
        """
        if self._api is None:
            logger.warning("Tushare API 未初始化，无法获取股票列表")
            return None
        
        try:
            # 速率限制检查
            self._check_rate_limit()
            
            # 调用 stock_basic 接口获取所有股票
            df = self._api.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,name,industry,area,market'
            )
            
            if df is not None and not df.empty:
                # 转换 ts_code 为标准代码格式
                df['code'] = df['ts_code'].apply(lambda x: x.split('.')[0])
                
                # 更新缓存
                if not hasattr(self, '_stock_name_cache'):
                    self._stock_name_cache = {}
                for _, row in df.iterrows():
                    self._stock_name_cache[row['code']] = row['name']
                
                logger.info(f"Tushare 获取股票列表成功: {len(df)} 条")
                return df[['code', 'name', 'industry', 'area', 'market']]
            
        except Exception as e:
            logger.warning(f"Tushare 获取股票列表失败: {e}")
        
        return None
    
    def get_realtime_quote(self, stock_code: str) -> Optional[dict]:
        """
        获取实时行情（Tushare Pro 需要较高积分才能使用实时接口）
        
        注意：Tushare 实时行情接口需要较高积分（>=2000），
        普通用户建议使用其他数据源的实时行情。
        
        Args:
            stock_code: 股票代码
            
        Returns:
            实时行情数据字典，失败返回 None
        """
        # Tushare 实时行情需要高积分，普通用户无法使用
        # 这里仅作为接口预留，实际应使用 efinance 或 akshare 的实时数据
        logger.debug(f"Tushare 实时行情接口需要高积分，建议使用其他数据源: {stock_code}")
        return None


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = TushareFetcher()
    
    try:
<<<<<<< HEAD
        df = fetcher.get_daily_data('601179')  # 茅台
=======
        # 测试历史数据
        df = fetcher.get_daily_data('600519')  # 茅台
>>>>>>> ea3ce3c8034cb553ed2f2ac97fada6ce658dc6c4
        print(f"获取成功，共 {len(df)} 条数据")
        print(df.tail())
        
        # 测试股票名称
        name = fetcher.get_stock_name('600519')
        print(f"股票名称: {name}")
        
    except Exception as e:
        print(f"获取失败: {e}")