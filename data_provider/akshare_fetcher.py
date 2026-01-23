# -*- coding: utf-8 -*-
"""
===================================
AkshareFetcher - 主數據源 (Priority 1)
===================================

數據來源：東方財富爬蟲（通過 akshare 庫）
特點：免費、無需 Token、數據全面
風險：爬蟲機制易被反爬封禁

防封禁策略：
1. 每次請求前隨機休眠 2-5 秒
2. 隨機輪換 User-Agent
3. 使用 tenacity 實現指數退避重試

增強數據：
- 實時行情：量比、換手率、市盈率、市淨率、總市值、流通市值
- 籌碼分佈：獲利比例、平均成本、籌碼集中度
"""

import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .base import BaseFetcher, DataFetchError, RateLimitError, STANDARD_COLUMNS


@dataclass
class RealtimeQuote:
    """
    實時行情數據
    
    包含當日實時交易數據和估值指標
    """
    code: str
    name: str = ""
    price: float = 0.0           # 最新價
    change_pct: float = 0.0      # 漲跌幅(%)
    change_amount: float = 0.0   # 漲跌額
    
    # 量價指標
    volume_ratio: float = 0.0    # 量比（當前成交量/過去5日平均成交量）
    turnover_rate: float = 0.0   # 換手率(%)
    amplitude: float = 0.0       # 振幅(%)
    
    # 估值指標
    pe_ratio: float = 0.0        # 市盈率(動態)
    pb_ratio: float = 0.0        # 市淨率
    total_mv: float = 0.0        # 總市值(元)
    circ_mv: float = 0.0         # 流通市值(元)
    
    # 其他
    change_60d: float = 0.0      # 60日漲跌幅(%)
    high_52w: float = 0.0        # 52周最高
    low_52w: float = 0.0         # 52周最低
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change_pct': self.change_pct,
            'volume_ratio': self.volume_ratio,
            'turnover_rate': self.turnover_rate,
            'amplitude': self.amplitude,
            'pe_ratio': self.pe_ratio,
            'pb_ratio': self.pb_ratio,
            'total_mv': self.total_mv,
            'circ_mv': self.circ_mv,
            'change_60d': self.change_60d,
        }


@dataclass  
class ChipDistribution:
    """
    籌碼分佈數據
    
    反映持倉成本分佈和獲利情況
    """
    code: str
    date: str = ""
    
    # 獲利情況
    profit_ratio: float = 0.0     # 獲利比例(0-1)
    avg_cost: float = 0.0         # 平均成本
    
    # 籌碼集中度
    cost_90_low: float = 0.0      # 90%籌碼成本下限
    cost_90_high: float = 0.0     # 90%籌碼成本上限
    concentration_90: float = 0.0  # 90%籌碼集中度（越小越集中）
    
    cost_70_low: float = 0.0      # 70%籌碼成本下限
    cost_70_high: float = 0.0     # 70%籌碼成本上限
    concentration_70: float = 0.0  # 70%籌碼集中度
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'code': self.code,
            'date': self.date,
            'profit_ratio': self.profit_ratio,
            'avg_cost': self.avg_cost,
            'cost_90_low': self.cost_90_low,
            'cost_90_high': self.cost_90_high,
            'concentration_90': self.concentration_90,
            'concentration_70': self.concentration_70,
        }
    
    def get_chip_status(self, current_price: float) -> str:
        """
        獲取籌碼狀態描述
        
        Args:
            current_price: 當前股價
            
        Returns:
            籌碼狀態描述
        """
        status_parts = []
        
        # 獲利比例分析
        if self.profit_ratio >= 0.9:
            status_parts.append("獲利盤極高(>90%)")
        elif self.profit_ratio >= 0.7:
            status_parts.append("獲利盤較高(70-90%)")
        elif self.profit_ratio >= 0.5:
            status_parts.append("獲利盤中等(50-70%)")
        elif self.profit_ratio >= 0.3:
            status_parts.append("套牢盤較多(>30%)")
        else:
            status_parts.append("套牢盤極重(>70%)")
        
        # 籌碼集中度分析 (90%集中度 < 10% 表示集中)
        if self.concentration_90 < 0.08:
            status_parts.append("籌碼高度集中")
        elif self.concentration_90 < 0.15:
            status_parts.append("籌碼較集中")
        elif self.concentration_90 < 0.25:
            status_parts.append("籌碼分散度中等")
        else:
            status_parts.append("籌碼較分散")
        
        # 成本與現價關係
        if current_price > 0 and self.avg_cost > 0:
            cost_diff = (current_price - self.avg_cost) / self.avg_cost * 100
            if cost_diff > 20:
                status_parts.append(f"現價高於平均成本{cost_diff:.1f}%")
            elif cost_diff > 5:
                status_parts.append(f"現價略高於成本{cost_diff:.1f}%")
            elif cost_diff > -5:
                status_parts.append("現價接近平均成本")
            else:
                status_parts.append(f"現價低於平均成本{abs(cost_diff):.1f}%")
        
        return "，".join(status_parts)

