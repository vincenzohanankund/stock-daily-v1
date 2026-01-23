# -*- coding: utf-8 -*-
"""
===================================
Web 處理器層 - 請求處理
===================================

職責：
1. 處理各類 HTTP 請求
2. 調用服務層執行業務邏輯
3. 返回響應數據

處理器分類：
- PageHandler: 頁面請求處理
- ApiHandler: API 接口處理
"""

from __future__ import annotations

import json
import re
import logging
from http import HTTPStatus
from datetime import datetime
from typing import Dict, Any, TYPE_CHECKING

from web.services import get_config_service, get_analysis_service
from web.templates import render_config_page
from enums import ReportType

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


# ============================================================
# 響應輔助類
# ============================================================

class Response:
    """HTTP 響應封裝"""
    
    def __init__(
        self,
        body: bytes,
        status: HTTPStatus = HTTPStatus.OK,
        content_type: str = "text/html; charset=utf-8"
    ):
        self.body = body
        self.status = status
        self.content_type = content_type
    
    def send(self, handler: 'BaseHTTPRequestHandler') -> None:
        """發送響應到客戶端"""
        handler.send_response(self.status)
        handler.send_header("Content-Type", self.content_type)
        handler.send_header("Content-Length", str(len(self.body)))
        handler.end_headers()
        handler.wfile.write(self.body)


class JsonResponse(Response):
    """JSON 響應封裝"""
    
    def __init__(
        self,
        data: Dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK
    ):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        super().__init__(
            body=body,
            status=status,
            content_type="application/json; charset=utf-8"
        )


class HtmlResponse(Response):
    """HTML 響應封裝"""
    
    def __init__(
        self,
        body: bytes,
        status: HTTPStatus = HTTPStatus.OK
    ):
        super().__init__(
            body=body,
            status=status,
            content_type="text/html; charset=utf-8"
        )


# ============================================================
# 頁面處理器
# ============================================================

class PageHandler:
    """頁面請求處理器"""
    
    def __init__(self):
        self.config_service = get_config_service()
    
    def handle_index(self) -> Response:
        """處理首頁請求 GET /"""
        stock_list = self.config_service.get_stock_list()
        env_filename = self.config_service.get_env_filename()
        body = render_config_page(stock_list, env_filename)
        return HtmlResponse(body)
    
    def handle_update(self, form_data: Dict[str, list]) -> Response:
        """
        處理配置更新 POST /update
        
        Args:
            form_data: 表單數據
        """
        stock_list = form_data.get("stock_list", [""])[0]
        normalized = self.config_service.set_stock_list(stock_list)
        env_filename = self.config_service.get_env_filename()
        body = render_config_page(normalized, env_filename, message="已保存")
        return HtmlResponse(body)


# ============================================================
# API 處理器
# ============================================================

