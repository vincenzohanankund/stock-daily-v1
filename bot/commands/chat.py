# -*- coding: utf-8 -*-
"""
Chat command for free-form conversation with the Agent.
"""

import logging
from typing import Any, Dict, Optional

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse
from src.config import get_config

logger = logging.getLogger(__name__)

class ChatCommand(BotCommand):
    """
    Chat command handler.
    
    Usage: /chat <message>
    Example: /chat 帮我分析一下茅台最近的走势
    """
    
    @property
    def name(self) -> str:
        return "chat"
        
    @property
    def description(self) -> str:
        return "与 AI 助手进行自由对话 (需开启 Agent 模式)"
        
    @property
    def usage(self) -> str:
        return "/chat <问题>"
        
    @property
    def aliases(self) -> list[str]:
        return ["c", "问"]
        
    def execute(self, message: BotMessage, args: list[str]) -> BotResponse:
        """Execute the chat command."""
        config = get_config()
        
        if not config.agent_mode:
            return BotResponse.text_response(
                "⚠️ Agent 模式未开启，无法使用对话功能。\n请在配置中设置 `AGENT_MODE=true`。"
            )
            
        if not args:
            return BotResponse.text_response(
                "⚠️ 请提供要询问的问题。\n用法: `/chat <问题>`\n示例: `/chat 帮我分析一下茅台最近的走势`"
            )
            
        user_message = " ".join(args)
        session_id = f"{message.platform}_{message.user_id}"
        
        try:
            # Import agent components
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
            for tool_fn in (ALL_DATA_TOOLS + ALL_ANALYSIS_TOOLS + ALL_SEARCH_TOOLS + ALL_MARKET_TOOLS):
                registry.register(tool_fn)
                
            # Build skill manager
            skill_manager = SkillManager()
            skill_manager.load_builtin_strategies()
            custom_dir = getattr(config, 'agent_strategy_dir', None)
            if custom_dir:
                skill_manager.load_custom_strategies(custom_dir)
            if config.agent_skills:
                skill_manager.activate(config.agent_skills)
            else:
                skill_manager.activate(["all"])
            skill_instructions = skill_manager.get_skill_instructions()
            
            # Build LLM adapter
            llm_adapter = LLMToolAdapter(config)
            
            # Build executor
            executor = AgentExecutor(
                tool_registry=registry,
                llm_adapter=llm_adapter,
                skill_instructions=skill_instructions,
                max_steps=config.agent_max_steps,
            )
            
            # Run chat
            result = executor.chat(message=user_message, session_id=session_id)
            
            if result.success:
                return BotResponse.text_response(result.content)
            else:
                return BotResponse.text_response(f"⚠️ 对话失败: {result.error}")
                
        except Exception as e:
            logger.error(f"Chat command failed: {e}")
            logger.exception("Chat error details:")
            return BotResponse.text_response(f"⚠️ 对话执行出错: {str(e)}")
