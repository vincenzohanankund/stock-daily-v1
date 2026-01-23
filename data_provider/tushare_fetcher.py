# -*- coding: utf-8 -*-
"""
===================================
TushareFetcher - 備用數據源 1 (Priority 2)
===================================

數據來源：Tushare Pro API（挖地兔）
特點：需要 Token、有請求配額限制
優點：數據質量高、接口穩定

流控策略：
1. 實現"每分鐘調用計數器"
2. 超過免費配額（80次/分）時，強制休眠到下一分鐘
3. 使用 tenacity 實現指數退避重試
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
from config import get_config

logger = logging.getLogger(__name__)


class TushareFetcher(BaseFetcher):
    """
    Tushare Pro 數據源實現
    
    優先級：2
    數據來源：Tushare Pro API
    
    關鍵策略：
    - 每分鐘調用計數器，防止超出配額
    - 超過 80 次/分鐘時強制等待
    - 失敗後指數退避重試
    
    配額說明（Tushare 免費用戶）：
    - 每分鐘最多 80 次請求
    - 每天最多 500 次請求
    """
    
    name = "TushareFetcher"
    priority = 2  # 默認優先級，會在 __init__ 中根據配置動態調整

    def __init__(self, rate_limit_per_minute: int = 80):
        """
        初始化 TushareFetcher

        Args:
            rate_limit_per_minute: 每分鐘最大請求數（默認80，Tushare免費配額）
        """
        self.rate_limit_per_minute = rate_limit_per_minute
        self._call_count = 0  # 當前分鐘內的調用次數
        self._minute_start: Optional[float] = None  # 當前計數週期開始時間
        self._api: Optional[object] = None  # Tushare API 實例

        # 嘗試初始化 API
        self._init_api()

        # 根據 API 初始化結果動態調整優先級
        self.priority = self._determine_priority()
    
    def _init_api(self) -> None:
        """
        初始化 Tushare API
        
        如果 Token 未配置，此數據源將不可用
        """
        config = get_config()
        
        if not config.tushare_token:
            logger.warning("Tushare Token 未配置，此數據源不可用")
            return
        
        try:
            import tushare as ts
            
            # 設置 Token
            ts.set_token(config.tushare_token)
            
            # 獲取 API 實例
            self._api = ts.pro_api()
            
            logger.info("Tushare API 初始化成功")
            
        except Exception as e:
            logger.error(f"Tushare API 初始化失敗: {e}")
            self._api = None

    def _determine_priority(self) -> int:
        """
        根據 Token 配置和 API 初始化狀態確定優先級

        策略：
        - Token 配置且 API 初始化成功：優先級 0（最高）
        - 其他情況：優先級 2（默認）

        Returns:
            優先級數字（0=最高，數字越大優先級越低）
        """
        config = get_config()

        if config.tushare_token and self._api is not None:
            # Token 配置且 API 初始化成功，提升為最高優先級
            logger.info("✅ 檢測到 TUSHARE_TOKEN 且 API 初始化成功，Tushare 數據源優先級提升為最高 (Priority 0)")
            return 0

        # Token 未配置或 API 初始化失敗，保持默認優先級
        return 2

    def is_available(self) -> bool:
        """
        檢查數據源是否可用

        Returns:
            True 表示可用，False 表示不可用
        """
        return self._api is not None

    def _check_rate_limit(self) -> None:
        """
        檢查並執行速率限制
        
        流控策略：
        1. 檢查是否進入新的一分鐘
        2. 如果是，重置計數器
        3. 如果當前分鐘調用次數超過限制，強制休眠
        """
        current_time = time.time()
        
        # 檢查是否需要重置計數器（新的一分鐘）
        if self._minute_start is None:
            self._minute_start = current_time
            self._call_count = 0
        elif current_time - self._minute_start >= 60:
            # 已經過了一分鐘，重置計數器
            self._minute_start = current_time
            self._call_count = 0
            logger.debug("速率限制計數器已重置")
        
        # 檢查是否超過配額
        if self._call_count >= self.rate_limit_per_minute:
            # 計算需要等待的時間（到下一分鐘）
            elapsed = current_time - self._minute_start
            sleep_time = max(0, 60 - elapsed) + 1  # +1 秒緩衝
            
            logger.warning(
                f"Tushare 達到速率限制 ({self._call_count}/{self.rate_limit_per_minute} 次/分鐘)，"
                f"等待 {sleep_time:.1f} 秒..."
            )
            
            time.sleep(sleep_time)
            
            # 重置計數器
            self._minute_start = time.time()
            self._call_count = 0
        
        # 增加調用計數
        self._call_count += 1
        logger.debug(f"Tushare 當前分鐘調用次數: {self._call_count}/{self.rate_limit_per_minute}")
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """
        轉換股票代碼為 Tushare 格式
        
        Tushare 要求的格式：
        - 滬市：600519.SH
        - 深市：000001.SZ
        
        Args:
            stock_code: 原始代碼，如 '600519', '000001'
            
        Returns:
            Tushare 格式代碼，如 '600519.SH', '000001.SZ'
        """
        code = stock_code.strip()
        
        # 已經包含後綴的情況
        if '.' in code:
            return code.upper()
        
        # 根據代碼前綴判斷市場
        # 滬市：600xxx, 601xxx, 603xxx, 688xxx (科創板)
        # 深市：000xxx, 002xxx, 300xxx (創業板)
        if code.startswith(('600', '601', '603', '688')):
            return f"{code}.SH"
        elif code.startswith(('000', '002', '300')):
            return f"{code}.SZ"
        else:
            # 默認嘗試深市
            logger.warning(f"無法確定股票 {code} 的市場，默認使用深市")
            return f"{code}.SZ"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        從 Tushare 獲取原始數據
        
        使用 daily() 接口獲取日線數據
        
        流程：
        1. 檢查 API 是否可用
        2. 執行速率限制檢查
        3. 轉換股票代碼格式
        4. 調用 API 獲取數據
        """
        if self._api is None:
            raise DataFetchError("Tushare API 未初始化，請檢查 Token 配置")
        
        # 速率限制檢查
        self._check_rate_limit()
        
        # 轉換代碼格式
        ts_code = self._convert_stock_code(stock_code)
        
        # 轉換日期格式（Tushare 要求 YYYYMMDD）
        ts_start = start_date.replace('-', '')
        ts_end = end_date.replace('-', '')
        
        logger.debug(f"調用 Tushare daily({ts_code}, {ts_start}, {ts_end})")
        
        try:
            # 調用 daily 接口獲取日線數據
            df = self._api.daily(
                ts_code=ts_code,
                start_date=ts_start,
                end_date=ts_end,
            )
            
            return df
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 檢測配額超限
            if any(keyword in error_msg for keyword in ['quota', '配額', 'limit', '權限']):
                logger.warning(f"Tushare 配額可能超限: {e}")
                raise RateLimitError(f"Tushare 配額超限: {e}") from e
            
            raise DataFetchError(f"Tushare 獲取數據失敗: {e}") from e
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        標準化 Tushare 數據
        
        Tushare daily 返回的列名：
        ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
        
        需要映射到標準列名：
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
        
        # 轉換日期格式（YYYYMMDD -> YYYY-MM-DD）
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        # 成交量單位轉換（Tushare 的 vol 單位是手，需要轉換為股）
        if 'volume' in df.columns:
            df['volume'] = df['volume'] * 100
        
        # 成交額單位轉換（Tushare 的 amount 單位是千元，轉換為元）
        if 'amount' in df.columns:
            df['amount'] = df['amount'] * 1000
        
        # 添加股票代碼列
        df['code'] = stock_code
        
        # 只保留需要的列
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]
        
        return df


if __name__ == "__main__":
    # 測試代碼
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = TushareFetcher()
    
    try:
        df = fetcher.get_daily_data('600519')  # 茅臺
        print(f"獲取成功，共 {len(df)} 條數據")
        print(df.tail())
    except Exception as e:
        print(f"獲取失敗: {e}")
