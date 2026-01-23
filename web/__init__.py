# -*- coding: utf-8 -*-
"""
===================================
Web 服務模塊
===================================

分層架構：
- server.py    - HTTP 服務器核心
- router.py    - 路由分發
- handlers.py  - 請求處理器
- services.py  - 業務服務層
- templates.py - HTML 模板

使用方式：
    from web import run_server_in_thread, WebServer
    
    # 後臺啟動
    run_server_in_thread(host="127.0.0.1", port=8000)
    
    # 前臺啟動
    server = WebServer(host="127.0.0.1", port=8000)
    server.run()
"""

from web.server import WebServer, run_server_in_thread

__all__ = [
    'WebServer',
    'run_server_in_thread',
]
