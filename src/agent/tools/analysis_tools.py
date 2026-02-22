# -*- coding: utf-8 -*-
"""
Analysis tools — wraps StockTrendAnalyzer as an agent-callable tool.

Tools:
- analyze_trend: comprehensive technical trend analysis
"""

import logging
from typing import Optional

from src.agent.tools.registry import ToolParameter, ToolDefinition

logger = logging.getLogger(__name__)


def _handle_analyze_trend(stock_code: str) -> dict:
    """Run technical trend analysis on a stock."""
    from src.stock_analyzer import StockTrendAnalyzer
    from src.storage import get_db

    db = get_db()
    analyzer = StockTrendAnalyzer()

    # Fetch raw data from DB context
    context = db.get_analysis_context(stock_code)
    if context is None or "raw_data" not in context:
        return {"error": f"No historical data available for trend analysis on {stock_code}"}

    raw_data = context["raw_data"]
    if not isinstance(raw_data, list) or len(raw_data) < 5:
        return {"error": f"Insufficient data for trend analysis on {stock_code} (need >= 5 days)"}

    import pandas as pd
    df = pd.DataFrame(raw_data)

    result = analyzer.analyze(df, stock_code)

    return {
        "code": result.code,
        "trend_status": result.trend_status.value,
        "ma_alignment": result.ma_alignment,
        "trend_strength": result.trend_strength,
        "ma5": result.ma5,
        "ma10": result.ma10,
        "ma20": result.ma20,
        "ma60": result.ma60,
        "current_price": result.current_price,
        "bias_ma5": round(result.bias_ma5, 2),
        "bias_ma10": round(result.bias_ma10, 2),
        "bias_ma20": round(result.bias_ma20, 2),
        "volume_status": result.volume_status.value,
        "volume_ratio_5d": round(result.volume_ratio_5d, 2),
        "volume_trend": result.volume_trend,
        "support_ma5": result.support_ma5,
        "support_ma10": result.support_ma10,
        "resistance_levels": result.resistance_levels,
        "support_levels": result.support_levels,
        "macd_dif": round(result.macd_dif, 4),
        "macd_dea": round(result.macd_dea, 4),
        "macd_bar": round(result.macd_bar, 4),
        "macd_status": result.macd_status.value,
        "macd_signal": result.macd_signal,
        "rsi_6": round(result.rsi_6, 2),
        "rsi_12": round(result.rsi_12, 2),
        "rsi_24": round(result.rsi_24, 2),
        "rsi_status": result.rsi_status.value,
        "rsi_signal": result.rsi_signal,
        "buy_signal": result.buy_signal.value,
        "signal_score": result.signal_score,
        "signal_reasons": result.signal_reasons,
        "risk_factors": result.risk_factors,
    }


analyze_trend_tool = ToolDefinition(
    name="analyze_trend",
    description="Run comprehensive technical trend analysis on a stock. "
                "Returns MA alignment, bias rates, MACD status, RSI levels, "
                "volume analysis, support/resistance levels, and a buy/sell signal "
                "with a score (0-100). Requires historical data in the database.",
    parameters=[
        ToolParameter(
            name="stock_code",
            type="string",
            description="Stock code to analyze, e.g., '600519'",
        ),
    ],
    handler=_handle_analyze_trend,
    category="analysis",
)


ALL_ANALYSIS_TOOLS = [
    analyze_trend_tool,
]
