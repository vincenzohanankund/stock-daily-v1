# -*- coding: utf-8 -*-
"""
Agent API endpoints.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config import get_config

# Tool name -> Chinese display name mapping
TOOL_DISPLAY_NAMES: Dict[str, str] = {
    "get_realtime_quote": "获取实时行情",
    "get_k_history": "获取历史K线",
    "get_technical_analysis": "分析技术指标",
    "get_chip_analysis": "分析筹码分布",
    "search_news": "搜索新闻资讯",
    "search_web": "搜索网络信息",
    "get_market_overview": "获取市场概览",
    "get_sector_analysis": "分析行业板块",
    "get_financial_data": "获取财务数据",
    "get_stock_info": "获取股票基本信息",
    "analyze_pattern": "识别K线形态",
    "get_volume_analysis": "分析量能变化",
}

logger = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_AGENT_SKILLS = [
    "bull_trend",
    "ma_golden_cross",
    "volume_breakout",
    "shrink_pullback",
]

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    skills: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None  # Previous analysis context for data reuse

class ChatResponse(BaseModel):
    success: bool
    content: str
    session_id: str
    error: Optional[str] = None

class StrategyInfo(BaseModel):
    id: str
    name: str
    description: str

class StrategiesResponse(BaseModel):
    strategies: List[StrategyInfo]

@router.get("/strategies", response_model=StrategiesResponse)
async def get_strategies():
    """
    Get available agent strategies.
    """
    config = get_config()
    from src.agent.skills.base import SkillManager
    
    skill_manager = SkillManager()
    skill_manager.load_builtin_strategies()
    custom_dir = getattr(config, 'agent_strategy_dir', None)
    if custom_dir:
        skill_manager.load_custom_strategies(custom_dir)
        
    strategies = []
    for skill_id, skill in skill_manager._skills.items():
        strategies.append(StrategyInfo(
            id=skill_id,
            name=skill.display_name,
            description=skill.description
        ))
        
    return StrategiesResponse(strategies=strategies)

@router.post("/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    """
    Chat with the AI Agent.
    """
    config = get_config()
    
    if not config.agent_mode:
        raise HTTPException(status_code=400, detail="Agent mode is not enabled")
        
    session_id = request.session_id or "default_session"
    
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
            
        skills_to_activate = request.skills if request.skills is not None else (config.agent_skills or DEFAULT_AGENT_SKILLS)
        if skills_to_activate:
            skill_manager.activate(skills_to_activate)
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
        result = executor.chat(message=request.message, session_id=session_id)
        
        return ChatResponse(
            success=result.success,
            content=result.content,
            session_id=session_id,
            error=result.error
        )
            
    except Exception as e:
        logger.error(f"Agent chat API failed: {e}")
        logger.exception("Agent chat error details:")
        raise HTTPException(status_code=500, detail=str(e))


def _build_executor(config, skills: Optional[List[str]] = None):
    """Build and return a configured AgentExecutor (sync helper)."""
    from src.agent.executor import AgentExecutor
    from src.agent.llm_adapter import LLMToolAdapter
    from src.agent.tools.registry import ToolRegistry
    from src.agent.skills.base import SkillManager
    from src.agent.tools.data_tools import ALL_DATA_TOOLS
    from src.agent.tools.analysis_tools import ALL_ANALYSIS_TOOLS
    from src.agent.tools.search_tools import ALL_SEARCH_TOOLS
    from src.agent.tools.market_tools import ALL_MARKET_TOOLS

    registry = ToolRegistry()
    for tool_fn in (ALL_DATA_TOOLS + ALL_ANALYSIS_TOOLS + ALL_SEARCH_TOOLS + ALL_MARKET_TOOLS):
        registry.register(tool_fn)

    skill_manager = SkillManager()
    skill_manager.load_builtin_strategies()
    custom_dir = getattr(config, "agent_strategy_dir", None)
    if custom_dir:
        skill_manager.load_custom_strategies(custom_dir)

    skills_to_activate = skills if skills is not None else (config.agent_skills or DEFAULT_AGENT_SKILLS)
    skill_manager.activate(skills_to_activate if skills_to_activate else ["all"])
    logger.info(f"Activated strategies: {skills_to_activate}")

    llm_adapter = LLMToolAdapter(config)
    return AgentExecutor(
        tool_registry=registry,
        llm_adapter=llm_adapter,
        skill_instructions=skill_manager.get_skill_instructions(),
        max_steps=config.agent_max_steps,
    )


@router.post("/chat/stream")
async def agent_chat_stream(request: ChatRequest):
    """
    Chat with the AI Agent, streaming progress via SSE.
    Each SSE event is a JSON object with a 'type' field:
      - thinking: AI is deciding next action
      - tool_start: a tool call has begun
      - tool_done: a tool call finished
      - generating: final answer being generated
      - done: analysis complete, contains 'content' and 'success'
      - error: error occurred, contains 'message'
    """
    config = get_config()
    if not config.agent_mode:
        raise HTTPException(status_code=400, detail="Agent mode is not enabled")

    session_id = request.session_id or "default_session"
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def progress_callback(event: dict):
        # Enrich tool events with display names
        if event.get("type") in ("tool_start", "tool_done"):
            tool = event.get("tool", "")
            event["display_name"] = TOOL_DISPLAY_NAMES.get(tool, tool)
        asyncio.run_coroutine_threadsafe(queue.put(event), loop)

    def run_sync():
        try:
            executor = _build_executor(config, request.skills)
            result = executor.chat(
                message=request.message,
                session_id=session_id,
                progress_callback=progress_callback,
                context=request.context,
            )
            asyncio.run_coroutine_threadsafe(
                queue.put({
                    "type": "done",
                    "success": result.success,
                    "content": result.content,
                    "error": result.error,
                    "total_steps": result.total_steps,
                }),
                loop,
            )
        except Exception as exc:
            logger.error(f"Agent stream error: {exc}")
            asyncio.run_coroutine_threadsafe(
                queue.put({"type": "error", "message": str(exc)}),
                loop,
            )

    async def event_generator():
        # Start executor in a thread so we don't block the event loop
        fut = loop.run_in_executor(None, run_sync)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=300.0)
                except asyncio.TimeoutError:
                    yield "data: " + json.dumps({"type": "error", "message": "分析超时"}, ensure_ascii=False) + "\n\n"
                    break
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
                if event.get("type") in ("done", "error"):
                    break
        finally:
            try:
                await asyncio.wait_for(fut, timeout=5.0)
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
