# -*- coding: utf-8 -*-
"""
===================================
趋势交易分析器 - 基于用户交易理念
===================================

交易理念核心原则：
1. 严进策略 - 不追高，追求每笔交易成功率
2. 趋势交易 - MA5>MA10>MA20 多头排列，顺势而为
3. 效率优先 - 关注筹码结构好的股票
4. 买点偏好 - 在 MA5/MA10 附近回踩买入

技术标准：
- 多头排列：MA5 > MA10 > MA20
- 乖离率：(Close - MA5) / MA5 < 5%（不追高）
- 量能形态：缩量回调优先
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class TrendStatus(Enum):
    """趋势状态枚举"""
    STRONG_BULL = "强势多头"      # MA5 > MA10 > MA20，且间距扩大
    BULL = "多头排列"             # MA5 > MA10 > MA20
    WEAK_BULL = "弱势多头"        # MA5 > MA10，但 MA10 < MA20
    CONSOLIDATION = "盘整"        # 均线缠绕
    WEAK_BEAR = "弱势空头"        # MA5 < MA10，但 MA10 > MA20
    BEAR = "空头排列"             # MA5 < MA10 < MA20
    STRONG_BEAR = "强势空头"      # MA5 < MA10 < MA20，且间距扩大


class VolumeStatus(Enum):
    """量能状态枚举"""
    HEAVY_VOLUME_UP = "放量上涨"       # 量价齐升
    HEAVY_VOLUME_DOWN = "放量下跌"     # 放量杀跌
    SHRINK_VOLUME_UP = "缩量上涨"      # 无量上涨
    SHRINK_VOLUME_DOWN = "缩量回调"    # 缩量回调（好）
    NORMAL = "量能正常"


class BuySignal(Enum):
    """买入信号枚举"""
    STRONG_BUY = "强烈买入"       # 多条件满足
    BUY = "买入"                  # 基本条件满足
    HOLD = "持有"                 # 已持有可继续
    WAIT = "观望"                 # 等待更好时机
    SELL = "卖出"                 # 趋势转弱
    STRONG_SELL = "强烈卖出"      # 趋势破坏


class MACDStatus(Enum):
    """MACD状态枚举"""
    GOLDEN_CROSS_ZERO = "零轴上金叉"      # DIF上穿DEA，且在零轴上方
    GOLDEN_CROSS = "金叉"                # DIF上穿DEA
    BULLISH = "多头"                    # DIF>DEA>0
    CROSSING_UP = "上穿零轴"             # DIF上穿零轴
    CROSSING_DOWN = "下穿零轴"           # DIF下穿零轴
    BEARISH = "空头"                    # DIF<DEA<0
    DEATH_CROSS = "死叉"                # DIF下穿DEA


class RSIStatus(Enum):
    """RSI状态枚举"""
    OVERBOUGHT = "超买"        # RSI > 70
    STRONG_BUY = "强势买入"    # 50 < RSI < 70
    NEUTRAL = "中性"          # 40 <= RSI <= 60
    WEAK = "弱势"             # 30 < RSI < 40
    OVERSOLD = "超卖"         # RSI < 30


class KDJStatus(Enum):
    """KDJ状态枚举"""
    GOLDEN_CROSS = "金叉"          # J上穿D
    DEATH_CROSS = "死叉"           # J下穿D
    OVERBOUGHT = "超买"            # K>80 且 D>80
    OVERSOLD = "超卖"              # K<20 且 D<20
    BULLISH = "多头"               # K>D
    BEARISH = "空头"               # K<D


class BollingerStatus(Enum):
    """布林带状态枚举"""
    ABOVE_UPPER = "突破上轨"       # 价格>上轨
    NEAR_UPPER = "接近上轨"        # 价格在中轨和上轨之间偏上
    MIDDLE = "中轨附近"            # 价格在中轨附近
    NEAR_LOWER = "接近下轨"        # 价格在中轨和下轨之间偏下
    BELOW_LOWER = "跌破下轨"       # 价格<下轨
    SQUEEZE = "缩口"               # 带宽收窄，即将变盘


@dataclass
class TrendAnalysisResult:
    """趋势分析结果"""
    code: str
    
    # 趋势判断
    trend_status: TrendStatus = TrendStatus.CONSOLIDATION
    ma_alignment: str = ""           # 均线排列描述
    trend_strength: float = 0.0      # 趋势强度 0-100
    
    # 均线数据
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    current_price: float = 0.0
    
    # 乖离率（与 MA5 的偏离度）
    bias_ma5: float = 0.0            # (Close - MA5) / MA5 * 100
    bias_ma10: float = 0.0
    bias_ma20: float = 0.0
    
    # 量能分析
    volume_status: VolumeStatus = VolumeStatus.NORMAL
    volume_ratio_5d: float = 0.0     # 当日成交量/5日均量
    volume_trend: str = ""           # 量能趋势描述
    
    # 支撑压力
    support_ma5: bool = False        # MA5 是否构成支撑
    support_ma10: bool = False       # MA10 是否构成支撑
    resistance_levels: List[float] = field(default_factory=list)
    support_levels: List[float] = field(default_factory=list)

    # MACD 指标
    macd_dif: float = 0.0          # DIF 快线
    macd_dea: float = 0.0          # DEA 慢线
    macd_bar: float = 0.0           # MACD 柱状图
    macd_status: MACDStatus = MACDStatus.BULLISH
    macd_signal: str = ""            # MACD 信号描述

    # RSI 指标
    rsi_6: float = 0.0              # RSI(6) 短期
    rsi_12: float = 0.0             # RSI(12) 中期
    rsi_24: float = 0.0             # RSI(24) 长期
    rsi_status: RSIStatus = RSIStatus.NEUTRAL
    rsi_signal: str = ""              # RSI 信号描述

    # KDJ 指标
    kdj_k: float = 50.0             # K值
    kdj_d: float = 50.0             # D值
    kdj_j: float = 50.0             # J值
    kdj_status: KDJStatus = KDJStatus.BULLISH
    kdj_signal: str = ""             # KDJ 信号描述

    # 布林带指标
    boll_upper: float = 0.0         # 上轨
    boll_middle: float = 0.0        # 中轨 (MA20)
    boll_lower: float = 0.0         # 下轨
    boll_width: float = 0.0         # 带宽 (upper-lower)/middle*100
    boll_position: float = 0.0      # 价格在带中的位置 0-100
    boll_status: BollingerStatus = BollingerStatus.MIDDLE
    boll_signal: str = ""            # 布林带信号描述

    # 买入信号
    buy_signal: BuySignal = BuySignal.WAIT
    signal_score: int = 0            # 综合评分 0-100
    signal_reasons: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'trend_status': self.trend_status.value,
            'ma_alignment': self.ma_alignment,
            'trend_strength': self.trend_strength,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'ma60': self.ma60,
            'current_price': self.current_price,
            'bias_ma5': self.bias_ma5,
            'bias_ma10': self.bias_ma10,
            'bias_ma20': self.bias_ma20,
            'volume_status': self.volume_status.value,
            'volume_ratio_5d': self.volume_ratio_5d,
            'volume_trend': self.volume_trend,
            'support_ma5': self.support_ma5,
            'support_ma10': self.support_ma10,
            'buy_signal': self.buy_signal.value,
            'signal_score': self.signal_score,
            'signal_reasons': self.signal_reasons,
            'risk_factors': self.risk_factors,
            'macd_dif': self.macd_dif,
            'macd_dea': self.macd_dea,
            'macd_bar': self.macd_bar,
            'macd_status': self.macd_status.value,
            'macd_signal': self.macd_signal,
            'rsi_6': self.rsi_6,
            'rsi_12': self.rsi_12,
            'rsi_24': self.rsi_24,
            'rsi_status': self.rsi_status.value,
            'rsi_signal': self.rsi_signal,
            'kdj_k': self.kdj_k,
            'kdj_d': self.kdj_d,
            'kdj_j': self.kdj_j,
            'kdj_status': self.kdj_status.value,
            'kdj_signal': self.kdj_signal,
            'boll_upper': self.boll_upper,
            'boll_middle': self.boll_middle,
            'boll_lower': self.boll_lower,
            'boll_width': self.boll_width,
            'boll_position': self.boll_position,
            'boll_status': self.boll_status.value,
            'boll_signal': self.boll_signal,
        }


class StockTrendAnalyzer:
    """
    股票趋势分析器

    基于用户交易理念实现：
    1. 趋势判断 - MA5>MA10>MA20 多头排列
    2. 乖离率检测 - 不追高，偏离 MA5 超过 5% 不买
    3. 量能分析 - 偏好缩量回调
    4. 买点识别 - 回踩 MA5/MA10 支撑
    5. MACD 指标 - 趋势确认和金叉死叉信号
    6. RSI 指标 - 超买超卖判断
    7. KDJ 指标 - 超买超卖和金叉死叉信号
    8. 布林带 - 通道突破和缩口变盘信号
    """
    
    # 交易参数配置
    BIAS_THRESHOLD = 5.0        # 乖离率阈值（%），超过此值不买入
    VOLUME_SHRINK_RATIO = 0.7   # 缩量判断阈值（当日量/5日均量）
    VOLUME_HEAVY_RATIO = 1.5    # 放量判断阈值
    MA_SUPPORT_TOLERANCE = 0.02  # MA 支撑判断容忍度（2%）

    # MACD 参数（标准12/26/9）
    MACD_FAST = 12              # 快线周期
    MACD_SLOW = 26             # 慢线周期
    MACD_SIGNAL = 9             # 信号线周期

    # RSI 参数
    RSI_SHORT = 6               # 短期RSI周期
    RSI_MID = 12               # 中期RSI周期
    RSI_LONG = 24              # 长期RSI周期
    RSI_OVERBOUGHT = 70        # 超买阈值
    RSI_OVERSOLD = 30          # 超卖阈值

    # KDJ 参数（标准9/3/3）
    KDJ_PERIOD = 9              # RSV 周期
    KDJ_K_SMOOTH = 3            # K 平滑周期
    KDJ_D_SMOOTH = 3            # D 平滑周期
    KDJ_OVERBOUGHT = 80         # 超买阈值
    KDJ_OVERSOLD = 20           # 超卖阈值

    # 布林带参数（标准20/2）
    BOLL_PERIOD = 20            # 中轨周期
    BOLL_STD_DEV = 2            # 标准差倍数
    BOLL_SQUEEZE_RATIO = 0.7    # 缩口判断：当前带宽 < 近期均值 * 此比例视为缩口
    
    def __init__(self):
        """初始化分析器"""
        pass
    
    def analyze(self, df: pd.DataFrame, code: str) -> TrendAnalysisResult:
        """
        分析股票趋势
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
            code: 股票代码
            
        Returns:
            TrendAnalysisResult 分析结果
        """
        result = TrendAnalysisResult(code=code)
        
        if df is None or df.empty or len(df) < 20:
            logger.warning(f"{code} 数据不足，无法进行趋势分析")
            result.risk_factors.append("数据不足，无法完成分析")
            return result
        
        # 确保数据按日期排序
        df = df.sort_values('date').reset_index(drop=True)
        
        # 计算均线
        df = self._calculate_mas(df)

        # 计算 MACD 和 RSI
        df = self._calculate_macd(df)
        df = self._calculate_rsi(df)
        df = self._calculate_kdj(df)
        df = self._calculate_bollinger(df)

        # 获取最新数据
        latest = df.iloc[-1]
        result.current_price = float(latest['close'])
        result.ma5 = float(latest['MA5'])
        result.ma10 = float(latest['MA10'])
        result.ma20 = float(latest['MA20'])
        result.ma60 = float(latest.get('MA60', 0))

        # 1. 趋势判断
        self._analyze_trend(df, result)

        # 2. 乖离率计算
        self._calculate_bias(result)

        # 3. 量能分析
        self._analyze_volume(df, result)

        # 4. 支撑压力分析
        self._analyze_support_resistance(df, result)

        # 5. MACD 分析
        self._analyze_macd(df, result)

        # 6. RSI 分析
        self._analyze_rsi(df, result)

        # 7. KDJ 分析
        self._analyze_kdj(df, result)

        # 8. 布林带分析
        self._analyze_bollinger(df, result)

        # 9. 生成买入信号
        self._generate_signal(result)

        return result
    
    def _calculate_mas(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算均线"""
        df = df.copy()
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        if len(df) >= 60:
            df['MA60'] = df['close'].rolling(window=60).mean()
        else:
            df['MA60'] = df['MA20']  # 数据不足时使用 MA20 替代
        return df

    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 MACD 指标

        公式：
        - EMA(12)：12日指数移动平均
        - EMA(26)：26日指数移动平均
        - DIF = EMA(12) - EMA(26)
        - DEA = EMA(DIF, 9)
        - MACD = (DIF - DEA) * 2
        """
        df = df.copy()

        # 计算快慢线 EMA
        ema_fast = df['close'].ewm(span=self.MACD_FAST, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.MACD_SLOW, adjust=False).mean()

        # 计算快线 DIF
        df['MACD_DIF'] = ema_fast - ema_slow

        # 计算信号线 DEA
        df['MACD_DEA'] = df['MACD_DIF'].ewm(span=self.MACD_SIGNAL, adjust=False).mean()

        # 计算柱状图
        df['MACD_BAR'] = (df['MACD_DIF'] - df['MACD_DEA']) * 2

        return df

    def _calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 RSI 指标

        公式：
        - RS = 平均上涨幅度 / 平均下跌幅度
        - RSI = 100 - (100 / (1 + RS))
        """
        df = df.copy()

        for period in [self.RSI_SHORT, self.RSI_MID, self.RSI_LONG]:
            # 计算价格变化
            delta = df['close'].diff()

            # 分离上涨和下跌
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # 计算平均涨跌幅
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()

            # 计算 RS 和 RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # 填充 NaN 值
            rsi = rsi.fillna(50)  # 默认中性值

            # 添加到 DataFrame
            col_name = f'RSI_{period}'
            df[col_name] = rsi

        return df
    
    def _analyze_trend(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析趋势状态
        
        核心逻辑：判断均线排列和趋势强度
        """
        ma5, ma10, ma20 = result.ma5, result.ma10, result.ma20
        
        # 判断均线排列
        if ma5 > ma10 > ma20:
            # 检查间距是否在扩大（强势）
            prev = df.iloc[-5] if len(df) >= 5 else df.iloc[-1]
            prev_spread = (prev['MA5'] - prev['MA20']) / prev['MA20'] * 100 if prev['MA20'] > 0 else 0
            curr_spread = (ma5 - ma20) / ma20 * 100 if ma20 > 0 else 0
            
            if curr_spread > prev_spread and curr_spread > 5:
                result.trend_status = TrendStatus.STRONG_BULL
                result.ma_alignment = "强势多头排列，均线发散上行"
                result.trend_strength = 90
            else:
                result.trend_status = TrendStatus.BULL
                result.ma_alignment = "多头排列 MA5>MA10>MA20"
                result.trend_strength = 75
                
        elif ma5 > ma10 and ma10 <= ma20:
            result.trend_status = TrendStatus.WEAK_BULL
            result.ma_alignment = "弱势多头，MA5>MA10 但 MA10≤MA20"
            result.trend_strength = 55
            
        elif ma5 < ma10 < ma20:
            prev = df.iloc[-5] if len(df) >= 5 else df.iloc[-1]
            prev_spread = (prev['MA20'] - prev['MA5']) / prev['MA5'] * 100 if prev['MA5'] > 0 else 0
            curr_spread = (ma20 - ma5) / ma5 * 100 if ma5 > 0 else 0
            
            if curr_spread > prev_spread and curr_spread > 5:
                result.trend_status = TrendStatus.STRONG_BEAR
                result.ma_alignment = "强势空头排列，均线发散下行"
                result.trend_strength = 10
            else:
                result.trend_status = TrendStatus.BEAR
                result.ma_alignment = "空头排列 MA5<MA10<MA20"
                result.trend_strength = 25
                
        elif ma5 < ma10 and ma10 >= ma20:
            result.trend_status = TrendStatus.WEAK_BEAR
            result.ma_alignment = "弱势空头，MA5<MA10 但 MA10≥MA20"
            result.trend_strength = 40
            
        else:
            result.trend_status = TrendStatus.CONSOLIDATION
            result.ma_alignment = "均线缠绕，趋势不明"
            result.trend_strength = 50
    
    def _calculate_bias(self, result: TrendAnalysisResult) -> None:
        """
        计算乖离率
        
        乖离率 = (现价 - 均线) / 均线 * 100%
        
        严进策略：乖离率超过 5% 不追高
        """
        price = result.current_price
        
        if result.ma5 > 0:
            result.bias_ma5 = (price - result.ma5) / result.ma5 * 100
        if result.ma10 > 0:
            result.bias_ma10 = (price - result.ma10) / result.ma10 * 100
        if result.ma20 > 0:
            result.bias_ma20 = (price - result.ma20) / result.ma20 * 100
    
    def _analyze_volume(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析量能
        
        偏好：缩量回调 > 放量上涨 > 缩量上涨 > 放量下跌
        """
        if len(df) < 5:
            return
        
        latest = df.iloc[-1]
        vol_5d_avg = df['volume'].iloc[-6:-1].mean()
        
        if vol_5d_avg > 0:
            result.volume_ratio_5d = float(latest['volume']) / vol_5d_avg
        
        # 判断价格变化
        prev_close = df.iloc[-2]['close']
        price_change = (latest['close'] - prev_close) / prev_close * 100
        
        # 量能状态判断
        if result.volume_ratio_5d >= self.VOLUME_HEAVY_RATIO:
            if price_change > 0:
                result.volume_status = VolumeStatus.HEAVY_VOLUME_UP
                result.volume_trend = "放量上涨，多头力量强劲"
            else:
                result.volume_status = VolumeStatus.HEAVY_VOLUME_DOWN
                result.volume_trend = "放量下跌，注意风险"
        elif result.volume_ratio_5d <= self.VOLUME_SHRINK_RATIO:
            if price_change > 0:
                result.volume_status = VolumeStatus.SHRINK_VOLUME_UP
                result.volume_trend = "缩量上涨，上攻动能不足"
            else:
                result.volume_status = VolumeStatus.SHRINK_VOLUME_DOWN
                result.volume_trend = "缩量回调，洗盘特征明显（好）"
        else:
            result.volume_status = VolumeStatus.NORMAL
            result.volume_trend = "量能正常"
    
    def _analyze_support_resistance(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析支撑压力位
        
        买点偏好：回踩 MA5/MA10 获得支撑
        """
        price = result.current_price
        
        # 检查是否在 MA5 附近获得支撑
        if result.ma5 > 0:
            ma5_distance = abs(price - result.ma5) / result.ma5
            if ma5_distance <= self.MA_SUPPORT_TOLERANCE and price >= result.ma5:
                result.support_ma5 = True
                result.support_levels.append(result.ma5)
        
        # 检查是否在 MA10 附近获得支撑
        if result.ma10 > 0:
            ma10_distance = abs(price - result.ma10) / result.ma10
            if ma10_distance <= self.MA_SUPPORT_TOLERANCE and price >= result.ma10:
                result.support_ma10 = True
                if result.ma10 not in result.support_levels:
                    result.support_levels.append(result.ma10)
        
        # MA20 作为重要支撑
        if result.ma20 > 0 and price >= result.ma20:
            result.support_levels.append(result.ma20)
        
        # 近期高点作为压力
        if len(df) >= 20:
            recent_high = df['high'].iloc[-20:].max()
            if recent_high > price:
                result.resistance_levels.append(recent_high)

    def _analyze_macd(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析 MACD 指标

        核心信号：
        - 零轴上金叉：最强买入信号
        - 金叉：DIF 上穿 DEA
        - 死叉：DIF 下穿 DEA
        """
        if len(df) < self.MACD_SLOW:
            result.macd_signal = "数据不足"
            return

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 获取 MACD 数据
        result.macd_dif = float(latest['MACD_DIF'])
        result.macd_dea = float(latest['MACD_DEA'])
        result.macd_bar = float(latest['MACD_BAR'])

        # 判断金叉死叉
        prev_dif_dea = prev['MACD_DIF'] - prev['MACD_DEA']
        curr_dif_dea = result.macd_dif - result.macd_dea

        # 金叉：DIF 上穿 DEA
        is_golden_cross = prev_dif_dea <= 0 and curr_dif_dea > 0

        # 死叉：DIF 下穿 DEA
        is_death_cross = prev_dif_dea >= 0 and curr_dif_dea < 0

        # 零轴穿越
        prev_zero = prev['MACD_DIF']
        curr_zero = result.macd_dif
        is_crossing_up = prev_zero <= 0 and curr_zero > 0
        is_crossing_down = prev_zero >= 0 and curr_zero < 0

        # 判断 MACD 状态
        if is_golden_cross and curr_zero > 0:
            result.macd_status = MACDStatus.GOLDEN_CROSS_ZERO
            result.macd_signal = "⭐ 零轴上金叉，强烈买入信号！"
        elif is_crossing_up:
            result.macd_status = MACDStatus.CROSSING_UP
            result.macd_signal = "⚡ DIF上穿零轴，趋势转强"
        elif is_golden_cross:
            result.macd_status = MACDStatus.GOLDEN_CROSS
            result.macd_signal = "✅ 金叉，趋势向上"
        elif is_death_cross:
            result.macd_status = MACDStatus.DEATH_CROSS
            result.macd_signal = "❌ 死叉，趋势向下"
        elif is_crossing_down:
            result.macd_status = MACDStatus.CROSSING_DOWN
            result.macd_signal = "⚠️ DIF下穿零轴，趋势转弱"
        elif result.macd_dif > 0 and result.macd_dea > 0:
            result.macd_status = MACDStatus.BULLISH
            result.macd_signal = "✓ 多头排列，持续上涨"
        elif result.macd_dif < 0 and result.macd_dea < 0:
            result.macd_status = MACDStatus.BEARISH
            result.macd_signal = "⚠ 空头排列，持续下跌"
        else:
            result.macd_status = MACDStatus.BULLISH
            result.macd_signal = " MACD 中性区域"

    def _analyze_rsi(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析 RSI 指标

        核心判断：
        - RSI > 70：超买，谨慎追高
        - RSI < 30：超卖，关注反弹
        - 40-60：中性区域
        """
        if len(df) < self.RSI_LONG:
            result.rsi_signal = "数据不足"
            return

        latest = df.iloc[-1]

        # 获取 RSI 数据
        result.rsi_6 = float(latest[f'RSI_{self.RSI_SHORT}'])
        result.rsi_12 = float(latest[f'RSI_{self.RSI_MID}'])
        result.rsi_24 = float(latest[f'RSI_{self.RSI_LONG}'])

        # 以中期 RSI(12) 为主进行判断
        rsi_mid = result.rsi_12

        # 判断 RSI 状态
        if rsi_mid > self.RSI_OVERBOUGHT:
            result.rsi_status = RSIStatus.OVERBOUGHT
            result.rsi_signal = f"⚠️ RSI超买({rsi_mid:.1f}>70)，短期回调风险高"
        elif rsi_mid > 60:
            result.rsi_status = RSIStatus.STRONG_BUY
            result.rsi_signal = f"✅ RSI强势({rsi_mid:.1f})，多头力量充足"
        elif rsi_mid >= 40:
            result.rsi_status = RSIStatus.NEUTRAL
            result.rsi_signal = f" RSI中性({rsi_mid:.1f})，震荡整理中"
        elif rsi_mid >= self.RSI_OVERSOLD:
            result.rsi_status = RSIStatus.WEAK
            result.rsi_signal = f"⚡ RSI弱势({rsi_mid:.1f})，关注反弹"
        else:
            result.rsi_status = RSIStatus.OVERSOLD
            result.rsi_signal = f"⭐ RSI超卖({rsi_mid:.1f}<30)，反弹机会大"

    def _calculate_kdj(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 KDJ 指标

        公式：
        - RSV = (Close - Low_N) / (High_N - Low_N) * 100
        - K = (2/3) * prev_K + (1/3) * RSV  （经典递推平滑）
        - D = (2/3) * prev_D + (1/3) * K
        - J = 3*K - 2*D

        使用 α=1/3 递推平滑（与同花顺、通达信一致），
        而非 pandas ewm 的 α=2/(span+1) 公式。
        """
        df = df.copy()
        n = self.KDJ_PERIOD

        # 计算 N 日内最低价和最高价
        low_n = df['low'].rolling(window=n, min_periods=n).min()
        high_n = df['high'].rolling(window=n, min_periods=n).max()

        # 计算 RSV
        diff = high_n - low_n
        rsv = np.where(diff > 0, (df['close'] - low_n) / diff * 100, 50.0)

        # 经典递推平滑：K = (2/3)*prev_K + (1/3)*RSV
        alpha = 1.0 / self.KDJ_K_SMOOTH  # 1/3
        k_values = np.full(len(rsv), 50.0)
        d_values = np.full(len(rsv), 50.0)

        for i in range(len(rsv)):
            if np.isnan(rsv[i]):
                k_values[i] = k_values[i - 1] if i > 0 else 50.0
            else:
                prev_k = k_values[i - 1] if i > 0 else 50.0
                k_values[i] = (1 - alpha) * prev_k + alpha * rsv[i]
            prev_d = d_values[i - 1] if i > 0 else 50.0
            d_values[i] = (1 - alpha) * prev_d + alpha * k_values[i]

        j_values = 3 * k_values - 2 * d_values

        df['KDJ_K'] = k_values
        df['KDJ_D'] = d_values
        df['KDJ_J'] = j_values

        return df

    def _calculate_bollinger(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算布林带指标

        公式：
        - 中轨 = MA(Close, N)     （N=20）
        - 上轨 = 中轨 + K * STD   （K=2）
        - 下轨 = 中轨 - K * STD
        """
        df = df.copy()
        n = self.BOLL_PERIOD
        k = self.BOLL_STD_DEV

        df['BOLL_MID'] = df['close'].rolling(window=n, min_periods=n).mean()
        std = df['close'].rolling(window=n, min_periods=n).std()
        df['BOLL_UPPER'] = df['BOLL_MID'] + k * std
        df['BOLL_LOWER'] = df['BOLL_MID'] - k * std

        return df

    def _analyze_kdj(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析 KDJ 指标

        核心信号：
        - J<0 超卖区金叉：强反弹信号
        - K/D<20 超卖：关注反弹
        - K/D>80 超买：注意回调
        - J>100 超买区死叉：强回调信号
        """
        if len(df) < self.KDJ_PERIOD + 1:
            result.kdj_signal = "数据不足"
            return

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        result.kdj_k = float(latest['KDJ_K'])
        result.kdj_d = float(latest['KDJ_D'])
        result.kdj_j = float(latest['KDJ_J'])

        # 判断金叉死叉（J 穿越 D）
        prev_j_d = prev['KDJ_J'] - prev['KDJ_D']
        curr_j_d = result.kdj_j - result.kdj_d
        is_golden_cross = prev_j_d <= 0 and curr_j_d > 0
        is_death_cross = prev_j_d >= 0 and curr_j_d < 0

        if is_golden_cross and result.kdj_k < self.KDJ_OVERSOLD:
            result.kdj_status = KDJStatus.GOLDEN_CROSS
            result.kdj_signal = f"⭐ 超卖区金叉(K={result.kdj_k:.1f})，强反弹信号！"
        elif is_golden_cross:
            result.kdj_status = KDJStatus.GOLDEN_CROSS
            result.kdj_signal = f"✅ KDJ金叉(K={result.kdj_k:.1f})，趋势向上"
        elif is_death_cross and result.kdj_k > self.KDJ_OVERBOUGHT:
            result.kdj_status = KDJStatus.DEATH_CROSS
            result.kdj_signal = f"❌ 超买区死叉(K={result.kdj_k:.1f})，强回调信号！"
        elif is_death_cross:
            result.kdj_status = KDJStatus.DEATH_CROSS
            result.kdj_signal = f"⚠️ KDJ死叉(K={result.kdj_k:.1f})，趋势向下"
        elif result.kdj_k > self.KDJ_OVERBOUGHT and result.kdj_d > self.KDJ_OVERBOUGHT:
            result.kdj_status = KDJStatus.OVERBOUGHT
            result.kdj_signal = f"⚠️ KDJ超买(K={result.kdj_k:.1f},D={result.kdj_d:.1f})，注意回调"
        elif result.kdj_k < self.KDJ_OVERSOLD and result.kdj_d < self.KDJ_OVERSOLD:
            result.kdj_status = KDJStatus.OVERSOLD
            result.kdj_signal = f"⭐ KDJ超卖(K={result.kdj_k:.1f},D={result.kdj_d:.1f})，关注反弹"
        elif result.kdj_k > result.kdj_d:
            result.kdj_status = KDJStatus.BULLISH
            result.kdj_signal = f"✓ KDJ多头(K={result.kdj_k:.1f}>D={result.kdj_d:.1f})"
        else:
            result.kdj_status = KDJStatus.BEARISH
            result.kdj_signal = f"⚠ KDJ空头(K={result.kdj_k:.1f}<D={result.kdj_d:.1f})"

    def _analyze_bollinger(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析布林带指标

        核心信号：
        - 价格突破上轨：超强势，但注意回调
        - 价格跌破下轨：超弱势，关注反弹
        - 布林带缩口：变盘信号，即将选择方向
        - 价格在中轨获得支撑：多头持续
        """
        if len(df) < self.BOLL_PERIOD:
            result.boll_signal = "数据不足"
            return

        latest = df.iloc[-1]

        # NaN 保护：数据有缺口时中轨可能为 NaN
        if pd.isna(latest['BOLL_MID']):
            result.boll_signal = "数据不足"
            return

        price = result.current_price

        result.boll_upper = float(latest['BOLL_UPPER'])
        result.boll_middle = float(latest['BOLL_MID'])
        result.boll_lower = float(latest['BOLL_LOWER'])

        # 计算带宽
        if result.boll_middle > 0:
            result.boll_width = (result.boll_upper - result.boll_lower) / result.boll_middle * 100

        # 计算价格在带中的位置（0=下轨, 100=上轨）
        band_range = result.boll_upper - result.boll_lower
        if band_range > 0:
            result.boll_position = (price - result.boll_lower) / band_range * 100
            result.boll_position = max(0, min(100, result.boll_position))

        # 检测缩口（比较当前带宽与近期平均带宽）
        is_squeeze = False
        if len(df) >= self.BOLL_PERIOD + 10:
            boll_widths = (df['BOLL_UPPER'] - df['BOLL_LOWER']) / df['BOLL_MID'] * 100
            avg_width = boll_widths.iloc[-10:-1].mean()
            if not pd.isna(avg_width) and avg_width > 0:
                is_squeeze = result.boll_width < avg_width * self.BOLL_SQUEEZE_RATIO

        # 判断布林带状态
        if price > result.boll_upper:
            result.boll_status = BollingerStatus.ABOVE_UPPER
            result.boll_signal = f"⚠️ 突破上轨({result.boll_upper:.2f})，超强势但注意回调"
        elif price < result.boll_lower:
            result.boll_status = BollingerStatus.BELOW_LOWER
            result.boll_signal = f"⭐ 跌破下轨({result.boll_lower:.2f})，超卖关注反弹"
        elif is_squeeze:
            result.boll_status = BollingerStatus.SQUEEZE
            result.boll_signal = f"⚡ 布林带缩口(带宽{result.boll_width:.1f}%)，即将变盘！"
        elif result.boll_position > 75:
            result.boll_status = BollingerStatus.NEAR_UPPER
            result.boll_signal = f"⚠ 接近上轨(位置{result.boll_position:.0f}%)，压力较大"
        elif result.boll_position < 25:
            result.boll_status = BollingerStatus.NEAR_LOWER
            result.boll_signal = f"✅ 接近下轨(位置{result.boll_position:.0f}%)，支撑区域"
        else:
            result.boll_status = BollingerStatus.MIDDLE
            result.boll_signal = f"✓ 中轨附近(位置{result.boll_position:.0f}%)，趋势中性"

    def _generate_signal(self, result: TrendAnalysisResult) -> None:
        """
        生成买入信号

        综合评分系统：
        - 趋势（25分）：多头排列得分高
        - 乖离率（15分）：接近 MA5 得分高
        - 量能（10分）：缩量回调得分高
        - 支撑（10分）：获得均线支撑得分高
        - MACD（15分）：金叉和多头得分高
        - RSI（8分）：超卖和强势得分高
        - KDJ（9分）：金叉和超卖得分高
        - 布林带（8分）：下轨支撑和缩口得分高
        """
        score = 0
        reasons = []
        risks = []

        # === 趋势评分（25分）===
        trend_scores = {
            TrendStatus.STRONG_BULL: 25,
            TrendStatus.BULL: 21,
            TrendStatus.WEAK_BULL: 15,
            TrendStatus.CONSOLIDATION: 10,
            TrendStatus.WEAK_BEAR: 6,
            TrendStatus.BEAR: 3,
            TrendStatus.STRONG_BEAR: 0,
        }
        trend_score = trend_scores.get(result.trend_status, 10)
        score += trend_score

        if result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL]:
            reasons.append(f"✅ {result.trend_status.value}，顺势做多")
        elif result.trend_status in [TrendStatus.BEAR, TrendStatus.STRONG_BEAR]:
            risks.append(f"⚠️ {result.trend_status.value}，不宜做多")

        # === 乖离率评分（15分）===
        bias = result.bias_ma5
        if bias < 0:
            # 价格在 MA5 下方（回调中）
            if bias > -3:
                score += 15
                reasons.append(f"✅ 价格略低于MA5({bias:.1f}%)，回踩买点")
            elif bias > -5:
                score += 12
                reasons.append(f"✅ 价格回踩MA5({bias:.1f}%)，观察支撑")
            else:
                score += 6
                risks.append(f"⚠️ 乖离率过大({bias:.1f}%)，可能破位")
        elif bias < 2:
            score += 14
            reasons.append(f"✅ 价格贴近MA5({bias:.1f}%)，介入好时机")
        elif bias < self.BIAS_THRESHOLD:
            score += 10
            reasons.append(f"⚡ 价格略高于MA5({bias:.1f}%)，可小仓介入")
        else:
            score += 3
            risks.append(f"❌ 乖离率过高({bias:.1f}%>5%)，严禁追高！")

        # === 量能评分（10分）===
        volume_scores = {
            VolumeStatus.SHRINK_VOLUME_DOWN: 10,  # 缩量回调最佳
            VolumeStatus.HEAVY_VOLUME_UP: 8,      # 放量上涨次之
            VolumeStatus.NORMAL: 6,
            VolumeStatus.SHRINK_VOLUME_UP: 4,     # 无量上涨较差
            VolumeStatus.HEAVY_VOLUME_DOWN: 0,    # 放量下跌最差
        }
        vol_score = volume_scores.get(result.volume_status, 8)
        score += vol_score

        if result.volume_status == VolumeStatus.SHRINK_VOLUME_DOWN:
            reasons.append("✅ 缩量回调，主力洗盘")
        elif result.volume_status == VolumeStatus.HEAVY_VOLUME_DOWN:
            risks.append("⚠️ 放量下跌，注意风险")

        # === 支撑评分（10分）===
        if result.support_ma5:
            score += 5
            reasons.append("✅ MA5支撑有效")
        if result.support_ma10:
            score += 5
            reasons.append("✅ MA10支撑有效")

        # === MACD 评分（15分）===
        macd_scores = {
            MACDStatus.GOLDEN_CROSS_ZERO: 15,  # 零轴上金叉最强
            MACDStatus.GOLDEN_CROSS: 12,      # 金叉
            MACDStatus.CROSSING_UP: 10,       # 上穿零轴
            MACDStatus.BULLISH: 8,            # 多头
            MACDStatus.BEARISH: 2,            # 空头
            MACDStatus.CROSSING_DOWN: 0,       # 下穿零轴
            MACDStatus.DEATH_CROSS: 0,        # 死叉
        }
        macd_score = macd_scores.get(result.macd_status, 5)
        score += macd_score

        if result.macd_status in [MACDStatus.GOLDEN_CROSS_ZERO, MACDStatus.GOLDEN_CROSS]:
            reasons.append(result.macd_signal)
        elif result.macd_status in [MACDStatus.DEATH_CROSS, MACDStatus.CROSSING_DOWN]:
            risks.append(result.macd_signal)
        else:
            reasons.append(result.macd_signal)

        # === RSI 评分（8分）===
        rsi_scores = {
            RSIStatus.OVERSOLD: 8,        # 超卖最佳
            RSIStatus.STRONG_BUY: 6,     # 强势
            RSIStatus.NEUTRAL: 4,        # 中性
            RSIStatus.WEAK: 2,            # 弱势
            RSIStatus.OVERBOUGHT: 0,       # 超买最差
        }
        rsi_score = rsi_scores.get(result.rsi_status, 4)
        score += rsi_score

        if result.rsi_status in [RSIStatus.OVERSOLD, RSIStatus.STRONG_BUY]:
            reasons.append(result.rsi_signal)
        elif result.rsi_status == RSIStatus.OVERBOUGHT:
            risks.append(result.rsi_signal)
        else:
            reasons.append(result.rsi_signal)

        # === KDJ 评分（9分）===
        kdj_scores = {
            KDJStatus.GOLDEN_CROSS: 9,    # 金叉最佳
            KDJStatus.OVERSOLD: 7,        # 超卖
            KDJStatus.BULLISH: 5,         # 多头
            KDJStatus.BEARISH: 2,         # 空头
            KDJStatus.OVERBOUGHT: 1,      # 超买
            KDJStatus.DEATH_CROSS: 0,     # 死叉最差
        }
        kdj_score = kdj_scores.get(result.kdj_status, 4)
        score += kdj_score

        if result.kdj_status in [KDJStatus.GOLDEN_CROSS, KDJStatus.OVERSOLD]:
            reasons.append(result.kdj_signal)
        elif result.kdj_status in [KDJStatus.DEATH_CROSS, KDJStatus.OVERBOUGHT]:
            risks.append(result.kdj_signal)
        else:
            reasons.append(result.kdj_signal)

        # === 布林带评分（8分）===
        boll_scores = {
            BollingerStatus.NEAR_LOWER: 8,     # 下轨支撑最佳
            BollingerStatus.BELOW_LOWER: 7,    # 跌破下轨（超卖反弹）
            BollingerStatus.SQUEEZE: 6,        # 缩口变盘
            BollingerStatus.MIDDLE: 4,         # 中轨附近
            BollingerStatus.NEAR_UPPER: 2,     # 接近上轨
            BollingerStatus.ABOVE_UPPER: 1,    # 突破上轨
        }
        boll_score = boll_scores.get(result.boll_status, 4)
        score += boll_score

        if result.boll_status in [BollingerStatus.NEAR_LOWER, BollingerStatus.BELOW_LOWER]:
            reasons.append(result.boll_signal)
        elif result.boll_status == BollingerStatus.SQUEEZE:
            reasons.append(result.boll_signal)
        elif result.boll_status in [BollingerStatus.ABOVE_UPPER, BollingerStatus.NEAR_UPPER]:
            risks.append(result.boll_signal)
        else:
            reasons.append(result.boll_signal)

        # === 综合判断 ===
        result.signal_score = score
        result.signal_reasons = reasons
        result.risk_factors = risks

        # 生成买入信号（调整阈值以适应新的100分制）
        if score >= 75 and result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL]:
            result.buy_signal = BuySignal.STRONG_BUY
        elif score >= 60 and result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL, TrendStatus.WEAK_BULL]:
            result.buy_signal = BuySignal.BUY
        elif score >= 45:
            result.buy_signal = BuySignal.HOLD
        elif score >= 30:
            result.buy_signal = BuySignal.WAIT
        elif result.trend_status in [TrendStatus.BEAR, TrendStatus.STRONG_BEAR]:
            result.buy_signal = BuySignal.STRONG_SELL
        else:
            result.buy_signal = BuySignal.SELL
    
    def format_analysis(self, result: TrendAnalysisResult) -> str:
        """
        格式化分析结果为文本

        Args:
            result: 分析结果

        Returns:
            格式化的分析文本
        """
        lines = [
            f"=== {result.code} 趋势分析 ===",
            f"",
            f"📊 趋势判断: {result.trend_status.value}",
            f"   均线排列: {result.ma_alignment}",
            f"   趋势强度: {result.trend_strength}/100",
            f"",
            f"📈 均线数据:",
            f"   现价: {result.current_price:.2f}",
            f"   MA5:  {result.ma5:.2f} (乖离 {result.bias_ma5:+.2f}%)",
            f"   MA10: {result.ma10:.2f} (乖离 {result.bias_ma10:+.2f}%)",
            f"   MA20: {result.ma20:.2f} (乖离 {result.bias_ma20:+.2f}%)",
            f"",
            f"📊 量能分析: {result.volume_status.value}",
            f"   量比(vs5日): {result.volume_ratio_5d:.2f}",
            f"   量能趋势: {result.volume_trend}",
            f"",
            f"📈 MACD指标: {result.macd_status.value}",
            f"   DIF: {result.macd_dif:.4f}",
            f"   DEA: {result.macd_dea:.4f}",
            f"   MACD: {result.macd_bar:.4f}",
            f"   信号: {result.macd_signal}",
            f"",
            f"📊 RSI指标: {result.rsi_status.value}",
            f"   RSI(6): {result.rsi_6:.1f}",
            f"   RSI(12): {result.rsi_12:.1f}",
            f"   RSI(24): {result.rsi_24:.1f}",
            f"   信号: {result.rsi_signal}",
            f"",
            f"📈 KDJ指标: {result.kdj_status.value}",
            f"   K: {result.kdj_k:.1f}",
            f"   D: {result.kdj_d:.1f}",
            f"   J: {result.kdj_j:.1f}",
            f"   信号: {result.kdj_signal}",
            f"",
            f"📊 布林带: {result.boll_status.value}",
            f"   上轨: {result.boll_upper:.2f}",
            f"   中轨: {result.boll_middle:.2f}",
            f"   下轨: {result.boll_lower:.2f}",
            f"   带宽: {result.boll_width:.1f}%  位置: {result.boll_position:.0f}%",
            f"   信号: {result.boll_signal}",
            f"",
            f"🎯 操作建议: {result.buy_signal.value}",
            f"   综合评分: {result.signal_score}/100",
        ]

        if result.signal_reasons:
            lines.append(f"")
            lines.append(f"✅ 买入理由:")
            for reason in result.signal_reasons:
                lines.append(f"   {reason}")

        if result.risk_factors:
            lines.append(f"")
            lines.append(f"⚠️ 风险因素:")
            for risk in result.risk_factors:
                lines.append(f"   {risk}")

        return "\n".join(lines)


def analyze_stock(df: pd.DataFrame, code: str) -> TrendAnalysisResult:
    """
    便捷函数：分析单只股票
    
    Args:
        df: 包含 OHLCV 数据的 DataFrame
        code: 股票代码
        
    Returns:
        TrendAnalysisResult 分析结果
    """
    analyzer = StockTrendAnalyzer()
    return analyzer.analyze(df, code)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 模拟数据测试
    import numpy as np
    
    dates = pd.date_range(start='2025-01-01', periods=60, freq='D')
    np.random.seed(42)
    
    # 模拟多头排列的数据
    base_price = 10.0
    prices = [base_price]
    for i in range(59):
        change = np.random.randn() * 0.02 + 0.003  # 轻微上涨趋势
        prices.append(prices[-1] * (1 + change))
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
        'low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000000, 5000000) for _ in prices],
    })
    
    analyzer = StockTrendAnalyzer()
    result = analyzer.analyze(df, '000001')
    print(analyzer.format_analysis(result))
