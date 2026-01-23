# -*- coding: utf-8 -*-
"""
===================================
A股自選股智能分析系統 - 存儲層
===================================

職責：
1. 管理 SQLite 數據庫連接（單例模式）
2. 定義 ORM 數據模型
3. 提供數據存取接口
4. 實現智能更新邏輯（斷點續傳）
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    Date,
    DateTime,
    Integer,
    Index,
    UniqueConstraint,
    select,
    and_,
    desc,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    Session,
)
from sqlalchemy.exc import IntegrityError

from config import get_config

logger = logging.getLogger(__name__)

# SQLAlchemy ORM 基類
Base = declarative_base()


# === 數據模型定義 ===

class StockDaily(Base):
    """
    股票日線數據模型
    
    存儲每日行情數據和計算的技術指標
    支持多股票、多日期的唯一約束
    """
    __tablename__ = 'stock_daily'
    
    # 主鍵
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 股票代碼（如 600519, 000001）
    code = Column(String(10), nullable=False, index=True)
    
    # 交易日期
    date = Column(Date, nullable=False, index=True)
    
    # OHLC 數據
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    
    # 成交數據
    volume = Column(Float)  # 成交量（股）
    amount = Column(Float)  # 成交額（元）
    pct_chg = Column(Float)  # 漲跌幅（%）
    
    # 技術指標
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    volume_ratio = Column(Float)  # 量比
    
    # 數據來源
    data_source = Column(String(50))  # 記錄數據來源（如 AkshareFetcher）
    
    # 更新時間
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 唯一約束：同一股票同一日期只能有一條數據
    __table_args__ = (
        UniqueConstraint('code', 'date', name='uix_code_date'),
        Index('ix_code_date', 'code', 'date'),
    )
    
    def __repr__(self):
        return f"<StockDaily(code={self.code}, date={self.date}, close={self.close})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'code': self.code,
            'date': self.date,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'amount': self.amount,
            'pct_chg': self.pct_chg,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'volume_ratio': self.volume_ratio,
            'data_source': self.data_source,
        }


class DatabaseManager:
    """
    數據庫管理器 - 單例模式
    
    職責：
    1. 管理數據庫連接池
    2. 提供 Session 上下文管理
    3. 封裝數據存取操作
    """
    
    _instance: Optional['DatabaseManager'] = None
    
    def __new__(cls, *args, **kwargs):
        """單例模式實現"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_url: Optional[str] = None):
        """
        初始化數據庫管理器
        
        Args:
            db_url: 數據庫連接 URL（可選，默認從配置讀取）
        """
        if self._initialized:
            return
        
        if db_url is None:
            config = get_config()
            db_url = config.get_db_url()
        
        # 創建數據庫引擎
        self._engine = create_engine(
            db_url,
            echo=False,  # 設為 True 可查看 SQL 語句
            pool_pre_ping=True,  # 連接健康檢查
        )
        
        # 創建 Session 工廠
        self._SessionLocal = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
        )
        
        # 創建所有表
        Base.metadata.create_all(self._engine)
        
        self._initialized = True
        logger.info(f"數據庫初始化完成: {db_url}")
    
    @classmethod
    def get_instance(cls) -> 'DatabaseManager':
        """獲取單例實例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置單例（用於測試）"""
        if cls._instance is not None:
            cls._instance._engine.dispose()
            cls._instance = None
    
    def get_session(self) -> Session:
        """
        獲取數據庫 Session
        
        使用示例:
            with db.get_session() as session:
                # 執行查詢
                session.commit()  # 如果需要
        """
        session = self._SessionLocal()
        try:
            return session
        except Exception:
            session.close()
            raise
    
    def has_today_data(self, code: str, target_date: Optional[date] = None) -> bool:
        """
        檢查是否已有指定日期的數據
        
        用於斷點續傳邏輯：如果已有數據則跳過網絡請求
        
        Args:
            code: 股票代碼
            target_date: 目標日期（默認今天）
            
        Returns:
            是否存在數據
        """
        if target_date is None:
            target_date = date.today()
        
        with self.get_session() as session:
            result = session.execute(
                select(StockDaily).where(
                    and_(
                        StockDaily.code == code,
                        StockDaily.date == target_date
                    )
                )
            ).scalar_one_or_none()
            
            return result is not None
    
    def get_latest_data(
        self, 
        code: str, 
        days: int = 2
    ) -> List[StockDaily]:
        """
        獲取最近 N 天的數據
        
        用於計算"相比昨日"的變化
        
        Args:
            code: 股票代碼
            days: 獲取天數
            
        Returns:
            StockDaily 對象列表（按日期降序）
        """
        with self.get_session() as session:
            results = session.execute(
                select(StockDaily)
                .where(StockDaily.code == code)
                .order_by(desc(StockDaily.date))
                .limit(days)
            ).scalars().all()
            
            return list(results)
    
    def get_data_range(
        self, 
        code: str, 
        start_date: date, 
        end_date: date
    ) -> List[StockDaily]:
        """
        獲取指定日期範圍的數據
        
        Args:
            code: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            StockDaily 對象列表
        """
        with self.get_session() as session:
            results = session.execute(
                select(StockDaily)
                .where(
                    and_(
                        StockDaily.code == code,
                        StockDaily.date >= start_date,
                        StockDaily.date <= end_date
                    )
                )
                .order_by(StockDaily.date)
            ).scalars().all()
            
            return list(results)
    
    def save_daily_data(
        self, 
        df: pd.DataFrame, 
        code: str,
        data_source: str = "Unknown"
    ) -> int:
        """
        保存日線數據到數據庫
        
        策略：
        - 使用 UPSERT 邏輯（存在則更新，不存在則插入）
        - 跳過已存在的數據，避免重複
        
        Args:
            df: 包含日線數據的 DataFrame
            code: 股票代碼
            data_source: 數據來源名稱
            
        Returns:
            新增/更新的記錄數
        """
        if df is None or df.empty:
            logger.warning(f"保存數據為空，跳過 {code}")
            return 0
        
        saved_count = 0
        
        with self.get_session() as session:
            try:
                for _, row in df.iterrows():
                    # 解析日期
                    row_date = row.get('date')
                    if isinstance(row_date, str):
                        row_date = datetime.strptime(row_date, '%Y-%m-%d').date()
                    elif isinstance(row_date, datetime):
                        row_date = row_date.date()
                    elif isinstance(row_date, pd.Timestamp):
                        row_date = row_date.date()
                    
                    # 檢查是否已存在
                    existing = session.execute(
                        select(StockDaily).where(
                            and_(
                                StockDaily.code == code,
                                StockDaily.date == row_date
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if existing:
                        # 更新現有記錄
                        existing.open = row.get('open')
                        existing.high = row.get('high')
                        existing.low = row.get('low')
                        existing.close = row.get('close')
                        existing.volume = row.get('volume')
                        existing.amount = row.get('amount')
                        existing.pct_chg = row.get('pct_chg')
                        existing.ma5 = row.get('ma5')
                        existing.ma10 = row.get('ma10')
                        existing.ma20 = row.get('ma20')
                        existing.volume_ratio = row.get('volume_ratio')
                        existing.data_source = data_source
                        existing.updated_at = datetime.now()
                    else:
                        # 創建新記錄
                        record = StockDaily(
                            code=code,
                            date=row_date,
                            open=row.get('open'),
                            high=row.get('high'),
                            low=row.get('low'),
                            close=row.get('close'),
                            volume=row.get('volume'),
                            amount=row.get('amount'),
                            pct_chg=row.get('pct_chg'),
                            ma5=row.get('ma5'),
                            ma10=row.get('ma10'),
                            ma20=row.get('ma20'),
                            volume_ratio=row.get('volume_ratio'),
                            data_source=data_source,
                        )
                        session.add(record)
                        saved_count += 1
                
                session.commit()
                logger.info(f"保存 {code} 數據成功，新增 {saved_count} 條")
                
            except Exception as e:
                session.rollback()
                logger.error(f"保存 {code} 數據失敗: {e}")
                raise
        
        return saved_count
    
    def get_analysis_context(
        self, 
        code: str,
        target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        獲取分析所需的上下文數據
        
        返回今日數據 + 昨日數據的對比信息
        
        Args:
            code: 股票代碼
            target_date: 目標日期（默認今天）
            
        Returns:
            包含今日數據、昨日對比等信息的字典
        """
        if target_date is None:
            target_date = date.today()
        
        # 獲取最近2天數據
        recent_data = self.get_latest_data(code, days=2)
        
        if not recent_data:
            logger.warning(f"未找到 {code} 的數據")
            return None
        
        today_data = recent_data[0]
        yesterday_data = recent_data[1] if len(recent_data) > 1 else None
        
        context = {
            'code': code,
            'date': today_data.date.isoformat(),
            'today': today_data.to_dict(),
        }
        
        if yesterday_data:
            context['yesterday'] = yesterday_data.to_dict()
            
            # 計算相比昨日的變化
            if yesterday_data.volume and yesterday_data.volume > 0:
                context['volume_change_ratio'] = round(
                    today_data.volume / yesterday_data.volume, 2
                )
            
            if yesterday_data.close and yesterday_data.close > 0:
                context['price_change_ratio'] = round(
                    (today_data.close - yesterday_data.close) / yesterday_data.close * 100, 2
                )
            
            # 均線形態判斷
            context['ma_status'] = self._analyze_ma_status(today_data)
        
        return context
    
    def _analyze_ma_status(self, data: StockDaily) -> str:
        """
        分析均線形態
        
        判斷條件：
        - 多頭排列：close > ma5 > ma10 > ma20
        - 空頭排列：close < ma5 < ma10 < ma20
        - 震盪整理：其他情況
        """
        close = data.close or 0
        ma5 = data.ma5 or 0
        ma10 = data.ma10 or 0
        ma20 = data.ma20 or 0
        
        if close > ma5 > ma10 > ma20 > 0:
            return "多頭排列 📈"
        elif close < ma5 < ma10 < ma20 and ma20 > 0:
            return "空頭排列 📉"
        elif close > ma5 and ma5 > ma10:
            return "短期向好 🔼"
        elif close < ma5 and ma5 < ma10:
            return "短期走弱 🔽"
        else:
            return "震盪整理 ↔️"


# 便捷函數
def get_db() -> DatabaseManager:
    """獲取數據庫管理器實例的快捷方式"""
    return DatabaseManager.get_instance()


if __name__ == "__main__":
    # 測試代碼
    logging.basicConfig(level=logging.DEBUG)
    
    db = get_db()
    
    print("=== 數據庫測試 ===")
    print(f"數據庫初始化成功")
    
    # 測試檢查今日數據
    has_data = db.has_today_data('600519')
    print(f"茅臺今日是否有數據: {has_data}")
    
    # 測試保存數據
    test_df = pd.DataFrame({
        'date': [date.today()],
        'open': [1800.0],
        'high': [1850.0],
        'low': [1780.0],
        'close': [1820.0],
        'volume': [10000000],
        'amount': [18200000000],
        'pct_chg': [1.5],
        'ma5': [1810.0],
        'ma10': [1800.0],
        'ma20': [1790.0],
        'volume_ratio': [1.2],
    })
    
    saved = db.save_daily_data(test_df, '600519', 'TestSource')
    print(f"保存測試數據: {saved} 條")
    
    # 測試獲取上下文
    context = db.get_analysis_context('600519')
    print(f"分析上下文: {context}")
