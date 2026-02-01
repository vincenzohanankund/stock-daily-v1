# -*- coding: utf-8 -*-
"""
===================================
Web 服务层 - 业务逻辑
===================================

职责：
1. 配置管理服务 (ConfigService)
2. 分析任务服务 (AnalysisService)
"""

from __future__ import annotations

import os
import re
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

from src.enums import ReportType
from bot.models import BotMessage

logger = logging.getLogger(__name__)

# ============================================================
# 配置管理服务
# ============================================================

_ENV_PATH = os.getenv("ENV_FILE", ".env")

_STOCK_LIST_RE = re.compile(
    r"^(?P<prefix>\s*STOCK_LIST\s*=\s*)(?P<value>.*?)(?P<suffix>\s*)$"
)


class ConfigService:
    """
    配置管理服务
    
    负责 .env 文件中 STOCK_LIST 的读写操作
    """
    
    def __init__(self, env_path: Optional[str] = None):
        self.env_path = env_path or _ENV_PATH
    
    def read_env_text(self) -> str:
        """读取 .env 文件内容"""
        try:
            with open(self.env_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""
    
    def write_env_text(self, text: str) -> None:
        """写入 .env 文件内容"""
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.write(text)
    
    def get_stock_list(self) -> str:
        """获取当前自选股列表字符串"""
        env_text = self.read_env_text()
        return self._extract_stock_list(env_text)
    
    def set_stock_list(self, stock_list: str) -> str:
        """
        设置自选股列表
        
        Args:
            stock_list: 股票代码字符串（逗号或换行分隔）
            
        Returns:
            规范化后的股票列表字符串
        """
        env_text = self.read_env_text()
        normalized = self._normalize_stock_list(stock_list)
        updated = self._update_stock_list(env_text, normalized)
        self.write_env_text(updated)
        return normalized
    
    def get_env_filename(self) -> str:
        """获取 .env 文件名"""
        return os.path.basename(self.env_path)
    
    def _extract_stock_list(self, env_text: str) -> str:
        """从环境文件中提取 STOCK_LIST 值"""
        for line in env_text.splitlines():
            m = _STOCK_LIST_RE.match(line)
            if m:
                raw = m.group("value").strip()
                # 去除引号
                if (raw.startswith('"') and raw.endswith('"')) or \
                   (raw.startswith("'") and raw.endswith("'")):
                    raw = raw[1:-1]
                return raw
        return ""
    
    def _normalize_stock_list(self, value: str) -> str:
        """规范化股票列表格式"""
        parts = [p.strip() for p in value.replace("\n", ",").split(",")]
        parts = [p for p in parts if p]
        return ",".join(parts)
    
    def _update_stock_list(self, env_text: str, new_value: str) -> str:
        """更新环境文件中的 STOCK_LIST"""
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
# 分析任务服务
# ============================================================

class AnalysisService:
    """
    分析任务服务
    
    负责：
    1. 管理异步分析任务
    2. 执行股票分析
    3. 触发通知推送
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
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @property
    def executor(self) -> ThreadPoolExecutor:
        """获取或创建线程池"""
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
        提交异步分析任务
        
        Args:
            code: 股票代码
            report_type: 报告类型枚举
            
        Returns:
            任务信息字典
        """
        # 确保 report_type 是枚举类型
        if isinstance(report_type, str):
            report_type = ReportType.from_str(report_type)
        
        task_id = f"{code}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # 提交到线程池
        self.executor.submit(self._run_analysis, code, task_id, report_type, source_message)
        
        logger.info(f"[AnalysisService] 已提交股票 {code} 的分析任务, task_id={task_id}, report_type={report_type.value}")
        
        return {
            "success": True,
            "message": "分析任务已提交，将异步执行并推送通知",
            "code": code,
            "task_id": task_id,
            "report_type": report_type.value
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self._tasks_lock:
            return self._tasks.get(task_id)
    
    def list_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的任务"""
        with self._tasks_lock:
            tasks = list(self._tasks.values())
        # 按开始时间倒序
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
        执行单只股票分析
        
        内部方法，在线程池中运行
        
        Args:
            code: 股票代码
            task_id: 任务ID
            report_type: 报告类型枚举
        """
        # 初始化任务状态
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
            # 延迟导入避免循环依赖
            from src.config import get_config
            from main import StockAnalysisPipeline
            
            logger.info(f"[AnalysisService] 开始分析股票: {code}")
            
            # 创建分析管道
            config = get_config()
            pipeline = StockAnalysisPipeline(
                config=config,
                max_workers=1,
                source_message=source_message
            )
            
            # 执行单只股票分析（启用单股推送）
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
                        "error": "分析返回空结果"
                    })
                
                logger.warning(f"[AnalysisService] 股票 {code} 分析失败: 返回空结果")
                return {"success": False, "task_id": task_id, "error": "分析返回空结果"}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AnalysisService] 股票 {code} 分析异常: {error_msg}")
            
            with self._tasks_lock:
                self._tasks[task_id].update({
                    "status": "failed",
                    "end_time": datetime.now().isoformat(),
                    "error": error_msg
                })
            
            return {"success": False, "task_id": task_id, "error": error_msg}


