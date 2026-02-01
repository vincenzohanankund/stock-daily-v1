# -*- coding: utf-8 -*-
"""
===================================
Web 模板层 - HTML 页面生成
===================================

职责：
1. 生成 HTML 页面
2. 管理 CSS 样式
3. 提供可复用的页面组件

技术栈：原生 HTML + Tailwind CSS + Alpine.js
"""

from __future__ import annotations

import html
import os
from typing import Optional


# ============================================================
# 模板目录配置
# ============================================================

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


# ============================================================
# 模板渲染函数
# ============================================================

def render_template(template_name: str, **context) -> str:
    """
    渲染模板文件
    
    Args:
        template_name: 模板文件名 (如 "index.html")
        **context: 模板变量
        
    Returns:
        渲染后的 HTML 字符串
    """
    template_path = os.path.join(TEMPLATES_DIR, template_name)
    
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except FileNotFoundError:
        return f"<!-- Template not found: {template_name} -->"
    except Exception as e:
        return f"<!-- Error loading template {template_name}: {e} -->"
    
    # 处理模板继承 ({% extends %})
    if "{% extends" in template_content:
        template_content = _process_extends(template_content, **context)
    
    # 处理包含 ({% include %})
    template_content = _process_includes(template_content, **context)
    
    # 处理块 ({% block %})
    template_content = _process_blocks(template_content, **context)
    
    # 处理变量 ({{ var }})
    template_content = _process_variables(template_content, **context)
    
    # 处理条件 ({% if %})
    template_content = _process_conditionals(template_content, **context)
    
    # 处理默认值过滤器 (|default())
    template_content = _process_default_filters(template_content, **context)
    
    return template_content


def _process_extends(template_content: str, **context) -> str:
    """处理模板继承"""
    import re
    
    extends_match = re.search(r'{%\s*extends\s*["\'](.+?)["\']\s*%}', template_content)
    if not extends_match:
        return template_content
    
    parent_name = extends_match.group(1)
    parent_path = os.path.join(TEMPLATES_DIR, parent_name)
    
    try:
        with open(parent_path, "r", encoding="utf-8") as f:
            parent_content = f.read()
    except FileNotFoundError:
        return template_content
    
    # 提取子模板中的块内容
    child_blocks = {}
    block_pattern = r'{%\s*block\s+(\w+)\s*%}(.*?){%\s*endblock\s*%}'
    for match in re.finditer(block_pattern, template_content, re.DOTALL):
        block_name = match.group(1)
        block_content = match.group(2)
        child_blocks[block_name] = block_content
    
    # 替换父模板中的块
    def replace_block(match):
        block_name = match.group(1)
        if block_name in child_blocks:
            return child_blocks[block_name]
        return match.group(2)  # 保留父模板的默认内容
    
    parent_content = re.sub(block_pattern, replace_block, parent_content, flags=re.DOTALL)
    
    return parent_content


