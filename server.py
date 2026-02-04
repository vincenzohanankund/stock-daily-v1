# -*- coding: utf-8 -*-
"""
===================================
Daily Stock Analysis - FastAPI 后端服务入口
===================================

职责：
1. 提供 RESTful API 服务
2. 配置 CORS 跨域支持
3. 健康检查接口

启动方式：
    uvicorn server:app --reload --host 0.0.0.0 --port 8000
"""

from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# FastAPI 应用实例
# ============================================================

app = FastAPI(
    title="Daily Stock Analysis API",
    description="A股/港股/美股自选股智能分析系统 API",
    version="1.0.0",
)

# ============================================================
# CORS 配置
# ============================================================

# 允许的跨域来源（React 开发服务器默认端口）
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 路由定义
# ============================================================

@app.get("/", response_model=Dict[str, str])
async def root() -> Dict[str, str]:
    """
    根路由 - API 状态信息
    
    Returns:
        包含 API 运行状态消息的字典
    """
    return {"message": "Daily Stock Analysis API is running"}


@app.get("/api/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """
    健康检查接口
    
    用于前后端联调、负载均衡健康检查等场景
    
    Returns:
        包含健康状态的字典
    """
    return {"status": "ok"}


# ============================================================
# 入口（直接运行时使用）
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