# ============================================================
# 历史报告服务
# ============================================================

import os
import re
import json
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple


class HistoryReportService:
    """
    历史报告服务
    
    负责：
    1. 从 reports 目录读取已生成的报告文件
    2. 解析报告内容，提取结构化数据
    3. 提供按日期查询报告接口
    """
    
    def __init__(self, reports_dir: Optional[str] = None):
        """
        初始化历史报告服务
        
        Args:
            reports_dir: 报告目录路径（默认项目根目录下的 reports）
        """
        if reports_dir:
            self.reports_dir = Path(reports_dir)
        else:
            # 默认使用项目根目录下的 reports
            self.reports_dir = Path(__file__).parent.parent / 'reports'
    
    def get_available_dates(self) -> List[str]:
        """
        获取所有可用的报告日期列表
        
        Returns:
            日期字符串列表（格式：YYYY-MM-DD），按日期降序排列
        """
        dates = set()
        
        if not self.reports_dir.exists():
            return []
        
        # 匹配 report_YYYYMMDD.md 和 market_review_YYYYMMDD.md 文件
        report_pattern = re.compile(r'report_(\d{8})\.md')
        market_pattern = re.compile(r'market_review_(\d{8})\.md')
        
        for file in self.reports_dir.iterdir():
            if file.is_file():
                # 检查个股报告
                match = report_pattern.match(file.name)
                if match:
                    date_str = match.group(1)
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                    dates.add(formatted_date)
                    continue
                
                # 检查大盘复盘报告
                match = market_pattern.match(file.name)
                if match:
                    date_str = match.group(1)
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                    dates.add(formatted_date)
        
        # 按日期降序排列
        return sorted(list(dates), reverse=True)
    
    def get_report_by_date(self, target_date: str) -> Optional[Dict[str, Any]]:
        """
        获取指定日期的完整报告数据
        
        Args:
            target_date: 目标日期（格式：YYYY-MM-DD）
            
        Returns:
            报告数据字典，包含 marketReview 和 decisions
        """
        # 转换日期格式
        date_obj = datetime.strptime(target_date, '%Y-%m-%d')
        date_str_compact = date_obj.strftime('%Y%m%d')
        
        # 构建文件路径
        report_file = self.reports_dir / f'report_{date_str_compact}.md'
        market_file = self.reports_dir / f'market_review_{date_str_compact}.md'
        
        result = {
            'date': target_date,
            'marketReview': None,
            'decisions': []
        }
        
        # 读取大盘复盘
        if market_file.exists():
            result['marketReview'] = self._parse_market_review(market_file.read_text(encoding='utf-8'))
        
        # 读取个股决策报告
        if report_file.exists():
            result['decisions'] = self._parse_stock_report(report_file.read_text(encoding='utf-8'))
        
        # 如果没有任何报告数据，返回 None
        if result['marketReview'] is None and not result['decisions']:
            return None
        
        return result
    
    def _parse_market_review(self, content: str) -> Optional[Dict[str, str]]:
        """
        解析大盘复盘报告内容
        
        Args:
            content: Markdown 格式的报告内容
            
        Returns:
            解析后的市场复盘数据
        """
        sections = {
            'summary': '',
            'indexComment': '',
            'capitalFlow': '',
            'hotTopics': '',
            'outlook': '',
            'riskWarning': ''
        }
        
        # 使用正则表达式提取各部分内容
        # 市场总结 - 一、市场总结
        summary_match = re.search(r'### 一、市场总结\s*\n([^#]+?)(?=###|$)', content)
        if summary_match:
            sections['summary'] = summary_match.group(1).strip()
        
        # 指数点评 - 二、指数点评
        index_match = re.search(r'### 二、指数点评\s*\n([^#]+?)(?=###|$)', content)
        if index_match:
            sections['indexComment'] = index_match.group(1).strip()
        
        # 资金动向 - 三、资金动向
        capital_match = re.search(r'### 三、资金动向\s*\n([^#]+?)(?=###|$)', content)
        if capital_match:
            sections['capitalFlow'] = capital_match.group(1).strip()
        
        # 热点解读 - 四、热点解读
        hot_match = re.search(r'### 四、热点解读\s*\n([^#]+?)(?=###|$)', content)
        if hot_match:
            sections['hotTopics'] = hot_match.group(1).strip()
        
        # 后市展望 - 五、后市展望
        outlook_match = re.search(r'### 五、后市展望\s*\n([^#]+?)(?=###|$)', content)
        if outlook_match:
            sections['outlook'] = outlook_match.group(1).strip()
        
        # 风险提示 - 六、风险提示
        risk_match = re.search(r'### 六、风险提示\s*\n([^#]+?)(?=###|$)', content)
        if risk_match:
            sections['riskWarning'] = risk_match.group(1).strip()
        
        return sections if any(sections.values()) else None
    
    def _parse_stock_report(self, content: str) -> List[Dict[str, Any]]:
        """
        解析个股分析报告内容
        
        Args:
            content: Markdown 格式的报告内容
            
        Returns:
            个股决策列表
        """
        decisions = []
        
        # 提取报告摘要中的统计信息
        summary_match = re.search(r'> 共分析 \*\*(\d+)\*\* 只.*🟢买入:(\d+).*🟡观望:(\d+).*🔴卖出:(\d+)', content)
        
        # 使用finditer找到所有股票部分
        # 模式：## [emoji] 股票名称 (代码)
        # 注意：股票名称中可能包含空格，代码在括号中
        # 匹配到行尾，使用多行模式
        stock_pattern = r'^##\s+([💚⚪🔴])\s+(.+)$'
        
        matches = list(re.finditer(stock_pattern, content, re.MULTILINE))
        
        for i, match in enumerate(matches):
            emoji = match.group(1)
            header_line = match.group(2).strip()
            
            # 提取股票名称和代码
            # header_line 格式: "股票名称 (代码)" 或 "股票名称(代码)"
            # 从右往左找最后一个括号，避免股票名称中有括号
            if '(' in header_line and ')' in header_line:
                # 找到最后一个 '(' 和对应的 ')'
                code_start = header_line.rfind('(')
                code_end = header_line.rfind(')')
                if code_start < code_end:
                    name = header_line[:code_start].strip()
                    code = header_line[code_start + 1:code_end].strip()
                else:
                    continue
            else:
                continue
            
            # 获取该股票的内容（从当前匹配位置到下一个匹配位置或文件结束）
            start_pos = match.end()
            if i + 1 < len(matches):
                section_content = content[start_pos:matches[i + 1].start()]
            else:
                section_content = content[start_pos:]
            
            decision = self._parse_single_stock_content(name, code, emoji, section_content)
            if decision:
                decisions.append(decision)
        
        return decisions
    
    def _parse_single_stock_content(self, name: str, code: str, signal_emoji: str, section: str) -> Optional[Dict[str, Any]]:
        """
        解析单个股票的分析内容
        
        Args:
            name: 股票名称
            code: 股票代码
            signal_emoji: 信号emoji（💚买入/⚪观望/🔴卖出）
            section: 单个股票的分析内容
            
        Returns:
            解析后的股票决策数据
        """
        
        # 根据 emoji 判断信号类型
        signal_map = {
            '💚': 'buy',
            '⚪': 'watch',
            '🔴': 'sell'
        }
        signal = signal_map.get(signal_emoji, 'watch')
        
        # 提取评分
        score_match = re.search(r'评分[:\s]*(\d+)', section)
        score = int(score_match.group(1)) if score_match else 50
        
        # 提取当前价
        price_match = re.search(r'当前价\s*\|\s*([\d.]+)', section)
        price = float(price_match.group(1)) if price_match else 0.0
        
        # 提取乖离率
        bias_match = re.search(r'乖离率\([^)]+\)\s*\|\s*([+-]?[\d.]+)%', section)
        bias = float(bias_match.group(1)) if bias_match else 0.0
        
        # 提取趋势强度
        trend_match = re.search(r'趋势强度[:\s]*(\d+)', section)
        trend = int(trend_match.group(1)) if trend_match else 50
        
        # 提取决策指令（一句话决策）
        decision_match = re.search(r'> \*\*一句话决策\*\*[:：]\s*([^\n]+)', section)
        if not decision_match:
            decision_match = re.search(r'一句话决策[:\s]*([^\n]+)', section)
        decision = decision_match.group(1).strip() if decision_match else ''
        
        # 提取基本面要点
        fundamentals = []
        # 从重要信息速览中提取
        sentiment_match = re.search(r'\*\*💭 舆情情绪\*\*[:：]\s*([^\n]+)', section)
        if sentiment_match:
            fundamentals.append(f"舆情: {sentiment_match.group(1).strip()}")
        
        expectation_match = re.search(r'\*\*📊 业绩预期\*\*[:：]\s*([^\n]+)', section)
        if expectation_match:
            fundamentals.append(f"业绩: {expectation_match.group(1).strip()}")
        
        # 提取最新动态
        news_match = re.search(r'\*\*📢 最新动态\*\*[:：]\s*([^\n]+)', section)
        if news_match:
            fundamentals.append(f"动态: {news_match.group(1).strip()}")
        
        # 如果没有提取到基本面信息，使用默认信息
        if not fundamentals:
            fundamentals = ['暂无详细基本面数据']
        
        # 提取操作建议（空仓者建议）
        suggestion_match = re.search(r'\| 🆕 \*\*空仓者\*\* \|\s*([^\|]+?)\s*\|', section)
        if not suggestion_match:
            suggestion_match = re.search(r'空仓者.*建议[:：]\s*([^\n]+)', section)
        suggestion = suggestion_match.group(1).strip() if suggestion_match else '建议观望，等待机会。'
        
        return {
            'code': code,
            'name': name,
            'signal': signal,
            'score': score,
            'price': price,
            'bias': bias,
            'trend': trend,
            'decision': decision,
            'fundamentals': fundamentals,
            'suggestion': suggestion
        }


# ============================================================
# 便捷函数
# ============================================================

def get_config_service() -> ConfigService:
    """获取配置服务实例"""
    return ConfigService()


def get_analysis_service() -> AnalysisService:
    """获取分析服务单例"""
    return AnalysisService.get_instance()


def get_history_report_service() -> HistoryReportService:
    """获取历史报告服务实例"""
    return HistoryReportService()