logger = logging.getLogger(__name__)


# User-Agent 池，用於隨機輪換
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


# 緩存實時行情數據（避免重複請求）
_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 60  # 60秒緩存有效期
}

# ETF 實時行情緩存
_etf_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 60  # 60秒緩存有效期
}


def _is_etf_code(stock_code: str) -> bool:
    """
    判斷代碼是否為 ETF 基金
    
    ETF 代碼規則：
    - 上交所 ETF: 51xxxx, 52xxxx, 56xxxx, 58xxxx
    - 深交所 ETF: 15xxxx, 16xxxx, 18xxxx
    
    Args:
        stock_code: 股票/基金代碼
        
    Returns:
        True 表示是 ETF 代碼，False 表示是普通股票代碼
    """
    etf_prefixes = ('51', '52', '56', '58', '15', '16', '18')
    return stock_code.startswith(etf_prefixes) and len(stock_code) == 6


def _is_hk_code(stock_code: str) -> bool:
    """
    判斷代碼是否為港股
    
    港股代碼規則：
    - 5位數字代碼，如 '00700' (騰訊控股)
    - 部分港股代碼可能帶有前綴，如 'hk00700', 'hk1810'
    
    Args:
        stock_code: 股票代碼
        
    Returns:
        True 表示是港股代碼，False 表示不是港股代碼
    """
    # 去除可能的 'hk' 前綴並檢查是否為純數字
    code = stock_code.lower()
    if code.startswith('hk'):
        # 帶 hk 前綴的一定是港股，去掉前綴後應為純數字（1-5位）
        numeric_part = code[2:]
        return numeric_part.isdigit() and 1 <= len(numeric_part) <= 5
    # 無前綴時，5位純數字才視為港股（避免誤判 A 股代碼）
    return code.isdigit() and len(code) == 5