class ApiHandler:
    """API 請求處理器"""
    
    def __init__(self):
        self.analysis_service = get_analysis_service()
    
    def handle_health(self) -> Response:
        """
        健康檢查 GET /health
        
        返回:
            {
                "status": "ok",
                "timestamp": "2026-01-19T10:30:00",
                "service": "stock-analysis-webui"
            }
        """
        data = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "service": "stock-analysis-webui"
        }
        return JsonResponse(data)
    
    def handle_analysis(self, query: Dict[str, list]) -> Response:
        """
        觸發股票分析 GET /analysis?code=xxx
        
        Args:
            query: URL 查詢參數
            
        返回:
            {
                "success": true,
                "message": "分析任務已提交",
                "code": "600519",
                "task_id": "600519_20260119_103000"
            }
        """
        # 獲取股票代碼參數
        code_list = query.get("code", [])
        if not code_list or not code_list[0].strip():
            return JsonResponse(
                {"success": False, "error": "缺少必填參數: code (股票代碼)"},
                status=HTTPStatus.BAD_REQUEST
            )
        
        code = code_list[0].strip()
        
        # 驗證股票代碼格式：A股(6位數字) 或 港股(hk+5位數字)
        code = code.lower()
        is_valid = re.match(r'^\d{6}$', code) or re.match(r'^hk\d{5}$', code)
        if not is_valid:
            return JsonResponse(
                {"success": False, "error": f"無效的股票代碼格式: {code} (A股6位數字 或 港股hk+5位數字)"},
                status=HTTPStatus.BAD_REQUEST
            )
        
        # 獲取報告類型參數（默認精簡報告）
        report_type_str = query.get("report_type", ["simple"])[0]
        report_type = ReportType.from_str(report_type_str)
        
        # 提交異步分析任務
        try:
            result = self.analysis_service.submit_analysis(code, report_type=report_type)
            return JsonResponse(result)
        except Exception as e:
            logger.error(f"[ApiHandler] 提交分析任務失敗: {e}")
            return JsonResponse(
                {"success": False, "error": f"提交任務失敗: {str(e)}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
    
    def handle_tasks(self, query: Dict[str, list]) -> Response:
        """
        查詢任務列表 GET /tasks
        
        Args:
            query: URL 查詢參數 (可選 limit)
            
        返回:
            {
                "success": true,
                "tasks": [...]
            }
        """
        limit_list = query.get("limit", ["20"])
        try:
            limit = int(limit_list[0])
        except ValueError:
            limit = 20
        
        tasks = self.analysis_service.list_tasks(limit=limit)
        return JsonResponse({"success": True, "tasks": tasks})
    
    def handle_task_status(self, query: Dict[str, list]) -> Response:
        """
        查詢單個任務狀態 GET /task?id=xxx
        
        Args:
            query: URL 查詢參數
        """
        task_id_list = query.get("id", [])
        if not task_id_list or not task_id_list[0].strip():
            return JsonResponse(
                {"success": False, "error": "缺少必填參數: id (任務ID)"},
                status=HTTPStatus.BAD_REQUEST
            )
        
        task_id = task_id_list[0].strip()
        task = self.analysis_service.get_task_status(task_id)
        
        if task is None:
            return JsonResponse(
                {"success": False, "error": f"任務不存在: {task_id}"},
                status=HTTPStatus.NOT_FOUND
            )
        
        return JsonResponse({"success": True, "task": task})


# ============================================================
# Bot Webhook 處理器
# ============================================================

class BotHandler:
    """
    機器人 Webhook 處理器
    
    處理各平臺的機器人回調請求。
    """
    
    def handle_webhook(self, platform: str, form_data: Dict[str, list], headers: Dict[str, str], body: bytes) -> Response:
        """
        處理 Webhook 請求
        
        Args:
            platform: 平臺名稱 (feishu, dingtalk, wecom, telegram)
            form_data: POST 數據（已解析）
            headers: HTTP 請求頭
            body: 原始請求體
            
        Returns:
            Response 對象
        """
        try:
            from bot.handler import handle_webhook
            from bot.models import WebhookResponse
            
            # 調用 bot 模塊處理
            webhook_response = handle_webhook(platform, headers, body)
            
            # 轉換為 web 響應
            return JsonResponse(
                webhook_response.body,
                status=HTTPStatus(webhook_response.status_code)
            )
            
        except ImportError as e:
            logger.error(f"[BotHandler] Bot 模塊未正確安裝: {e}")
            return JsonResponse(
                {"error": "Bot module not available"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"[BotHandler] 處理 {platform} Webhook 失敗: {e}")
            return JsonResponse(
                {"error": str(e)},
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )


# ============================================================
# 處理器工廠
# ============================================================

_page_handler: PageHandler | None = None
_api_handler: ApiHandler | None = None
_bot_handler: BotHandler | None = None


def get_page_handler() -> PageHandler:
    """獲取頁面處理器實例"""
    global _page_handler
    if _page_handler is None:
        _page_handler = PageHandler()
    return _page_handler


def get_api_handler() -> ApiHandler:
    """獲取 API 處理器實例"""
    global _api_handler
    if _api_handler is None:
        _api_handler = ApiHandler()
    return _api_handler


def get_bot_handler() -> BotHandler:
    """獲取 Bot 處理器實例"""
    global _bot_handler
    if _bot_handler is None:
        _bot_handler = BotHandler()
    return _bot_handler
