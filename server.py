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

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入 API v1 路由
from api.v1 import api_v1_router
from api.middlewares.error_handler import add_error_handlers
from api.v1.schemas.common import RootResponse, HealthResponse

# ============================================================
# FastAPI 应用实例
# ============================================================

app = FastAPI(
    title="Daily Stock Analysis API",
    description="A股/港股/美股自选股智能分析系统 API\n\n## 功能模块\n- 股票分析：触发 AI 智能分析\n- 历史记录：查询历史分析报告\n- 股票数据：获取行情数据\n\n## 认证方式\n当前版本暂无认证要求",
    version="1.0.0",
)

# ============================================================
# CORS 配置
# ============================================================

# 允许的跨域来源（React 开发服务器默认端口）
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 注册 API v1 路由
# ============================================================

app.include_router(api_v1_router)

# 添加全局异常处理器
add_error_handlers(app)


# ============================================================
# 路由定义
# ============================================================

@app.get(
    "/",
    response_model=RootResponse,
    tags=["Health"],
    summary="API 根路由",
    description="返回 API 运行状态信息"
)
async def root() -> RootResponse:
    """
    根路由 - API 状态信息
    
    Returns:
        RootResponse: 包含 API 运行状态消息和版本信息
    """
    return RootResponse(
        message="Daily Stock Analysis API is running",
        version="1.0.0"
    )


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="健康检查",
    description="用于负载均衡器或监控系统检查服务状态"
)
async def health_check() -> HealthResponse:
    """
    健康检查接口
    
    用于前后端联调、负载均衡健康检查等场景
    
    Returns:
        HealthResponse: 包含健康状态和时间戳的响应
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat()
    )


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
