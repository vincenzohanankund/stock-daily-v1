# -*- coding: utf-8 -*-
"""
===================================
Web 服務層 - 業務邏輯
===================================

職責：
1. 配置管理服務 (ConfigService)
2. 分析任務服務 (AnalysisService)
"""

from __future__ import annotations

import os
import re
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

from enums import ReportType
from bot.models import BotMessage

logger = logging.getLogger(__name__)

# ============================================================
# 配置管理服務
# ============================================================

_ENV_PATH = os.getenv("ENV_FILE", ".env")

_STOCK_LIST_RE = re.compile(
    r"^(?P<prefix>\s*STOCK_LIST\s*=\s*)(?P<value>.*?)(?P<suffix>\s*)$"
)


class ConfigService:
    """
    配置管理服務
    
    負責 .env 文件中 STOCK_LIST 的讀寫操作
    """
    
    def __init__(self, env_path: Optional[str] = None):
        self.env_path = env_path or _ENV_PATH
    
    def read_env_text(self) -> str:
        """讀取 .env 文件內容"""
        try:
            with open(self.env_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""
    
    def write_env_text(self, text: str) -> None:
        """寫入 .env 文件內容"""
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.write(text)
    
    def get_stock_list(self) -> str:
        """獲取當前自選股列表字符串"""
        env_text = self.read_env_text()
        return self._extract_stock_list(env_text)
    
    def set_stock_list(self, stock_list: str) -> str:
        """
        設置自選股列表
        
        Args:
            stock_list: 股票代碼字符串（逗號或換行分隔）
            
        Returns:
            規範化後的股票列表字符串
        """
        env_text = self.read_env_text()
        normalized = self._normalize_stock_list(stock_list)
        updated = self._update_stock_list(env_text, normalized)
        self.write_env_text(updated)
        return normalized
    
    def get_env_filename(self) -> str:
        """獲取 .env 文件名"""
        return os.path.basename(self.env_path)
    
    def _extract_stock_list(self, env_text: str) -> str:
        """從環境文件中提取 STOCK_LIST 值"""
        for line in env_text.splitlines():
            m = _STOCK_LIST_RE.match(line)
            if m:
                raw = m.group("value").strip()
                # 去除引號
                if (raw.startswith('"') and raw.endswith('"')) or \
                   (raw.startswith("'") and raw.endswith("'")):
                    raw = raw[1:-1]
                return raw
        return ""
    
    def _normalize_stock_list(self, value: str) -> str:
        """規範化股票列表格式"""
        parts = [p.strip() for p in value.replace("\n", ",").split(",")]
        parts = [p for p in parts if p]
        return ",".join(parts)
    
    def _update_stock_list(self, env_text: str, new_value: str) -> str:
        """更新環境文件中的 STOCK_LIST"""
        lines = env_text.splitlines(keepends=False)
        out_lines: List[str] = []
        replaced = False
        
        for line in lines:
            m = _STOCK_LIST_RE.match(line)
            if not m:
                out_lines.append(line)
                continue
            
            out_lines.append(f"{m.group('prefix')}{new_value}{m.group('suffix')}")
            replaced = True
        
        if not replaced:
            if out_lines and out_lines[-1].strip() != "":
                out_lines.append("")
            out_lines.append(f"STOCK_LIST={new_value}")
        
        trailing_newline = env_text.endswith("\n") if env_text else True
        out = "\n".join(out_lines)
        return out + ("\n" if trailing_newline else "")


# ============================================================
# 分析任務服務
# ============================================================

class AnalysisService:
    """
    分析任務服務
    
    負責：
    1. 管理異步分析任務
    2. 執行股票分析
    3. 觸發通知推送
    """
    
    _instance: Optional['AnalysisService'] = None
    _lock = threading.Lock()
    
    def __init__(self, max_workers: int = 3):
        self._executor: Optional[ThreadPoolExecutor] = None
        self._max_workers = max_workers
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._tasks_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'AnalysisService':
        """獲取單例實例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @property
    def executor(self) -> ThreadPoolExecutor:
        """獲取或創建線程池"""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="analysis_"
            )
        return self._executor
    
    def submit_analysis(
        self, 
        code: str, 
        report_type: Union[ReportType, str] = ReportType.SIMPLE,
        source_message: Optional[BotMessage] = None
    ) -> Dict[str, Any]:
        """
        提交異步分析任務
        
        Args:
            code: 股票代碼
            report_type: 報告類型枚舉
            
        Returns:
            任務信息字典
        """
        # 確保 report_type 是枚舉類型
        if isinstance(report_type, str):
            report_type = ReportType.from_str(report_type)
        
        task_id = f"{code}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # 提交到線程池
        self.executor.submit(self._run_analysis, code, task_id, report_type, source_message)
        
        logger.info(f"[AnalysisService] 已提交股票 {code} 的分析任務, task_id={task_id}, report_type={report_type.value}")
        
        return {
            "success": True,
            "message": "分析任務已提交，將異步執行並推送通知",
            "code": code,
            "task_id": task_id,
            "report_type": report_type.value
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """獲取任務狀態"""
        with self._tasks_lock:
            return self._tasks.get(task_id)
    
    def list_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的任務"""
        with self._tasks_lock:
            tasks = list(self._tasks.values())
        # 按開始時間倒序
        tasks.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        return tasks[:limit]
    
    def _run_analysis(
        self, 
        code: str, 
        task_id: str, 
        report_type: ReportType = ReportType.SIMPLE,
        source_message: Optional[BotMessage] = None
    ) -> Dict[str, Any]:
        """
        執行單隻股票分析
        
        內部方法，在線程池中運行
        
        Args:
            code: 股票代碼
            task_id: 任務ID
            report_type: 報告類型枚舉
        """
        # 初始化任務狀態
        with self._tasks_lock:
            self._tasks[task_id] = {
                "task_id": task_id,
                "code": code,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "result": None,
                "error": None,
                "report_type": report_type.value
            }
        
        try:
            # 延遲導入避免循環依賴
            from config import get_config
            from main import StockAnalysisPipeline
            
            logger.info(f"[AnalysisService] 開始分析股票: {code}")
            
            # 創建分析管道
            config = get_config()
            pipeline = StockAnalysisPipeline(
                config=config,
                max_workers=1,
                source_message=source_message
            )
            
            # 執行單隻股票分析（啟用單股推送）
            result = pipeline.process_single_stock(
                code=code,
                skip_analysis=False,
                single_stock_notify=True,
                report_type=report_type
            )
            
            if result:
                result_data = {
                    "code": result.code,
                    "name": result.name,
                    "sentiment_score": result.sentiment_score,
                    "operation_advice": result.operation_advice,
                    "trend_prediction": result.trend_prediction,
                    "analysis_summary": result.analysis_summary,
                }
                
                with self._tasks_lock:
                    self._tasks[task_id].update({
                        "status": "completed",
                        "end_time": datetime.now().isoformat(),
                        "result": result_data
                    })
                
                logger.info(f"[AnalysisService] 股票 {code} 分析完成: {result.operation_advice}")
                return {"success": True, "task_id": task_id, "result": result_data}
            else:
                with self._tasks_lock:
                    self._tasks[task_id].update({
                        "status": "failed",
                        "end_time": datetime.now().isoformat(),
                        "error": "分析返回空結果"
                    })
                
                logger.warning(f"[AnalysisService] 股票 {code} 分析失敗: 返回空結果")
                return {"success": False, "task_id": task_id, "error": "分析返回空結果"}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AnalysisService] 股票 {code} 分析異常: {error_msg}")
            
            with self._tasks_lock:
                self._tasks[task_id].update({
                    "status": "failed",
                    "end_time": datetime.now().isoformat(),
                    "error": error_msg
                })
            
            return {"success": False, "task_id": task_id, "error": error_msg}


# ============================================================
# 便捷函數
# ============================================================

def get_config_service() -> ConfigService:
    """獲取配置服務實例"""
    return ConfigService()


def get_analysis_service() -> AnalysisService:
    """獲取分析服務單例"""
    return AnalysisService.get_instance()