def _process_includes(template_content: str, **context) -> str:
    """处理包含指令"""
    import re
    
    include_pattern = r'{%\s*include\s*["\'](.+?)["\']\s*%}'
    
    def replace_include(match):
        include_name = match.group(1)
        include_path = os.path.join(TEMPLATES_DIR, include_name)
        
        try:
            with open(include_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return f"<!-- Include not found: {include_name} -->"
    
    return re.sub(include_pattern, replace_include, template_content)


def _process_blocks(template_content: str, **context) -> str:
    """处理块定义 (移除块标记)"""
    import re
    
    # 移除 {% block %} 和 {% endblock %} 标记
    template_content = re.sub(r'{%\s*block\s+\w+\s*%}', '', template_content)
    template_content = re.sub(r'{%\s*endblock\s*%}', '', template_content)
    
    return template_content


def _process_variables(template_content: str, **context) -> str:
    """处理模板变量"""
    import re
    
    def replace_var(match):
        var_expr = match.group(1).strip()
        
        # 处理过滤器
        if "|" in var_expr:
            var_name, filters = var_expr.split("|", 1)
            var_name = var_name.strip()
            value = context.get(var_name, "")
            
            # 应用过滤器
            for filter_expr in filters.split("|"):
                filter_expr = filter_expr.strip()
                if filter_expr == "default(\"\")" or filter_expr.startswith("default("):
                    if not value:
                        default_match = re.search(r'default\(["\']?(.*?)["\']?\)', filter_expr)
                        value = default_match.group(1) if default_match else ""
                elif filter_expr == "e" or filter_expr == "escape":
                    value = html.escape(str(value))
            return str(value)
        
        # 简单变量
        value = context.get(var_expr, "")
        return html.escape(str(value)) if value else ""
    
    return re.sub(r'{{\s*(.+?)\s*}}', replace_var, template_content)


def _process_conditionals(template_content: str, **context) -> str:
    """处理条件语句"""
    import re
    
    # 简单的 if/endif 处理
    if_pattern = r'{%\s*if\s+(.+?)\s*%}(.*?){%\s*endif\s*%}'
    
    def replace_if(match):
        condition = match.group(1).strip()
        content = match.group(2)
        
        # 支持简单的变量存在性检查
        if condition.startswith("not "):
            var_name = condition[4:].strip()
            if context.get(var_name):
                return ""
            return content
        else:
            var_name = condition
            if context.get(var_name):
                return content
            return ""
    
    return re.sub(if_pattern, replace_if, template_content, flags=re.DOTALL)


def _process_default_filters(template_content: str, **context) -> str:
    """处理默认值过滤器"""
    import re
    
    # 处理 {{ var|default("value") }}
    pattern = r'{{\s*(\w+)\s*\|\s*default\(["\']?(.*?)["\']?\)\s*}}'
    
    def replace_default(match):
        var_name = match.group(1)
        default_value = match.group(2)
        value = context.get(var_name)
        return html.escape(str(value)) if value else default_value
    
    return re.sub(pattern, replace_default, template_content)


# ============================================================
# 页面渲染函数
# ============================================================

def render_index_page(
    stock_list: str = "",
    env_filename: str = ".env"
) -> bytes:
    """
    渲染服务首页
    
    Args:
        stock_list: 自选股列表
        env_filename: 环境文件名
        
    Returns:
        HTML 字节内容
    """
    html_content = render_template(
        "index.html",
        page_name="index",
        stock_list=stock_list,
        env_filename=env_filename
    )
    return html_content.encode("utf-8")


def render_stock_analysis_page(
    stock_list: str = "",
    env_filename: str = ".env",
    message: Optional[str] = None
) -> bytes:
    """
    渲染个股分析页面
    
    Args:
        stock_list: 自选股列表
        env_filename: 环境文件名
        message: 提示消息
        
    Returns:
        HTML 字节内容
    """
    html_content = render_template(
        "stock_analysis.html",
        page_name="stock_analysis",
        stock_list=stock_list,
        env_filename=env_filename,
        message=message
    )
    return html_content.encode("utf-8")


def render_history_page() -> bytes:
    """
    渲染历史报告页面
    
    Returns:
        HTML 字节内容
    """
    html_content = render_template(
        "history.html",
        page_name="history"
    )
    return html_content.encode("utf-8")


def render_stock_picker_page() -> bytes:
    """
    渲染选股助手页面
    
    Returns:
        HTML 字节内容
    """
    html_content = render_template(
        "stock_picker.html",
        page_name="stock_picker"
    )
    return html_content.encode("utf-8")


def render_config_page(
    stock_list: str,
    env_filename: str,
    message: Optional[str] = None
) -> bytes:
    """
    渲染配置页面 (兼容旧接口，重定向到个股分析页面)
    
    Args:
        stock_list: 当前自选股列表
        env_filename: 环境文件名
        message: 可选的提示消息
        
    Returns:
        HTML 字节内容
    """
    return render_stock_analysis_page(stock_list, env_filename, message)


def render_error_page(
    status_code: int,
    message: str,
    details: Optional[str] = None
) -> bytes:
    """
    渲染错误页面
    
    Args:
        status_code: HTTP 状态码
        message: 错误消息
        details: 详细信息
        
    Returns:
        HTML 字节内容
    """
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>错误 {status_code} - Alpha Quant</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        'geek-bg': '#0f172a',
                        'geek-card': '#1e293b',
                        'geek-border': '#334155',
                        'accent': '#6366f1',
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{ background-color: #020617; color: #cbd5e1; min-height: 100vh; }}
    </style>
</head>
<body class="flex items-center justify-center">
    <div class="text-center p-8">
        <div class="inline-flex items-center justify-center p-4 bg-red-500/10 border border-red-500/30 rounded-2xl mb-6">
            <i class="fa-solid fa-triangle-exclamation text-red-400 text-4xl"></i>
        </div>
        <h1 class="text-4xl font-bold text-white mb-4">{status_code}</h1>
        <p class="text-xl text-slate-400 mb-2">{html.escape(message)}</p>
        {f'<p class="text-sm text-slate-500 mb-6">{html.escape(details)}</p>' if details else ''}
        <a href="/" class="inline-flex items-center px-6 py-3 bg-accent hover:bg-accent/80 text-white font-semibold rounded-lg transition-all">
            <i class="fa-solid fa-arrow-left mr-2"></i>
            返回首页
        </a>
    </div>
</body>
</html>"""
    return html_content.encode("utf-8")


# ============================================================
# 向后兼容
# ============================================================

# 保留旧的 BASE_CSS 常量以兼容可能的引用
BASE_CSS = """
/* Legacy CSS - 已迁移到 Tailwind CSS */
:root {{
    --primary: #6366f1;
    --geek-bg: #0f172a;
    --geek-card: #1e293b;
    --geek-border: #334155;
}}
"""


def render_base(
    title: str,
    content: str,
    extra_css: str = "",
    extra_js: str = ""
) -> str:
    """
    渲染基础 HTML 模板 (向后兼容)
    
    注意: 新代码应使用 render_template() 函数
    """
    return f"""<!doctype html>
<html lang="zh-CN" class="dark">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body {{ background-color: #020617; color: #cbd5e1; }}
    {extra_css}
  </style>
</head>
<body>
  {content}
  {extra_js}
</body>
</html>"""


def render_toast(message: str, toast_type: str = "success") -> str:
    """
    渲染 Toast 通知 (向后兼容)
    """
    icon_map = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️"
    }
    icon = icon_map.get(toast_type, "ℹ️")
    color_class = "green" if toast_type == "success" else "red" if toast_type == "error" else "yellow"
    
    return f"""
    <div id="toast" class="fixed bottom-4 left-1/2 -translate-x-1/2 bg-slate-800 border-l-4 border-{color_class}-500 text-white px-6 py-3 rounded shadow-lg flex items-center gap-3 z-50">
        <span>{icon}</span>
        <span>{html.escape(message)}</span>
    </div>
    <script>
        setTimeout(() => {{
            const toast = document.getElementById('toast');
            if (toast) toast.remove();
        }}, 3000);
    </script>
    """