class AkshareFetcher(BaseFetcher):
    """
    Akshare 數據源實現
    
    優先級：1（最高）
    數據來源：東方財富網爬蟲
    
    關鍵策略：
    - 每次請求前隨機休眠 2.0-5.0 秒
    - 隨機 User-Agent 輪換
    - 失敗後指數退避重試（最多3次）
    """
    
    name = "AkshareFetcher"
    priority = 1
    
    def __init__(self, sleep_min: float = 2.0, sleep_max: float = 5.0):
        """
        初始化 AkshareFetcher
        
        Args:
            sleep_min: 最小休眠時間（秒）
            sleep_max: 最大休眠時間（秒）
        """
        self.sleep_min = sleep_min
        self.sleep_max = sleep_max
        self._last_request_time: Optional[float] = None
    
    def _set_random_user_agent(self) -> None:
        """
        設置隨機 User-Agent
        
        通過修改 requests Session 的 headers 實現
        這是關鍵的反爬策略之一
        """
        try:
            import akshare as ak
            # akshare 內部使用 requests，我們通過環境變量或直接設置來影響
            # 實際上 akshare 可能不直接暴露 session，這裡通過 fake_useragent 作為補充
            random_ua = random.choice(USER_AGENTS)
            logger.debug(f"設置 User-Agent: {random_ua[:50]}...")
        except Exception as e:
            logger.debug(f"設置 User-Agent 失敗: {e}")
    
    def _enforce_rate_limit(self) -> None:
        """
        強制執行速率限制
        
        策略：
        1. 檢查距離上次請求的時間間隔
        2. 如果間隔不足，補充休眠時間
        3. 然後再執行隨機 jitter 休眠
        """
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            min_interval = self.sleep_min
            if elapsed < min_interval:
                additional_sleep = min_interval - elapsed
                logger.debug(f"補充休眠 {additional_sleep:.2f} 秒")
                time.sleep(additional_sleep)
        
        # 執行隨機 jitter 休眠
        self.random_sleep(self.sleep_min, self.sleep_max)
        self._last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),  # 最多重試3次
        wait=wait_exponential(multiplier=1, min=2, max=30),  # 指數退避：2, 4, 8... 最大30秒
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        從 Akshare 獲取原始數據
        
        根據代碼類型自動選擇 API：
        - 普通股票：使用 ak.stock_zh_a_hist()
        - ETF 基金：使用 ak.fund_etf_hist_em()
        
        流程：
        1. 判斷代碼類型（股票/ETF）
        2. 設置隨機 User-Agent
        3. 執行速率限制（隨機休眠）
        4. 調用對應的 akshare API
        5. 處理返回數據
        """
        # 根據代碼類型選擇不同的獲取方法
        if _is_hk_code(stock_code):
            return self._fetch_hk_data(stock_code, start_date, end_date)
        elif _is_etf_code(stock_code):
            return self._fetch_etf_data(stock_code, start_date, end_date)
        else:
            return self._fetch_stock_data(stock_code, start_date, end_date)
    
    def _fetch_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        獲取普通 A 股歷史數據
        
        數據來源：ak.stock_zh_a_hist()
        """
        import akshare as ak
        
        # 防封禁策略 1: 隨機 User-Agent
        self._set_random_user_agent()
        
        # 防封禁策略 2: 強制休眠
        self._enforce_rate_limit()
        
        logger.info(f"[API調用] ak.stock_zh_a_hist(symbol={stock_code}, period=daily, "
                   f"start_date={start_date.replace('-', '')}, end_date={end_date.replace('-', '')}, adjust=qfq)")
        
        try:
            # 調用 akshare 獲取 A 股日線數據
            # period="daily" 獲取日線數據
            # adjust="qfq" 獲取前復權數據
            import time as _time
            api_start = _time.time()
            
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # 前復權
            )
            
            api_elapsed = _time.time() - api_start
            
            # 記錄返回數據摘要
            if df is not None and not df.empty:
                logger.info(f"[API返回] ak.stock_zh_a_hist 成功: 返回 {len(df)} 行數據, 耗時 {api_elapsed:.2f}s")
                logger.info(f"[API返回] 列名: {list(df.columns)}")
                logger.info(f"[API返回] 日期範圍: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[API返回] 最新3條數據:\n{df.tail(3).to_string()}")
            else:
                logger.warning(f"[API返回] ak.stock_zh_a_hist 返回空數據, 耗時 {api_elapsed:.2f}s")
            
            return df
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 檢測反爬封禁
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '頻率', 'rate', '限制']):
                logger.warning(f"檢測到可能被封禁: {e}")
                raise RateLimitError(f"Akshare 可能被限流: {e}") from e
            
            raise DataFetchError(f"Akshare 獲取數據失敗: {e}") from e
    
    def _fetch_etf_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        獲取 ETF 基金歷史數據
        
        數據來源：ak.fund_etf_hist_em()
        
        Args:
            stock_code: ETF 代碼，如 '512400', '159883'
            start_date: 開始日期，格式 'YYYY-MM-DD'
            end_date: 結束日期，格式 'YYYY-MM-DD'
            
        Returns:
            ETF 歷史數據 DataFrame
        """
        import akshare as ak
        
        # 防封禁策略 1: 隨機 User-Agent
        self._set_random_user_agent()
        
        # 防封禁策略 2: 強制休眠
        self._enforce_rate_limit()
        
        logger.info(f"[API調用] ak.fund_etf_hist_em(symbol={stock_code}, period=daily, "
                   f"start_date={start_date.replace('-', '')}, end_date={end_date.replace('-', '')}, adjust=qfq)")
        
        try:
            import time as _time
            api_start = _time.time()
            
            # 調用 akshare 獲取 ETF 日線數據
            df = ak.fund_etf_hist_em(
                symbol=stock_code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # 前復權
            )
            
            api_elapsed = _time.time() - api_start
            
            # 記錄返回數據摘要
            if df is not None and not df.empty:
                logger.info(f"[API返回] ak.fund_etf_hist_em 成功: 返回 {len(df)} 行數據, 耗時 {api_elapsed:.2f}s")
                logger.info(f"[API返回] 列名: {list(df.columns)}")
                logger.info(f"[API返回] 日期範圍: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[API返回] 最新3條數據:\n{df.tail(3).to_string()}")
            else:
                logger.warning(f"[API返回] ak.fund_etf_hist_em 返回空數據, 耗時 {api_elapsed:.2f}s")
            
            return df
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 檢測反爬封禁
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '頻率', 'rate', '限制']):
                logger.warning(f"檢測到可能被封禁: {e}")
                raise RateLimitError(f"Akshare 可能被限流: {e}") from e
            
            raise DataFetchError(f"Akshare 獲取 ETF 數據失敗: {e}") from e
    
    def _fetch_hk_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        獲取港股歷史數據
        
        數據來源：ak.stock_hk_hist()
        
        Args:
            stock_code: 港股代碼，如 '00700', '01810'
            start_date: 開始日期，格式 'YYYY-MM-DD'
            end_date: 結束日期，格式 'YYYY-MM-DD'
            
        Returns:
            港股歷史數據 DataFrame
        """
        import akshare as ak
        
        # 防封禁策略 1: 隨機 User-Agent
        self._set_random_user_agent()
        
        # 防封禁策略 2: 強制休眠
        self._enforce_rate_limit()
        
        # 確保代碼格式正確（5位數字）
        code = stock_code.lower().replace('hk', '').zfill(5)
        
        logger.info(f"[API調用] ak.stock_hk_hist(symbol={code}, period=daily, "
                   f"start_date={start_date.replace('-', '')}, end_date={end_date.replace('-', '')}, adjust=qfq)")
        
        try:
            import time as _time
            api_start = _time.time()
            
            # 調用 akshare 獲取港股日線數據
            df = ak.stock_hk_hist(
                symbol=code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # 前復權
            )
            
            api_elapsed = _time.time() - api_start
            
            # 記錄返回數據摘要
            if df is not None and not df.empty:
                logger.info(f"[API返回] ak.stock_hk_hist 成功: 返回 {len(df)} 行數據, 耗時 {api_elapsed:.2f}s")
                logger.info(f"[API返回] 列名: {list(df.columns)}")
                logger.info(f"[API返回] 日期範圍: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[API返回] 最新3條數據:\n{df.tail(3).to_string()}")
            else:
                logger.warning(f"[API返回] ak.stock_hk_hist 返回空數據, 耗時 {api_elapsed:.2f}s")
            
            return df
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 檢測反爬封禁
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '頻率', 'rate', '限制']):
                logger.warning(f"檢測到可能被封禁: {e}")
                raise RateLimitError(f"Akshare 可能被限流: {e}") from e
            
            raise DataFetchError(f"Akshare 獲取港股數據失敗: {e}") from e
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        標準化 Akshare 數據
        
        Akshare 返回的列名（中文）：
        日期, 開盤, 收盤, 最高, 最低, 成交量, 成交額, 振幅, 漲跌幅, 漲跌額, 換手率
        
        需要映射到標準列名：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()
        
        # 列名映射（Akshare 中文列名 -> 標準英文列名）
        column_mapping = {
            '日期': 'date',
            '開盤': 'open',
            '收盤': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交額': 'amount',
            '漲跌幅': 'pct_chg',
        }
        
        # 重命名列
        df = df.rename(columns=column_mapping)
        
        # 添加股票代碼列
        df['code'] = stock_code
        
        # 只保留需要的列
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]
        
        return df
    
    def get_realtime_quote(self, stock_code: str) -> Optional[RealtimeQuote]:
        """
        獲取實時行情數據
        
        根據代碼類型自動選擇數據源：
        - 普通股票：ak.stock_zh_a_spot_em()
        - ETF 基金：ak.fund_etf_spot_em()
        
        Args:
            stock_code: 股票/ETF代碼
            
        Returns:
            RealtimeQuote 對象，獲取失敗返回 None
        """
        # 根據代碼類型選擇不同的獲取方法
        if _is_hk_code(stock_code):
            return self._get_hk_realtime_quote(stock_code)
        elif _is_etf_code(stock_code):
            return self._get_etf_realtime_quote(stock_code)
        else:
            return self._get_stock_realtime_quote(stock_code)
    
    def _get_stock_realtime_quote(self, stock_code: str) -> Optional[RealtimeQuote]:
        """
        獲取普通 A 股實時行情數據
        
        數據來源：ak.stock_zh_a_spot_em()
        包含：量比、換手率、市盈率、市淨率、總市值、流通市值等
        """
        import akshare as ak
        
        try:
            # 檢查緩存
            current_time = time.time()
            if (_realtime_cache['data'] is not None and 
                current_time - _realtime_cache['timestamp'] < _realtime_cache['ttl']):
                df = _realtime_cache['data']
                logger.debug(f"[緩存命中] 使用緩存的A股實時行情數據")
            else:
                last_error: Optional[Exception] = None
                df = None
                for attempt in range(1, 3):
                    try:
                        # 防封禁策略
                        self._set_random_user_agent()
                        self._enforce_rate_limit()

                        logger.info(f"[API調用] ak.stock_zh_a_spot_em() 獲取A股實時行情... (attempt {attempt}/2)")
                        import time as _time
                        api_start = _time.time()

                        df = ak.stock_zh_a_spot_em()

                        api_elapsed = _time.time() - api_start
                        logger.info(f"[API返回] ak.stock_zh_a_spot_em 成功: 返回 {len(df)} 只股票, 耗時 {api_elapsed:.2f}s")
                        break
                    except Exception as e:
                        last_error = e
                        logger.warning(f"[API錯誤] ak.stock_zh_a_spot_em 獲取失敗 (attempt {attempt}/2): {e}")
                        time.sleep(min(2 ** attempt, 5))

                # 更新緩存：成功緩存數據；失敗也緩存空數據，避免同一輪任務對同一接口反覆請求
                if df is None:
                    logger.error(f"[API錯誤] ak.stock_zh_a_spot_em 最終失敗: {last_error}")
                    df = pd.DataFrame()
                _realtime_cache['data'] = df
                _realtime_cache['timestamp'] = current_time

            if df is None or df.empty:
                logger.warning(f"[實時行情] A股實時行情數據為空，跳過 {stock_code}")
                return None
            
            # 查找指定股票
            row = df[df['代碼'] == stock_code]
            if row.empty:
                logger.warning(f"[API返回] 未找到股票 {stock_code} 的實時行情")
                return None
            
            row = row.iloc[0]
            
            # 安全獲取字段值
            def safe_float(val, default=0.0):
                try:
                    if pd.isna(val):
                        return default
                    return float(val)
                except:
                    return default
            
            quote = RealtimeQuote(
                code=stock_code,
                name=str(row.get('名稱', '')),
                price=safe_float(row.get('最新價')),
                change_pct=safe_float(row.get('漲跌幅')),
                change_amount=safe_float(row.get('漲跌額')),
                volume_ratio=safe_float(row.get('量比')),
                turnover_rate=safe_float(row.get('換手率')),
                amplitude=safe_float(row.get('振幅')),
                pe_ratio=safe_float(row.get('市盈率-動態')),
                pb_ratio=safe_float(row.get('市淨率')),
                total_mv=safe_float(row.get('總市值')),
                circ_mv=safe_float(row.get('流通市值')),
                change_60d=safe_float(row.get('60日漲跌幅')),
                high_52w=safe_float(row.get('52周最高')),
                low_52w=safe_float(row.get('52周最低')),
            )
            
            logger.info(f"[實時行情] {stock_code} {quote.name}: 價格={quote.price}, 漲跌={quote.change_pct}%, "
                       f"量比={quote.volume_ratio}, 換手率={quote.turnover_rate}%, "
                       f"PE={quote.pe_ratio}, PB={quote.pb_ratio}")
            return quote
            
        except Exception as e:
            logger.error(f"[API錯誤] 獲取 {stock_code} 實時行情失敗: {e}")
            return None
    
    def _get_etf_realtime_quote(self, stock_code: str) -> Optional[RealtimeQuote]:
        """
        獲取 ETF 基金實時行情數據
        
        數據來源：ak.fund_etf_spot_em()
        包含：最新價、漲跌幅、成交量、成交額、換手率等
        
        Args:
            stock_code: ETF 代碼
            
        Returns:
            RealtimeQuote 對象，獲取失敗返回 None
        """
        import akshare as ak
        
        try:
            # 檢查緩存
            current_time = time.time()
            if (_etf_realtime_cache['data'] is not None and 
                current_time - _etf_realtime_cache['timestamp'] < _etf_realtime_cache['ttl']):
                df = _etf_realtime_cache['data']
                logger.debug(f"[緩存命中] 使用緩存的ETF實時行情數據")
            else:
                last_error: Optional[Exception] = None
                df = None
                for attempt in range(1, 3):
                    try:
                        # 防封禁策略
                        self._set_random_user_agent()
                        self._enforce_rate_limit()

                        logger.info(f"[API調用] ak.fund_etf_spot_em() 獲取ETF實時行情... (attempt {attempt}/2)")
                        import time as _time
                        api_start = _time.time()

                        df = ak.fund_etf_spot_em()

                        api_elapsed = _time.time() - api_start
                        logger.info(f"[API返回] ak.fund_etf_spot_em 成功: 返回 {len(df)} 只ETF, 耗時 {api_elapsed:.2f}s")
                        break
                    except Exception as e:
                        last_error = e
                        logger.warning(f"[API錯誤] ak.fund_etf_spot_em 獲取失敗 (attempt {attempt}/2): {e}")
                        time.sleep(min(2 ** attempt, 5))

                if df is None:
                    logger.error(f"[API錯誤] ak.fund_etf_spot_em 最終失敗: {last_error}")
                    df = pd.DataFrame()
                _etf_realtime_cache['data'] = df
                _etf_realtime_cache['timestamp'] = current_time

            if df is None or df.empty:
                logger.warning(f"[實時行情] ETF實時行情數據為空，跳過 {stock_code}")
                return None
            
            # 查找指定 ETF
            row = df[df['代碼'] == stock_code]
            if row.empty:
                logger.warning(f"[API返回] 未找到 ETF {stock_code} 的實時行情")
                return None
            
            row = row.iloc[0]
            
            # 安全獲取字段值
            def safe_float(val, default=0.0):
                try:
                    if pd.isna(val):
                        return default
                    return float(val)
                except:
                    return default
            
            # ETF 行情數據構建（部分字段 ETF 可能不支持，使用默認值）
            quote = RealtimeQuote(
                code=stock_code,
                name=str(row.get('名稱', '')),
                price=safe_float(row.get('最新價')),
                change_pct=safe_float(row.get('漲跌幅')),
                change_amount=safe_float(row.get('漲跌額')),
                volume_ratio=safe_float(row.get('量比', 0)),  # ETF 可能無量比
                turnover_rate=safe_float(row.get('換手率')),
                amplitude=safe_float(row.get('振幅')),
                pe_ratio=0.0,  # ETF 通常無市盈率
                pb_ratio=0.0,  # ETF 通常無市淨率
                total_mv=safe_float(row.get('總市值', 0)),
                circ_mv=safe_float(row.get('流通市值', 0)),
                change_60d=0.0,  # ETF 接口可能不提供
                high_52w=safe_float(row.get('52周最高', 0)),
                low_52w=safe_float(row.get('52周最低', 0)),
            )
            
            logger.info(f"[ETF實時行情] {stock_code} {quote.name}: 價格={quote.price}, 漲跌={quote.change_pct}%, "
                       f"換手率={quote.turnover_rate}%")
            return quote
            
        except Exception as e:
            logger.error(f"[API錯誤] 獲取 ETF {stock_code} 實時行情失敗: {e}")
            return None
    
    def _get_hk_realtime_quote(self, stock_code: str) -> Optional[RealtimeQuote]:
        """
        獲取港股實時行情數據
        
        數據來源：ak.stock_hk_spot_em()
        包含：最新價、漲跌幅、成交量、成交額等
        
        Args:
            stock_code: 港股代碼
            
        Returns:
            RealtimeQuote 對象，獲取失敗返回 None
        """
        import akshare as ak
        
        try:
            # 防封禁策略
            self._set_random_user_agent()
            self._enforce_rate_limit()
            
            # 確保代碼格式正確（5位數字）
            code = stock_code.lower().replace('hk', '').zfill(5)
            
            logger.info(f"[API調用] ak.stock_hk_spot_em() 獲取港股實時行情...")
            import time as _time
            api_start = _time.time()
            
            df = ak.stock_hk_spot_em()
            
            api_elapsed = _time.time() - api_start
            logger.info(f"[API返回] ak.stock_hk_spot_em 成功: 返回 {len(df)} 只港股, 耗時 {api_elapsed:.2f}s")
            
            # 查找指定港股
            row = df[df['代碼'] == code]
            if row.empty:
                logger.warning(f"[API返回] 未找到港股 {code} 的實時行情")
                return None
            
            row = row.iloc[0]
            
            # 安全獲取字段值
            def safe_float(val, default=0.0):
                try:
                    if pd.isna(val):
                        return default
                    return float(val)
                except:
                    return default
            
            # 港股行情數據構建
            quote = RealtimeQuote(
                code=stock_code,
                name=str(row.get('名稱', '')),
                price=safe_float(row.get('最新價')),
                change_pct=safe_float(row.get('漲跌幅')),
                change_amount=safe_float(row.get('漲跌額')),
                volume_ratio=safe_float(row.get('量比', 0)),  # 港股可能無量比
                turnover_rate=safe_float(row.get('換手率', 0)),
                amplitude=safe_float(row.get('振幅', 0)),
                pe_ratio=safe_float(row.get('市盈率', 0)),  # 港股可能有市盈率
                pb_ratio=safe_float(row.get('市淨率', 0)),  # 港股可能有市淨率
                total_mv=safe_float(row.get('總市值', 0)),
                circ_mv=safe_float(row.get('流通市值', 0)),
                change_60d=0.0,  # 港股接口可能不提供
                high_52w=safe_float(row.get('52周最高', 0)),
                low_52w=safe_float(row.get('52周最低', 0)),
            )
            
            logger.info(f"[港股實時行情] {stock_code} {quote.name}: 價格={quote.price}, 漲跌={quote.change_pct}%, "
                       f"換手率={quote.turnover_rate}%")
            return quote
            
        except Exception as e:
            logger.error(f"[API錯誤] 獲取港股 {stock_code} 實時行情失敗: {e}")
            return None
    
    def get_chip_distribution(self, stock_code: str) -> Optional[ChipDistribution]:
        """
        獲取籌碼分佈數據
        
        數據來源：ak.stock_cyq_em()
        包含：獲利比例、平均成本、籌碼集中度
        
        注意：ETF/指數沒有籌碼分佈數據，會直接返回 None
        
        Args:
            stock_code: 股票代碼
            
        Returns:
            ChipDistribution 對象（最新一天的數據），獲取失敗返回 None
        """
        import akshare as ak
        
        # ETF/指數沒有籌碼分佈數據
        if _is_etf_code(stock_code):
            logger.debug(f"[API跳過] {stock_code} 是 ETF/指數，無籌碼分佈數據")
            return None
        
        try:
            # 防封禁策略
            self._set_random_user_agent()
            self._enforce_rate_limit()
            
            logger.info(f"[API調用] ak.stock_cyq_em(symbol={stock_code}) 獲取籌碼分佈...")
            import time as _time
            api_start = _time.time()
            
            df = ak.stock_cyq_em(symbol=stock_code)
            
            api_elapsed = _time.time() - api_start
            
            if df.empty:
                logger.warning(f"[API返回] ak.stock_cyq_em 返回空數據, 耗時 {api_elapsed:.2f}s")
                return None
            
            logger.info(f"[API返回] ak.stock_cyq_em 成功: 返回 {len(df)} 天數據, 耗時 {api_elapsed:.2f}s")
            logger.debug(f"[API返回] 籌碼數據列名: {list(df.columns)}")
            
            # 取最新一天的數據
            latest = df.iloc[-1]
            
            def safe_float(val, default=0.0):
                try:
                    if pd.isna(val):
                        return default
                    return float(val)
                except:
                    return default
            
            chip = ChipDistribution(
                code=stock_code,
                date=str(latest.get('日期', '')),
                profit_ratio=safe_float(latest.get('獲利比例')),
                avg_cost=safe_float(latest.get('平均成本')),
                cost_90_low=safe_float(latest.get('90成本-低')),
                cost_90_high=safe_float(latest.get('90成本-高')),
                concentration_90=safe_float(latest.get('90集中度')),
                cost_70_low=safe_float(latest.get('70成本-低')),
                cost_70_high=safe_float(latest.get('70成本-高')),
                concentration_70=safe_float(latest.get('70集中度')),
            )
            
            logger.info(f"[籌碼分佈] {stock_code} 日期={chip.date}: 獲利比例={chip.profit_ratio:.1%}, "
                       f"平均成本={chip.avg_cost}, 90%集中度={chip.concentration_90:.2%}, "
                       f"70%集中度={chip.concentration_70:.2%}")
            return chip
            
        except Exception as e:
            logger.error(f"[API錯誤] 獲取 {stock_code} 籌碼分佈失敗: {e}")
            return None
    
    def get_enhanced_data(self, stock_code: str, days: int = 60) -> Dict[str, Any]:
        """
        獲取增強數據（歷史K線 + 實時行情 + 籌碼分佈）
        
        Args:
            stock_code: 股票代碼
            days: 歷史數據天數
            
        Returns:
            包含所有數據的字典
        """
        result = {
            'code': stock_code,
            'daily_data': None,
            'realtime_quote': None,
            'chip_distribution': None,
        }
        
        # 獲取日線數據
        try:
            df = self.get_daily_data(stock_code, days=days)
            result['daily_data'] = df
        except Exception as e:
            logger.error(f"獲取 {stock_code} 日線數據失敗: {e}")
        
        # 獲取實時行情
        result['realtime_quote'] = self.get_realtime_quote(stock_code)
        
        # 獲取籌碼分佈
        result['chip_distribution'] = self.get_chip_distribution(stock_code)
        
        return result


