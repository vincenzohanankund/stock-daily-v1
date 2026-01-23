# -*- coding: utf-8 -*-
"""
===================================
Web 服務器核心
===================================

職責：
1. 啟動 HTTP 服務器
2. 處理請求分發
3. 提供後臺運行接口
"""

from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, Type

from web.router import Router, get_router

logger = logging.getLogger(__name__)


# ============================================================
# HTTP 請求處理器
# ============================================================

class WebRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP 請求處理器
    
    將請求分發到路由器處理
    """
    
    # 類級別的路由器引用
    router: Router = None  # type: ignore
    
    def do_GET(self) -> None:
        """處理 GET 請求"""
        self.router.dispatch(self, "GET")
    
    def do_POST(self) -> None:
        """處理 POST 請求"""
        self.router.dispatch_post(self)
    
    def log_message(self, fmt: str, *args) -> None:
        """自定義日誌格式（使用 logging 而非 stderr）"""
        # 可以取消註釋以啟用請求日誌
        # logger.debug(f"[WebServer] {self.address_string()} - {fmt % args}")
        pass


# ============================================================
# Web 服務器
# ============================================================

class WebServer:
    """
    Web 服務器
    
    封裝 ThreadingHTTPServer，提供便捷的啟動和管理接口
    
    使用方式：
        # 前臺運行
        server = WebServer(host="127.0.0.1", port=8000)
        server.run()
        
        # 後臺運行
        server = WebServer(host="127.0.0.1", port=8000)
        server.start_background()
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        router: Optional[Router] = None
    ):
        """
        初始化 Web 服務器
        
        Args:
            host: 監聽地址
            port: 監聽端口
            router: 路由器實例（可選，默認使用全局路由）
        """
        self.host = host
        self.port = port
        self.router = router or get_router()
        
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
    
    @property
    def address(self) -> str:
        """服務器地址"""
        return f"http://{self.host}:{self.port}"
    
    def _create_handler_class(self) -> Type[WebRequestHandler]:
        """創建帶路由器引用的處理器類"""
        router = self.router
        
        class Handler(WebRequestHandler):
            pass
        
        Handler.router = router
        return Handler
    
    def _create_server(self) -> ThreadingHTTPServer:
        """創建 HTTP 服務器實例"""
        handler_class = self._create_handler_class()
        return ThreadingHTTPServer((self.host, self.port), handler_class)
    
    def run(self) -> None:
        """
        前臺運行服務器（阻塞）
        
        按 Ctrl+C 退出
        """
        self._server = self._create_server()
        
        logger.info(f"WebUI 服務啟動: {self.address}")
        print(f"WebUI 服務啟動: {self.address}")
        
        # 打印路由列表
        routes = self.router.list_routes()
        if routes:
            logger.info("已註冊路由:")
            for method, path, desc in routes:
                logger.info(f"  {method:6} {path:20} - {desc}")
        
        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            logger.info("收到退出信號，服務器關閉")
        finally:
            self._server.server_close()
            self._server = None
    
    def start_background(self) -> threading.Thread:
        """
        後臺運行服務器（非阻塞）
        
        Returns:
            服務器線程
        """
        self._server = self._create_server()
        
        def serve():
            logger.info(f"WebUI 已啟動: {self.address}")
            print(f"WebUI 已啟動: {self.address}")
            try:
                self._server.serve_forever()
            except Exception as e:
                logger.error(f"WebUI 發生錯誤: {e}")
            finally:
                if self._server:
                    self._server.server_close()
        
        self._thread = threading.Thread(target=serve, daemon=True)
        self._thread.start()
        return self._thread
    
    def stop(self) -> None:
        """停止服務器"""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            logger.info("WebUI 服務已停止")
    
    def is_running(self) -> bool:
        """檢查服務器是否運行中"""
        return self._server is not None


# ============================================================
# 便捷函數
# ============================================================

def run_server_in_thread(
    host: str = "127.0.0.1",
    port: int = 8000,
    router: Optional[Router] = None
) -> threading.Thread:
    """
    在後臺線程啟動 WebUI 服務器
    
    Args:
        host: 監聽地址
        port: 監聽端口
        router: 路由器實例（可選）
        
    Returns:
        服務器線程
    """
    server = WebServer(host=host, port=port, router=router)
    return server.start_background()


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    router: Optional[Router] = None
) -> None:
    """
    前臺運行 WebUI 服務器（阻塞）
    
    Args:
        host: 監聽地址
        port: 監聽端口
        router: 路由器實例（可選）
    """
    server = WebServer(host=host, port=port, router=router)
    server.run()
