# -*- coding: utf-8 -*-
"""
===================================
Web 路由層 - 請求分發
===================================

職責：
1. 解析請求路徑
2. 分發到對應的處理器
3. 支持路由註冊和擴展
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Callable, Dict, List, Optional, TYPE_CHECKING, Tuple
from urllib.parse import parse_qs, urlparse

from web.handlers import (
    Response, HtmlResponse, JsonResponse,
    get_page_handler, get_api_handler, get_bot_handler
)
from web.templates import render_error_page

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


# ============================================================
# 路由定義
# ============================================================

# 路由處理函數類型: (query_params) -> Response
RouteHandler = Callable[[Dict[str, list]], Response]


class Route:
    """路由定義"""
    
    def __init__(
        self,
        path: str,
        method: str,
        handler: RouteHandler,
        description: str = ""
    ):
        self.path = path
        self.method = method.upper()
        self.handler = handler
        self.description = description


class Router:
    """
    路由管理器
    
    負責：
    1. 註冊路由
    2. 匹配請求路徑
    3. 分發到處理器
    """
    
    def __init__(self):
        self._routes: Dict[str, Dict[str, Route]] = {}  # {path: {method: Route}}
    
    def register(
        self,
        path: str,
        method: str,
        handler: RouteHandler,
        description: str = ""
    ) -> None:
        """
        註冊路由
        
        Args:
            path: 路由路徑
            method: HTTP 方法 (GET, POST, etc.)
            handler: 處理函數
            description: 路由描述
        """
        method = method.upper()
        if path not in self._routes:
            self._routes[path] = {}
        
        self._routes[path][method] = Route(path, method, handler, description)
        logger.debug(f"[Router] 註冊路由: {method} {path}")
    
    def get(self, path: str, description: str = "") -> Callable:
        """裝飾器：註冊 GET 路由"""
        def decorator(handler: RouteHandler) -> RouteHandler:
            self.register(path, "GET", handler, description)
            return handler
        return decorator
    
    def post(self, path: str, description: str = "") -> Callable:
        """裝飾器：註冊 POST 路由"""
        def decorator(handler: RouteHandler) -> RouteHandler:
            self.register(path, "POST", handler, description)
            return handler
        return decorator
    
    def match(self, path: str, method: str) -> Optional[Route]:
        """
        匹配路由
        
        Args:
            path: 請求路徑
            method: HTTP 方法
            
        Returns:
            匹配的路由，或 None
        """
        method = method.upper()
        routes_for_path = self._routes.get(path)
        
        if routes_for_path is None:
            return None
        
        return routes_for_path.get(method)
    
    def dispatch(
        self,
        request_handler: 'BaseHTTPRequestHandler',
        method: str
    ) -> None:
        """
        分發請求
        
        Args:
            request_handler: HTTP 請求處理器
            method: HTTP 方法
        """
        # 解析 URL
        parsed = urlparse(request_handler.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        # 處理根路徑
        if path == "":
            path = "/"
        
        # 匹配路由
        route = self.match(path, method)
        
        if route is None:
            # 404 Not Found
            self._send_not_found(request_handler, path)
            return
        
        try:
            # 調用處理器
            response = route.handler(query)
            response.send(request_handler)
            
        except Exception as e:
            logger.error(f"[Router] 處理請求失敗: {method} {path} - {e}")
            self._send_error(request_handler, str(e))
    
    def dispatch_post(
        self,
        request_handler: 'BaseHTTPRequestHandler'
    ) -> None:
        """
        分發 POST 請求（需要讀取 body）
        
        Args:
            request_handler: HTTP 請求處理器
        """
        parsed = urlparse(request_handler.path)
        path = parsed.path
        
        # 讀取 POST body（保留原始字節用於 Bot Webhook）
        content_length = int(request_handler.headers.get("Content-Length", "0") or "0")
        raw_body_bytes = request_handler.rfile.read(content_length)
        raw_body = raw_body_bytes.decode("utf-8", errors="replace")
        
        # 檢查是否是 Bot Webhook 路由
        if path.startswith("/bot/"):
            self._dispatch_bot_webhook(request_handler, path, raw_body_bytes)
            return
        
        # 普通 POST 請求
        form_data = parse_qs(raw_body)
        
        # 匹配路由
        route = self.match(path, "POST")
        
        if route is None:
            self._send_not_found(request_handler, path)
            return
        
        try:
            # 調用處理器（傳入 form_data）
            response = route.handler(form_data)
            response.send(request_handler)
            
        except Exception as e:
            logger.error(f"[Router] 處理 POST 請求失敗: {path} - {e}")
            self._send_error(request_handler, str(e))
    
    def _dispatch_bot_webhook(
        self,
        request_handler: 'BaseHTTPRequestHandler',
        path: str,
        body: bytes
    ) -> None:
        """
        分發 Bot Webhook 請求
        
        Bot Webhook 需要原始 body 和 headers，與普通路由處理不同。
        
        Args:
            request_handler: HTTP 請求處理器
            path: 請求路徑
            body: 原始請求體字節
        """
        # 提取平臺名稱：/bot/feishu -> feishu
        parts = path.strip('/').split('/')
        if len(parts) < 2:
            self._send_not_found(request_handler, path)
            return
        
        platform = parts[1]
        
        # 獲取請求頭
        headers = {key: value for key, value in request_handler.headers.items()}
        
        try:
            bot_handler = get_bot_handler()
            response = bot_handler.handle_webhook(platform, {}, headers, body)
            response.send(request_handler)
            
        except Exception as e:
            logger.error(f"[Router] 處理 Bot Webhook 失敗: {path} - {e}")
            self._send_error(request_handler, str(e))
    
    def list_routes(self) -> List[Tuple[str, str, str]]:
        """
        列出所有路由
        
        Returns:
            [(method, path, description), ...]
        """
        routes = []
        for path, methods in self._routes.items():
            for method, route in methods.items():
                routes.append((method, path, route.description))
        return sorted(routes, key=lambda x: (x[1], x[0]))
    
    def _send_not_found(
        self,
        request_handler: 'BaseHTTPRequestHandler',
        path: str
    ) -> None:
        """發送 404 響應"""
        body = render_error_page(404, "頁面未找到", f"路徑 {path} 不存在")
        response = HtmlResponse(body, status=HTTPStatus.NOT_FOUND)
        response.send(request_handler)
    
    def _send_error(
        self,
        request_handler: 'BaseHTTPRequestHandler',
        message: str
    ) -> None:
        """發送 500 響應"""
        body = render_error_page(500, "服務器內部錯誤", message)
        response = HtmlResponse(body, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        response.send(request_handler)


# ============================================================
# 默認路由註冊
# ============================================================

def create_default_router() -> Router:
    """創建並配置默認路由"""
    router = Router()
    
    # 獲取處理器
    page_handler = get_page_handler()
    api_handler = get_api_handler()
    
    # === 頁面路由 ===
    router.register(
        "/", "GET",
        lambda q: page_handler.handle_index(),
        "配置首頁"
    )
    
    router.register(
        "/update", "POST",
        lambda form: page_handler.handle_update(form),
        "更新配置"
    )
    
    # === API 路由 ===
    router.register(
        "/health", "GET",
        lambda q: api_handler.handle_health(),
        "健康檢查"
    )
    
    router.register(
        "/analysis", "GET",
        lambda q: api_handler.handle_analysis(q),
        "觸發股票分析"
    )
    
    router.register(
        "/tasks", "GET",
        lambda q: api_handler.handle_tasks(q),
        "查詢任務列表"
    )
    
    router.register(
        "/task", "GET",
        lambda q: api_handler.handle_task_status(q),
        "查詢任務狀態"
    )
    
    # === Bot Webhook 路由 ===
    # 注意：Bot Webhook 路由在 dispatch_post 中特殊處理
    # 這裡只是為了在路由列表中顯示
    # 實際請求會被 _dispatch_bot_webhook 方法處理
    
    # 飛書機器人 Webhook
    router.register(
        "/bot/feishu", "POST",
        lambda form: JsonResponse({"error": "Use POST with JSON body"}),
        "飛書機器人 Webhook"
    )
    
    # 釘釘機器人 Webhook
    router.register(
        "/bot/dingtalk", "POST",
        lambda form: JsonResponse({"error": "Use POST with JSON body"}),
        "釘釘機器人 Webhook"
    )
    
    # 企業微信機器人 Webhook（開發中）
    # router.register(
    #     "/bot/wecom", "POST",
    #     lambda form: JsonResponse({"error": "Use POST with JSON body"}),
    #     "企業微信機器人 Webhook"
    # )
    
    # Telegram 機器人 Webhook（開發中）
    # router.register(
    #     "/bot/telegram", "POST",
    #     lambda form: JsonResponse({"error": "Use POST with JSON body"}),
    #     "Telegram 機器人 Webhook"
    # )
    
    return router


# 全局默認路由實例
_default_router: Router | None = None


def get_router() -> Router:
    """獲取默認路由實例"""
    global _default_router
    if _default_router is None:
        _default_router = create_default_router()
    return _default_router