if __name__ == "__main__":
    # 測試代碼
    logging.basicConfig(level=logging.DEBUG)
    
    fetcher = AkshareFetcher()
    
    # 測試普通股票
    print("=" * 50)
    print("測試普通股票數據獲取")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('600519')  # 茅臺
        print(f"[股票] 獲取成功，共 {len(df)} 條數據")
        print(df.tail())
    except Exception as e:
        print(f"[股票] 獲取失敗: {e}")
    
    # 測試 ETF 基金
    print("\n" + "=" * 50)
    print("測試 ETF 基金數據獲取")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('512400')  # 有色龍頭ETF
        print(f"[ETF] 獲取成功，共 {len(df)} 條數據")
        print(df.tail())
    except Exception as e:
        print(f"[ETF] 獲取失敗: {e}")
    
    # 測試 ETF 實時行情
    print("\n" + "=" * 50)
    print("測試 ETF 實時行情獲取")
    print("=" * 50)
    try:
        quote = fetcher.get_realtime_quote('512880')  # 證券ETF
        if quote:
            print(f"[ETF實時] {quote.name}: 價格={quote.price}, 漲跌幅={quote.change_pct}%")
        else:
            print("[ETF實時] 未獲取到數據")
    except Exception as e:
        print(f"[ETF實時] 獲取失敗: {e}")
    
    # 測試港股歷史數據
    print("\n" + "=" * 50)
    print("測試港股歷史數據獲取")
    print("=" * 50)
    try:
        df = fetcher.get_daily_data('00700')  # 騰訊控股
        print(f"[港股] 獲取成功，共 {len(df)} 條數據")
        print(df.tail())
    except Exception as e:
        print(f"[港股] 獲取失敗: {e}")
    
    # 測試港股實時行情
    print("\n" + "=" * 50)
    print("測試港股實時行情獲取")
    print("=" * 50)
    try:
        quote = fetcher.get_realtime_quote('00700')  # 騰訊控股
        if quote:
            print(f"[港股實時] {quote.name}: 價格={quote.price}, 漲跌幅={quote.change_pct}%")
        else:
            print("[港股實時] 未獲取到數據")
    except Exception as e:
        print(f"[港股實時] 獲取失敗: {e}")
