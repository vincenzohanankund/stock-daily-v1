# -*- coding: utf-8 -*-
"""
===================================
數據源基類與管理器
===================================

設計模式：策略模式 (Strategy Pattern)
- BaseFetcher: 抽象基類，定義統一接口
- DataFetcherManager: 策略管理器，實現自動切換

防封禁策略：
1. 每個 Fetcher 內置流控邏輯
2. 失敗自動切換到下一個數據源
3. 指數退避重試機制
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Tuple

import pandas as pd
import numpy as np
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# 配置日誌
logger = logging.getLogger(__name__)


# === 標準化列名定義 ===
STANDARD_COLUMNS = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']


class DataFetchError(Exception):
    """數據獲取異常基類"""
    pass


class RateLimitError(DataFetchError):
    """API 速率限制異常"""
    pass


class DataSourceUnavailableError(DataFetchError):
    """數據源不可用異常"""
    pass


class BaseFetcher(ABC):
    """
    數據源抽象基類
    
    職責：
    1. 定義統一的數據獲取接口
    2. 提供數據標準化方法
    3. 實現通用的技術指標計算
    
    子類實現：
    - _fetch_raw_data(): 從具體數據源獲取原始數據
    - _normalize_data(): 將原始數據轉換為標準格式
    """
    
    name: str = "BaseFetcher"
    priority: int = 99  # 優先級數字越小越優先
    
    @abstractmethod
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        從數據源獲取原始數據（子類必須實現）
        
        Args:
            stock_code: 股票代碼，如 '600519', '000001'
            start_date: 開始日期，格式 'YYYY-MM-DD'
            end_date: 結束日期，格式 'YYYY-MM-DD'
            
        Returns:
            原始數據 DataFrame（列名因數據源而異）
        """
        pass
    
    @abstractmethod
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        標準化數據列名（子類必須實現）
        
        將不同數據源的列名統一為：
        ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
        """
        pass
    
    def get_daily_data(
        self, 
        stock_code: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30
    ) -> pd.DataFrame:
        """
        獲取日線數據（統一入口）
        
        流程：
        1. 計算日期範圍
        2. 調用子類獲取原始數據
        3. 標準化列名
        4. 計算技術指標
        
        Args:
            stock_code: 股票代碼
            start_date: 開始日期（可選）
            end_date: 結束日期（可選，默認今天）
            days: 獲取天數（當 start_date 未指定時使用）
            
        Returns:
            標準化的 DataFrame，包含技術指標
        """
        # 計算日期範圍
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if start_date is None:
            # 默認獲取最近 30 個交易日（按日曆日估算，多取一些）
            from datetime import timedelta
            start_dt = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days * 2)
            start_date = start_dt.strftime('%Y-%m-%d')
        
        logger.info(f"[{self.name}] 獲取 {stock_code} 數據: {start_date} ~ {end_date}")
        
        try:
            # Step 1: 獲取原始數據
            raw_df = self._fetch_raw_data(stock_code, start_date, end_date)
            
            if raw_df is None or raw_df.empty:
                raise DataFetchError(f"[{self.name}] 未獲取到 {stock_code} 的數據")
            
            # Step 2: 標準化列名
            df = self._normalize_data(raw_df, stock_code)
            
            # Step 3: 數據清洗
            df = self._clean_data(df)
            
            # Step 4: 計算技術指標
            df = self._calculate_indicators(df)
            
            logger.info(f"[{self.name}] {stock_code} 獲取成功，共 {len(df)} 條數據")
            return df
            
        except Exception as e:
            logger.error(f"[{self.name}] 獲取 {stock_code} 失敗: {str(e)}")
            raise DataFetchError(f"[{self.name}] {stock_code}: {str(e)}") from e
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        數據清洗
        
        處理：
        1. 確保日期列格式正確
        2. 數值類型轉換
        3. 去除空值行
        4. 按日期排序
        """
        df = df.copy()
        
        # 確保日期列為 datetime 類型
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        # 數值列類型轉換
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 去除關鍵列為空的行
        df = df.dropna(subset=['close', 'volume'])
        
        # 按日期升序排序
        df = df.sort_values('date', ascending=True).reset_index(drop=True)
        
        return df
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算技術指標
        
        計算指標：
        - MA5, MA10, MA20: 移動平均線
        - Volume_Ratio: 量比（今日成交量 / 5日平均成交量）
        """
        df = df.copy()
        
        # 移動平均線
        df['ma5'] = df['close'].rolling(window=5, min_periods=1).mean()
        df['ma10'] = df['close'].rolling(window=10, min_periods=1).mean()
        df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()
        
        # 量比：當日成交量 / 5日平均成交量
        avg_volume_5 = df['volume'].rolling(window=5, min_periods=1).mean()
        df['volume_ratio'] = df['volume'] / avg_volume_5.shift(1)
        df['volume_ratio'] = df['volume_ratio'].fillna(1.0)
        
        # 保留2位小數
        for col in ['ma5', 'ma10', 'ma20', 'volume_ratio']:
            if col in df.columns:
                df[col] = df[col].round(2)
        
        return df
    
    @staticmethod
    def random_sleep(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """
        智能隨機休眠（Jitter）
        
        防封禁策略：模擬人類行為的隨機延遲
        在請求之間加入不規則的等待時間
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        logger.debug(f"隨機休眠 {sleep_time:.2f} 秒...")
        time.sleep(sleep_time)


