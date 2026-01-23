# -*- coding: utf-8 -*-
"""
===================================
YfinanceFetcher - 台股/港股/美股數據源 (Priority 0)
===================================

數據來源：Yahoo Finance（通過 yfinance 庫）
特點：支持台股、港股、美股等國際市場
定位：台股首選數據源，同時兼容其他市場

關鍵策略：
1. 自動識別股票代碼類型（台股 .TW / 港股 .HK / A股 .SS/.SZ / 美股）
2. 處理 Yahoo Finance 的數據格式差異
3. 失敗後指數退避重試
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .base import BaseFetcher, DataFetchError, STANDARD_COLUMNS

logger = logging.getLogger(__name__)


class YfinanceFetcher(BaseFetcher):
    """
    Yahoo Finance 數據源實現

    優先級：0（最高，台股首選）
    數據來源：Yahoo Finance

    關鍵策略：
    - 自動識別並轉換股票代碼格式（台股/港股/A股/美股）
    - 處理時區和數據格式差異
    - 失敗後指數退避重試

    支持市場：
    - 台股：2330.TW（台積電）、2317.TW（鴻海）
    - 港股：0700.HK（騰訊）、9988.HK（阿里巴巴）
    - A股：600519.SS（貴州茅台）、000001.SZ（平安銀行）
    - 美股：AAPL（蘋果）、TSLA（特斯拉）
    """

    name = "YfinanceFetcher"
    priority = 0  # 台股首選數據源
    
    def __init__(self):
        """初始化 YfinanceFetcher"""
        pass
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """
        轉換股票代碼為 Yahoo Finance 格式

        支持多市場自動識別：
        - 台股：2330.TW（台積電）、2317.TW（鴻海）
        - 港股：0700.HK（騰訊）、9988.HK（阿里巴巴）
        - A股滬市：600519.SS（貴州茅台）
        - A股深市：000001.SZ（平安銀行）
        - 美股：AAPL（蘋果）、TSLA（特斯拉）

        Args:
            stock_code: 原始代碼

        Returns:
            Yahoo Finance 格式代碼
        """
        code = stock_code.strip()

        # 已經包含正確後綴的情況（直接返回）
        valid_suffixes = ['.TW', '.TWO', '.HK', '.SS', '.SZ']
        if any(code.upper().endswith(suffix) for suffix in valid_suffixes):
            return code.upper()

        # 如果是美股代碼（純字母），直接返回
        if code.isalpha():
            return code.upper()

        # 去除可能的舊後綴（如 .SH）
        code = code.replace('.SH', '').replace('.sh', '')

        # 台股：4位數字 -> 默認加 .TW 後綴
        if code.isdigit() and len(code) == 4:
            logger.info(f"檢測到台股代碼 {code}，添加 .TW 後綴")
            return f"{code}.TW"

        # 港股：4位數字 + HK標識 或 5位數字（9開頭）
        if code.isdigit():
            if len(code) == 5 and code.startswith('9'):
                logger.info(f"檢測到港股代碼 {code}，添加 .HK 後綴")
                return f"{code}.HK"

        # A股滬市：600/601/603/688 開頭
        if code.startswith(('600', '601', '603', '688')):
            logger.info(f"檢測到A股滬市代碼 {code}，添加 .SS 後綴")
            return f"{code}.SS"

        # A股深市：000/002/300 開頭
        if code.startswith(('000', '002', '300')):
            logger.info(f"檢測到A股深市代碼 {code}，添加 .SZ 後綴")
            return f"{code}.SZ"

        # 默認：4位數字視為台股
        logger.warning(f"無法自動識別股票 {code} 的市場，默認使用台股 .TW 後綴")
        return f"{code}.TW"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        從 Yahoo Finance 獲取原始數據
        
        使用 yfinance.download() 獲取歷史數據
        
        流程：
        1. 轉換股票代碼格式
        2. 調用 yfinance API
        3. 處理返回數據
        """
        import yfinance as yf
        
        # 轉換代碼格式
        yf_code = self._convert_stock_code(stock_code)
        
        logger.debug(f"調用 yfinance.download({yf_code}, {start_date}, {end_date})")
        
        try:
            # 使用 yfinance 下載數據
            df = yf.download(
                tickers=yf_code,
                start=start_date,
                end=end_date,
                progress=False,  # 禁止進度條
                auto_adjust=True,  # 自動調整價格（復權）
            )
            
            if df.empty:
                raise DataFetchError(f"Yahoo Finance 未查詢到 {stock_code} 的數據")
            
            return df
            
        except Exception as e:
            if isinstance(e, DataFetchError):
                raise
            raise DataFetchError(f"Yahoo Finance 獲取數據失敗: {e}") from e
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        標準化 Yahoo Finance 數據
        
        yfinance 返回的列名：
        Open, High, Low, Close, Volume（索引是日期）
        
        需要映射到標準列名：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()
        
        # 重置索引，將日期從索引變為列
        df = df.reset_index()
        
        # 列名映射（yfinance 使用首字母大寫）
        column_mapping = {
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
        }
        
        df = df.rename(columns=column_mapping)
        
        # 計算漲跌幅（因為 yfinance 不直接提供）
        if 'close' in df.columns:
            df['pct_chg'] = df['close'].pct_change() * 100
            df['pct_chg'] = df['pct_chg'].fillna(0).round(2)
        
        # 計算成交額（yfinance 不提供，使用估算值）
        # 成交額 ≈ 成交量 * 平均價格
        if 'volume' in df.columns and 'close' in df.columns:
            df['amount'] = df['volume'] * df['close']
        else:
            df['amount'] = 0
        
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
    
    fetcher = YfinanceFetcher()
    
    try:
        df = fetcher.get_daily_data('600519')  # 茅臺
        print(f"獲取成功，共 {len(df)} 條數據")
        print(df.tail())
    except Exception as e:
        print(f"獲取失敗: {e}")
