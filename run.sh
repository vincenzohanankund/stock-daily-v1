#!/bin/bash
# -*- coding: utf-8 -*-
"""
快速启动脚本 - 自动选股+分析
"""

echo "=========================================="
echo "🚀 自动选股+AI分析系统"
echo "=========================================="
echo ""

# 检查必要文件
if [ ! -f "screeners/Selector.py" ]; then
    echo "⚠️  警告: 未找到 screeners/Selector.py"
    echo "请确保项目结构正确"
    exit 1
fi

if [ ! -d "data" ]; then
    echo "⚠️  警告: 未找到 data 目录"
    echo "请先准备 K 线数据"
    exit 1
fi

# 显示菜单
echo "请选择运行模式："
echo ""
echo "1. 策略选股 + AI 分析（推荐）"
echo "2. 仅策略选股"
echo "3. 仅 AI 分析（需先配置 STOCK_LIST）"
echo "4. 全市场选股（使用内置选股器）"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🎯 运行模式: 策略选股 + AI 分析"
        echo ""
        python3 scripts/auto_screen_and_analyze.py
        ;;
    2)
        echo ""
        echo "🎯 运行模式: 仅策略选股"
        echo ""
        python3 main.py --strategy-screen --no-notify
        ;;
    3)
        echo ""
        echo "🎯 运行模式: 仅 AI 分析"
        echo ""
        python3 main.py
        ;;
    4)
        echo ""
        echo "🎯 运行模式: 全市场选股"
        echo ""
        python3 main.py --screen --auto-analyze
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ 执行完成"
echo "=========================================="