class DataFetcherManager:
    """
    數據源策略管理器
    
    職責：
    1. 管理多個數據源（按優先級排序）
    2. 自動故障切換（Failover）
    3. 提供統一的數據獲取接口
    
    切換策略：
    - 優先使用高優先級數據源
    - 失敗後自動切換到下一個
    - 所有數據源都失敗時拋出異常
    """
    
    def __init__(self, fetchers: Optional[List[BaseFetcher]] = None):
        """
        初始化管理器
        
        Args:
            fetchers: 數據源列表（可選，默認按優先級自動創建）
        """
        self._fetchers: List[BaseFetcher] = []
        
        if fetchers:
            # 按優先級排序
            self._fetchers = sorted(fetchers, key=lambda f: f.priority)
        else:
            # 默認數據源將在首次使用時延遲加載
            self._init_default_fetchers()
    
    def _init_default_fetchers(self) -> None:
        """
        初始化默認數據源列表

        優先級動態調整邏輯：
        - 如果配置了 TUSHARE_TOKEN：Tushare 優先級提升為 0（最高）
        - 否則按默認優先級：
          0. EfinanceFetcher (Priority 0) - 最高優先級
          1. AkshareFetcher (Priority 1)
          2. TushareFetcher (Priority 2)
          3. BaostockFetcher (Priority 3)
          4. YfinanceFetcher (Priority 4)
        """
        from .efinance_fetcher import EfinanceFetcher
        from .akshare_fetcher import AkshareFetcher
        from .tushare_fetcher import TushareFetcher
        from .baostock_fetcher import BaostockFetcher
        from .yfinance_fetcher import YfinanceFetcher
        from config import get_config

        config = get_config()

        # 創建所有數據源實例（優先級在各 Fetcher 的 __init__ 中確定）
        efinance = EfinanceFetcher()
        akshare = AkshareFetcher()
        tushare = TushareFetcher()  # 會根據 Token 配置自動調整優先級
        baostock = BaostockFetcher()
        yfinance = YfinanceFetcher()

        # 初始化數據源列表
        self._fetchers = [
            efinance,
            akshare,
            tushare,
            baostock,
            yfinance,
        ]

        # 按優先級排序（Tushare 如果配置了 Token 且初始化成功，優先級為 0）
        self._fetchers.sort(key=lambda f: f.priority)

        # 構建優先級說明
        priority_info = ", ".join([f"{f.name}(P{f.priority})" for f in self._fetchers])
        logger.info(f"已初始化 {len(self._fetchers)} 個數據源（按優先級）: {priority_info}")
    
    def add_fetcher(self, fetcher: BaseFetcher) -> None:
        """添加數據源並重新排序"""
        self._fetchers.append(fetcher)
        self._fetchers.sort(key=lambda f: f.priority)
    
    def get_daily_data(
        self, 
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30
    ) -> Tuple[pd.DataFrame, str]:
        """
        獲取日線數據（自動切換數據源）
        
        故障切換策略：
        1. 從最高優先級數據源開始嘗試
        2. 捕獲異常後自動切換到下一個
        3. 記錄每個數據源的失敗原因
        4. 所有數據源失敗後拋出詳細異常
        
        Args:
            stock_code: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            days: 獲取天數
            
        Returns:
            Tuple[DataFrame, str]: (數據, 成功的數據源名稱)
            
        Raises:
            DataFetchError: 所有數據源都失敗時拋出
        """
        errors = []
        
        for fetcher in self._fetchers:
            try:
                logger.info(f"嘗試使用 [{fetcher.name}] 獲取 {stock_code}...")
                df = fetcher.get_daily_data(
                    stock_code=stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    days=days
                )
                
                if df is not None and not df.empty:
                    logger.info(f"[{fetcher.name}] 成功獲取 {stock_code}")
                    return df, fetcher.name
                    
            except Exception as e:
                error_msg = f"[{fetcher.name}] 失敗: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
                # 繼續嘗試下一個數據源
                continue
        
        # 所有數據源都失敗
        error_summary = f"所有數據源獲取 {stock_code} 失敗:\n" + "\n".join(errors)
        logger.error(error_summary)
        raise DataFetchError(error_summary)
    
    @property
    def available_fetchers(self) -> List[str]:
        """返回可用數據源名稱列表"""
        return [f.name for f in self._fetchers]
