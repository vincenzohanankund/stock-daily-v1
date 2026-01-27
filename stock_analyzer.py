"""
===================================
趋势交易分析器 - 基于交易理念（引入结构/供需）
===================================

交易理念核心原则：
1. 严进策略 - 不追高，追求每笔交易成功率
2. 趋势交易 - MA5>MA10>MA20 多头排列，顺势而为
3. 结构优先 - 关注箱体突破/回踩位置
4. 量价行为 - 努力/结果识别出货嫌疑
5. 相对强弱 - 只在强于大盘时给强信号
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class TrendStatus(Enum):
    """趋势状态枚举"""

    STRONG_BULL = "强势多头"
    BULL = "多头趋势"
    WEAK_BULL = "弱势多头"
    CONSOLIDATION = "震荡整理"
    WEAK_BEAR = "弱势空头"
    BEAR = "空头趋势"
    STRONG_BEAR = "强势空头"


class VolumeStatus(Enum):
    """量能状态枚举"""

    SHRINK_VOLUME_DOWN = "缩量回调"
    SHRINK_VOLUME_UP = "缩量上涨"
    HEAVY_VOLUME_UP = "放量上涨"
    HEAVY_VOLUME_DOWN = "放量下跌"
    NORMAL = "量能正常"


class BuySignal(Enum):
    """买入信号枚举"""

    STRONG_BUY = "突破买入"
    BUY = "回踩确认"
    HOLD = "持有"
    WAIT = "观望"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"


@dataclass
class TrendAnalysisResult:
    """趋势分析结果"""

    code: str
    current_price: float = 0.0

    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma_alignment: str = "未知"
    trend_status: TrendStatus = TrendStatus.CONSOLIDATION
    trend_strength: int = 50

    bias_ma5: float = 0.0
    bias_ma10: float = 0.0
    bias_ma20: float = 0.0

    volume_ratio_5d: float = 1.0
    volume_status: VolumeStatus = VolumeStatus.NORMAL
    volume_trend: str = "量能正常"

    support_ma5: bool = False
    support_ma10: bool = False
    resistance_levels: List[float] = field(default_factory=list)
    support_levels: List[float] = field(default_factory=list)

    structure_high: float = 0.0
    structure_low: float = 0.0
    structure_signal: str = ""
    structure_distance_pct: float = 0.0

    effort_ratio: float = 0.0
    result_body_pct: float = 0.0
    effort_result_flag: str = ""

    market_change_pct: Optional[float] = None
    stock_change_pct: Optional[float] = None
    relative_strength: Optional[float] = None
    rs_status: str = ""

    buy_signal: BuySignal = BuySignal.WAIT
    signal_score: int = 50
    signal_reasons: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "current_price": self.current_price,
            "ma5": self.ma5,
            "ma10": self.ma10,
            "ma20": self.ma20,
            "ma_alignment": self.ma_alignment,
            "trend_status": self.trend_status.value,
            "trend_strength": self.trend_strength,
            "bias_ma5": self.bias_ma5,
            "bias_ma10": self.bias_ma10,
            "bias_ma20": self.bias_ma20,
            "volume_ratio_5d": self.volume_ratio_5d,
            "volume_status": self.volume_status.value,
            "volume_trend": self.volume_trend,
            "support_ma5": self.support_ma5,
            "support_ma10": self.support_ma10,
            "support_levels": self.support_levels,
            "resistance_levels": self.resistance_levels,
            "structure_high": self.structure_high,
            "structure_low": self.structure_low,
            "structure_signal": self.structure_signal,
            "structure_distance_pct": self.structure_distance_pct,
            "effort_ratio": self.effort_ratio,
            "result_body_pct": self.result_body_pct,
            "effort_result_flag": self.effort_result_flag,
            "market_change_pct": self.market_change_pct,
            "stock_change_pct": self.stock_change_pct,
            "relative_strength": self.relative_strength,
            "rs_status": self.rs_status,
            "buy_signal": self.buy_signal.value,
            "signal_score": self.signal_score,
            "signal_reasons": self.signal_reasons,
            "risk_factors": self.risk_factors,
        }


class StockTrendAnalyzer:
    """趋势分析器"""

    BIAS_THRESHOLD = 5.0
    VOLUME_SHRINK_RATIO = 0.7
    VOLUME_HEAVY_RATIO = 1.5
    MA_SUPPORT_TOLERANCE = 0.02
    STRUCTURE_LOOKBACK = 60
    STRUCTURE_BREAKOUT_TOLERANCE = 0.005
    STRUCTURE_OVERBOUGHT_PCT = 20.0
    EFFORT_HEAVY_RATIO = 2.0
    RESULT_SMALL_BODY_PCT = 0.5

    def analyze(
        self,
        df: pd.DataFrame,
        code: str,
        market_change_pct: Optional[float] = None,
    ) -> TrendAnalysisResult:
        result = TrendAnalysisResult(code=code)
        if df is None or df.empty:
            return result

        df = df.copy()
        if "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)

        for col in ("open", "high", "low", "close", "volume"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "close" not in df.columns:
            return result

        df = df.dropna(subset=["close"])
        if df.empty:
            return result

        result.current_price = float(df.iloc[-1]["close"])

        df["ma5"] = df["close"].rolling(window=5, min_periods=1).mean()
        df["ma10"] = df["close"].rolling(window=10, min_periods=1).mean()
        df["ma20"] = df["close"].rolling(window=20, min_periods=1).mean()

        result.ma5 = float(df.iloc[-1]["ma5"])
        result.ma10 = float(df.iloc[-1]["ma10"])
        result.ma20 = float(df.iloc[-1]["ma20"])

        self._analyze_trend(result)
        self._calculate_bias(result)
        self._analyze_volume(df, result)
        self._analyze_support_resistance(df, result)
        self._analyze_structure(df, result)
        self._analyze_effort_result(df, result)
        self._analyze_relative_strength(df, result, market_change_pct)
        self._generate_signal(result)

        return result

    def _analyze_trend(self, result: TrendAnalysisResult) -> None:
        ma5, ma10, ma20 = result.ma5, result.ma10, result.ma20
        if ma5 > ma10 > ma20:
            result.trend_status = TrendStatus.STRONG_BULL
            result.ma_alignment = "MA5>MA10>MA20"
            result.trend_strength = 85
        elif ma5 > ma10 and ma10 <= ma20:
            result.trend_status = TrendStatus.WEAK_BULL
            result.ma_alignment = "MA5>MA10, MA10<=MA20"
            result.trend_strength = 65
        elif ma5 < ma10 < ma20:
            result.trend_status = TrendStatus.STRONG_BEAR
            result.ma_alignment = "MA5<MA10<MA20"
            result.trend_strength = 20
        else:
            result.trend_status = TrendStatus.CONSOLIDATION
            result.ma_alignment = "均线缠绕"
            result.trend_strength = 50

    def _calculate_bias(self, result: TrendAnalysisResult) -> None:
        price = result.current_price
        if result.ma5 > 0:
            result.bias_ma5 = (price - result.ma5) / result.ma5 * 100
        if result.ma10 > 0:
            result.bias_ma10 = (price - result.ma10) / result.ma10 * 100
        if result.ma20 > 0:
            result.bias_ma20 = (price - result.ma20) / result.ma20 * 100

    def _analyze_volume(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        if "volume" not in df.columns or len(df) < 5:
            return

        latest = df.iloc[-1]
        vol_5d_avg = df["volume"].iloc[-6:-1].mean()
        if vol_5d_avg and vol_5d_avg > 0:
            result.volume_ratio_5d = float(latest["volume"]) / vol_5d_avg

        prev_close = df.iloc[-2]["close"] if len(df) > 1 else latest["close"]
        price_change = (latest["close"] - prev_close) / prev_close * 100

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

    def _analyze_support_resistance(
        self, df: pd.DataFrame, result: TrendAnalysisResult
    ) -> None:
        price = result.current_price
        if result.ma5 > 0:
            ma5_distance = abs(price - result.ma5) / result.ma5
            if ma5_distance <= self.MA_SUPPORT_TOLERANCE and price >= result.ma5:
                result.support_ma5 = True
                result.support_levels.append(result.ma5)

        if result.ma10 > 0:
            ma10_distance = abs(price - result.ma10) / result.ma10
            if ma10_distance <= self.MA_SUPPORT_TOLERANCE and price >= result.ma10:
                result.support_ma10 = True
                if result.ma10 not in result.support_levels:
                    result.support_levels.append(result.ma10)

        if result.ma20 > 0 and price >= result.ma20:
            result.support_levels.append(result.ma20)

        if "high" in df.columns and len(df) >= 20:
            recent_high = df["high"].iloc[-20:].max()
            if recent_high > price:
                result.resistance_levels.append(float(recent_high))

    def _analyze_structure(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        if "high" not in df.columns or "low" not in df.columns:
            return
        lookback = min(len(df), self.STRUCTURE_LOOKBACK)
        if lookback < 10:
            return

        recent = df.iloc[-lookback:]
        structure_high = float(recent["high"].max())
        structure_low = float(recent["low"].min())
        result.structure_high = structure_high
        result.structure_low = structure_low

        if structure_high > 0:
            result.structure_distance_pct = (
                (result.current_price - structure_high) / structure_high * 100
            )

        prev_close = df.iloc[-2]["close"] if len(df) > 1 else result.current_price
        breakout_line = structure_high * (1 + self.STRUCTURE_BREAKOUT_TOLERANCE)
        near_top = (
            structure_high > 0
            and abs(result.current_price - structure_high) / structure_high <= 0.02
        )

        if result.current_price >= structure_high * (
            1 + self.STRUCTURE_OVERBOUGHT_PCT / 100
        ):
            result.structure_signal = "追高风险"
        elif prev_close <= structure_high and result.current_price > breakout_line:
            result.structure_signal = "突破买入"
        elif near_top and result.volume_ratio_5d <= 1.0:
            result.structure_signal = "回踩确认"
        elif near_top and result.volume_ratio_5d >= self.VOLUME_HEAVY_RATIO:
            result.structure_signal = "可能供给"
        else:
            result.structure_signal = "箱体内震荡"

    def _analyze_effort_result(
        self, df: pd.DataFrame, result: TrendAnalysisResult
    ) -> None:
        if not all(col in df.columns for col in ("open", "high", "close")):
            return
        latest = df.iloc[-1]
        close_price = float(latest["close"])
        if close_price <= 0:
            return

        body = abs(float(latest["close"]) - float(latest["open"]))
        result.result_body_pct = body / close_price * 100
        result.effort_ratio = result.volume_ratio_5d

        upper_shadow = float(latest["high"]) - max(
            float(latest["open"]), float(latest["close"])
        )
        upper_shadow_pct = upper_shadow / close_price * 100

        if (
            result.effort_ratio >= self.EFFORT_HEAVY_RATIO
            and result.result_body_pct <= self.RESULT_SMALL_BODY_PCT
            and upper_shadow_pct >= 0.8
        ):
            result.effort_result_flag = "出货嫌疑"
        else:
            result.effort_result_flag = "正常"

    def _analyze_relative_strength(
        self,
        df: pd.DataFrame,
        result: TrendAnalysisResult,
        market_change_pct: Optional[float],
    ) -> None:
        if len(df) < 2:
            return

        prev_close = float(df.iloc[-2]["close"])
        if prev_close <= 0:
            return

        result.stock_change_pct = (result.current_price - prev_close) / prev_close * 100
        result.market_change_pct = market_change_pct

        if market_change_pct is None:
            return

        result.relative_strength = result.stock_change_pct - market_change_pct
        result.rs_status = "RS强" if result.relative_strength > 0 else "RS弱"

    def _generate_signal(self, result: TrendAnalysisResult) -> None:
        score = 0
        reasons: List[str] = []
        risks: List[str] = []

        trend_scores = {
            TrendStatus.STRONG_BULL: 30,
            TrendStatus.BULL: 26,
            TrendStatus.WEAK_BULL: 20,
            TrendStatus.CONSOLIDATION: 12,
            TrendStatus.WEAK_BEAR: 8,
            TrendStatus.BEAR: 4,
            TrendStatus.STRONG_BEAR: 0,
        }
        score += trend_scores.get(result.trend_status, 12)

        if result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL]:
            reasons.append(f"✅ {result.trend_status.value}，顺势做多")
        elif result.trend_status in [TrendStatus.BEAR, TrendStatus.STRONG_BEAR]:
            risks.append(f"⚠️ {result.trend_status.value}，不宜做多")

        bias = result.bias_ma5
        if bias < 0:
            if bias > -3:
                score += 25
                reasons.append(f"✅ 价格略低于MA5({bias:.1f}%)，回踩买点")
            elif bias > -5:
                score += 20
                reasons.append(f"✅ 价格回踩MA5({bias:.1f}%)，观察支撑")
            else:
                score += 8
                risks.append(f"⚠️ 乖离率过大({bias:.1f}%)，可能破位")
        elif bias < 2:
            score += 23
            reasons.append(f"✅ 价格贴近MA5({bias:.1f}%)，介入好时机")
        elif bias < self.BIAS_THRESHOLD:
            score += 16
            reasons.append(f"⚡ 价格略高于MA5({bias:.1f}%)，可小仓介入")
        else:
            score += 4
            risks.append(f"❌ 乖离率过高({bias:.1f}%>5%)，严禁追高！")

        volume_scores = {
            VolumeStatus.SHRINK_VOLUME_DOWN: 15,
            VolumeStatus.HEAVY_VOLUME_UP: 10,
            VolumeStatus.NORMAL: 8,
            VolumeStatus.SHRINK_VOLUME_UP: 5,
            VolumeStatus.HEAVY_VOLUME_DOWN: 0,
        }
        score += volume_scores.get(result.volume_status, 8)

        if result.volume_status == VolumeStatus.SHRINK_VOLUME_DOWN:
            reasons.append("✅ 缩量回调，主力洗盘")
        elif result.volume_status == VolumeStatus.HEAVY_VOLUME_DOWN:
            risks.append("⚠️ 放量下跌，注意风险")

        if result.support_ma5:
            score += 5
            reasons.append("✅ MA5支撑有效")
        if result.support_ma10:
            score += 5
            reasons.append("✅ MA10支撑有效")

        if result.structure_signal == "突破买入":
            score += 12
            reasons.append("✅ 突破箱体上沿")
        elif result.structure_signal == "回踩确认":
            score += 10
            reasons.append("✅ 回踩箱顶确认")
        elif result.structure_signal == "追高风险":
            score -= 20
            risks.append("⚠️ 远离箱体上沿，追高风险")
        elif result.structure_signal == "可能供给":
            score -= 25
            risks.append("⚠️ 高位放量滞涨，供给增加")

        if result.effort_result_flag == "出货嫌疑":
            score -= 30
            risks.append("❌ 巨量小实体，主力出货嫌疑")

        if result.relative_strength is not None:
            if result.relative_strength > 0:
                score += 5
                reasons.append("✅ 相对强弱占优")
            else:
                score -= 10
                risks.append("⚠️ 相对强弱偏弱")

        result.signal_score = max(0, min(100, score))
        result.signal_reasons = reasons
        result.risk_factors = risks

        if result.effort_result_flag == "出货嫌疑":
            result.buy_signal = BuySignal.SELL
            return

        if result.structure_signal in ["追高风险", "可能供给"]:
            result.buy_signal = BuySignal.WAIT
            return

        if (
            score >= 80
            and result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL]
            and result.structure_signal in ["突破买入", "回踩确认"]
            and (result.relative_strength is None or result.relative_strength > 0)
        ):
            result.buy_signal = BuySignal.STRONG_BUY
        elif score >= 65 and result.trend_status in [
            TrendStatus.STRONG_BULL,
            TrendStatus.BULL,
            TrendStatus.WEAK_BULL,
        ]:
            result.buy_signal = BuySignal.BUY
        elif score >= 50:
            result.buy_signal = BuySignal.HOLD
        elif score >= 35:
            result.buy_signal = BuySignal.WAIT
        elif result.trend_status in [TrendStatus.BEAR, TrendStatus.STRONG_BEAR]:
            result.buy_signal = BuySignal.STRONG_SELL
        else:
            result.buy_signal = BuySignal.SELL

    def format_analysis(self, result: TrendAnalysisResult) -> str:
        lines = [
            f"=== {result.code} 趋势分析 ===",
            "",
            f"📊 趋势判断: {result.trend_status.value}",
            f"   均线排列: {result.ma_alignment}",
            f"   趋势强度: {result.trend_strength}/100",
            "",
            "📈 均线数据:",
            f"   现价: {result.current_price:.2f}",
            f"   MA5:  {result.ma5:.2f} (乖离 {result.bias_ma5:+.2f}%)",
            f"   MA10: {result.ma10:.2f} (乖离 {result.bias_ma10:+.2f}%)",
            f"   MA20: {result.ma20:.2f} (乖离 {result.bias_ma20:+.2f}%)",
            "",
            f"📊 量能分析: {result.volume_status.value}",
            f"   量比(vs5日): {result.volume_ratio_5d:.2f}",
            f"   量能趋势: {result.volume_trend}",
            "",
            f"🏗️ 结构扫描: {result.structure_signal}",
            f"   箱体区间: {result.structure_low:.2f}-{result.structure_high:.2f}",
            f"   距离箱顶: {result.structure_distance_pct:+.2f}%",
            "",
            f"⚖️ 努力/结果: {result.effort_result_flag}",
            f"   Effort: {result.effort_ratio:.2f} | Result: {result.result_body_pct:.2f}%",
            "",
            (
                f"📌 相对强弱: {result.rs_status} ({result.relative_strength:+.2f}%)"
                if result.relative_strength is not None
                else "📌 相对强弱: 未知"
            ),
            "",
            f"🎯 操作建议: {result.buy_signal.value}",
            f"   综合评分: {result.signal_score}/100",
        ]

        if result.signal_reasons:
            lines.append("")
            lines.append("✅ 买入理由:")
            for reason in result.signal_reasons:
                lines.append(f"   {reason}")

        if result.risk_factors:
            lines.append("")
            lines.append("⚠️ 风险因素:")
            for risk in result.risk_factors:
                lines.append(f"   {risk}")

        return "\n".join(lines)


def analyze_stock(df: pd.DataFrame, code: str) -> TrendAnalysisResult:
    analyzer = StockTrendAnalyzer()
    return analyzer.analyze(df, code)
