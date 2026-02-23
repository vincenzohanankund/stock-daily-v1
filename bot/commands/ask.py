# -*- coding: utf-8 -*-
"""
Ask command - analyze a stock using a specific Agent strategy.

Usage:
    /ask 600519                        -> Analyze with default strategy
    /ask 600519 用缠论分析              -> Parse strategy from message
    /ask 600519 chan_theory             -> Specify strategy id directly
"""

import re
import logging
import uuid
from typing import List, Optional

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse
from data_provider.base import canonical_stock_code
from src.config import get_config

logger = logging.getLogger(__name__)

# Strategy name to id mapping (CN name -> strategy id)
STRATEGY_NAME_MAP = {
    "缠论": "chan_theory",
    "缠论分析": "chan_theory",
    "波浪": "wave_theory",
    "波浪理论": "wave_theory",
    "艾略特": "wave_theory",
    "箱体": "box_oscillation",
    "箱体震荡": "box_oscillation",
    "情绪": "emotion_cycle",
    "情绪周期": "emotion_cycle",
    "趋势": "bull_trend",
    "多头趋势": "bull_trend",
    "均线金叉": "ma_golden_cross",
    "金叉": "ma_golden_cross",
    "缩量回踩": "shrink_pullback",
    "回踩": "shrink_pullback",
    "放量突破": "volume_breakout",
    "突破": "volume_breakout",
    "地量见底": "bottom_volume",
    "龙头": "dragon_head",
    "龙头战法": "dragon_head",
    "一阳穿三阴": "one_yang_three_yin",
}


class AskCommand(BotCommand):
    """
    Ask command handler - invoke Agent with a specific strategy to analyze a stock.

    Usage:
        /ask 600519                    -> Analyze with default strategy (bull_trend)
        /ask 600519 用缠论分析          -> Automatically selects chan_theory strategy
        /ask 600519 chan_theory         -> Directly specify strategy id
        /ask hk00700 波浪理论看看       -> HK stock with wave_theory
    """

    @property
    def name(self) -> str:
        return "ask"

    @property
    def aliases(self) -> List[str]:
        return ["问股"]

    @property
    def description(self) -> str:
        return "使用 Agent 策略分析股票"

    @property
    def usage(self) -> str:
        return "/ask <股票代码> [策略名称]"

    def validate_args(self, args: List[str]) -> Optional[str]:
        """Validate arguments."""
        if not args:
            return "请输入股票代码。用法: /ask <股票代码> [策略名称]\n示例: /ask 600519 用缠论分析"

        code = args[0].upper()
        is_a_stock = re.match(r"^\d{6}$", code)
        is_hk_stock = re.match(r"^HK\d{5}$", code)
        is_us_stock = re.match(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?$", code)

        if not (is_a_stock or is_hk_stock or is_us_stock):
            return f"无效的股票代码: {code}（A股6位数字 / 港股HK+5位数字 / 美股1-5个字母）"

        return None

    def _parse_strategy(self, args: List[str]) -> str:
        """Parse strategy from arguments, returning strategy id."""
        if len(args) < 2:
            return "bull_trend"

        # Join remaining args as the strategy text
        strategy_text = " ".join(args[1:]).strip()

        # Try direct strategy id match first
        from src.agent.skills.base import SkillManager

        try:
            sm = SkillManager()
            sm.load_builtin_strategies()
            available_ids = [s.name for s in sm.list_skills()]
            if strategy_text in available_ids:
                return strategy_text
        except Exception:
            pass

        # Try CN name mapping
        for cn_name, strategy_id in STRATEGY_NAME_MAP.items():
            if cn_name in strategy_text:
                return strategy_id

        # Default
        return "bull_trend"

    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """Execute the ask command via Agent pipeline."""
        config = get_config()

        if not config.agent_mode:
            return BotResponse.text_response(
                "⚠️ Agent 模式未开启，无法使用问股功能。\n请在配置中设置 `AGENT_MODE=true`。"
            )

        code = canonical_stock_code(args[0])
        strategy_id = self._parse_strategy(args)
        strategy_text = " ".join(args[1:]).strip() if len(args) > 1 else ""

        logger.info(f"[AskCommand] Stock: {code}, Strategy: {strategy_id}, Extra: {strategy_text}")

        try:
            from src.agent.executor import AgentExecutor
            from src.agent.llm_adapter import LLMToolAdapter
            from src.agent.tools.registry import ToolRegistry
            from src.agent.skills.base import SkillManager
            from src.agent.tools.data_tools import ALL_DATA_TOOLS
            from src.agent.tools.analysis_tools import ALL_ANALYSIS_TOOLS
            from src.agent.tools.search_tools import ALL_SEARCH_TOOLS
            from src.agent.tools.market_tools import ALL_MARKET_TOOLS

            # Build tool registry
            registry = ToolRegistry()
            for tool_fn in ALL_DATA_TOOLS + ALL_ANALYSIS_TOOLS + ALL_SEARCH_TOOLS + ALL_MARKET_TOOLS:
                registry.register(tool_fn)

            # Build skill manager - activate only the selected strategy
            skill_manager = SkillManager()
            skill_manager.load_builtin_strategies()
            custom_dir = getattr(config, "agent_strategy_dir", None)
            if custom_dir:
                skill_manager.load_custom_strategies(custom_dir)
            skill_manager.activate([strategy_id])
            skill_instructions = skill_manager.get_skill_instructions()

            # Build LLM adapter
            llm_adapter = LLMToolAdapter(config)

            # Build executor
            executor = AgentExecutor(
                tool_registry=registry,
                llm_adapter=llm_adapter,
                skill_instructions=skill_instructions,
                max_steps=getattr(config, "agent_max_steps", 10),
            )

            # Build message
            user_msg = f"请使用 {strategy_id} 策略分析股票 {code}"
            if strategy_text:
                user_msg = f"请分析股票 {code}，{strategy_text}"

            # Each /ask invocation is a self-contained single-shot analysis; isolate
            # sessions per request so that different stocks or retry attempts never
            # bleed context into each other.
            session_id = f"ask_{code}_{uuid.uuid4()}"
            result = executor.chat(message=user_msg, session_id=session_id)

            if result.success:
                # Prepend strategy tag
                strategy_name = strategy_id
                try:
                    sm2 = SkillManager()
                    sm2.load_builtin_strategies()
                    for s in sm2.list_skills():
                        if s.name == strategy_id:
                            strategy_name = s.display_name
                            break
                except Exception:
                    pass

                header = f"📊 {code} | 策略: {strategy_name}\n{'─' * 30}\n"
                return BotResponse.text_response(header + result.content)
            else:
                return BotResponse.text_response(f"⚠️ 分析失败: {result.error}")

        except Exception as e:
            logger.error(f"Ask command failed: {e}")
            logger.exception("Ask error details:")
            return BotResponse.text_response(f"⚠️ 问股执行出错: {str(e)}")
