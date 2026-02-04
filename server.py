# -*- coding: utf-8 -*-
"""
===================================
Daily Stock Analysis - FastAPI 后端服务入口
===================================

职责：
1. 提供 RESTful API 服务
2. 配置 CORS 跨域支持
3. 健康检查接口
4. 托管前端静态文件（生产模式）

启动方式：
    uvicorn server:app --reload --host 0.0.0.0 --port 8000
"""

import os
import logging
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 导入 API v1 路由
from api.v1 import api_v1_router
from api.middlewares.error_handler import add_error_handlers
from api.v1.schemas.common import RootResponse, HealthResponse
from src.config import get_config, setup_env

# ============================================================
# 初始化环境变量与日志
# ============================================================

setup_env()

LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_api_logging() -> None:
    """
    配置 FastAPI 日志输出（控制台）

    确保通过 API 触发的分析日志可以在控制台看到
    """
    config = get_config()
    level_name = (config.log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        root_logger.addHandler(console_handler)
    else:
        # 若已有 handler，确保级别至少是 INFO
        for handler in root_logger.handlers:
            if handler.level == logging.NOTSET or handler.level > level:
                handler.setLevel(level)


setup_api_logging()

# ============================================================
# 静态文件目录配置
# ============================================================

# 静态文件目录（前端打包输出目录）
STATIC_DIR = Path(__file__).parent / "static"

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

import os

# 允许的跨域来源
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# 从环境变量添加额外的允许来源（支持 ngrok 等公网访问）
# 例如: CORS_ORIGINS=https://abc123.ngrok.io,https://xyz.ngrok-free.app
extra_origins = os.environ.get("CORS_ORIGINS", "")
if extra_origins:
    ALLOWED_ORIGINS.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

# 如果设置了 CORS_ALLOW_ALL=true，则允许所有来源（开发/演示用，生产环境慎用）
if os.environ.get("CORS_ALLOW_ALL", "").lower() == "true":
    ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # allow_credentials=True if ALLOWED_ORIGINS != ["*"] else False,
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

# 根路由：如果有前端静态文件则返回 index.html，否则返回 API 状态
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    @app.get("/", include_in_schema=False)
    async def root():
        """根路由 - 返回前端页面"""
        return FileResponse(STATIC_DIR / "index.html")
else:
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
# 静态文件托管（前端 SPA）
# ============================================================

# 检查静态文件目录是否存在（已打包前端）
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    # 挂载静态资源目录（JS/CSS/图片等）
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    # SPA 路由：所有非 API 路由返回 index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, full_path: str):
        """
        SPA 路由回退
        
        对于所有非 API 的 GET 请求，返回 index.html，
        让前端路由处理页面导航
        """
        # 如果请求的是 API 路径，不处理（已被上面的路由处理）
        if full_path.startswith("api/"):
            return None
        
        # 检查是否请求的是静态文件
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # 其他所有请求返回 index.html（SPA 路由）
        return FileResponse(STATIC_DIR / "index.html")


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
