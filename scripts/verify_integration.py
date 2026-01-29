#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合验证脚本 - 检查所有必要文件和依赖
"""

import sys
from pathlib import Path
from typing import List, Tuple

def check_file(filepath: str, description: str) -> Tuple[bool, str]:
    """检查文件是否存在"""
    if Path(filepath).exists():
        return True, f"✅ {description}: {filepath}"
    else:
        return False, f"❌ {description}: {filepath} (未找到)"

def check_import(module_name: str, description: str) -> Tuple[bool, str]:
    """检查模块是否可导入"""
    try:
        __import__(module_name)
        return True, f"✅ {description}: {module_name}"
    except ImportError as e:
        return False, f"❌ {description}: {module_name} (导入失败: {e})"

def main():
    print("=" * 80)
    print("🔍 整合验证检查")
    print("=" * 80)
    print()
    
    all_checks = []
    
    # 1. 检查核心文件
    print("【1. 核心文件检查】")
    print()
    
    core_files = [
        ("Selector.py", "选股策略模块"),
        ("select_stock.py", "选股执行模块"),
        ("strategy_screener.py", "策略选股器"),
        ("auto_screen_and_analyze.py", "自动化脚本"),
        ("selector_configs.json", "策略配置文件"),
    ]
    
    for filepath, desc in core_files:
        success, msg = check_file(filepath, desc)
        all_checks.append(success)
        print(msg)
    
    print()
    
    # 2. 检查可选文件
    print("【2. 可选文件检查】")
    print()
    
    optional_files = [
        ("stocklist.csv", "股票列表文件（用于行业分析）"),
        ("SectorShift.py", "行业分析模块"),
        ("data/", "K线数据目录"),
    ]
    
    for filepath, desc in optional_files:
        success, msg = check_file(filepath, desc)
        print(msg)
    
    print()
    
    # 3. 检查 Python 依赖
    print("【3. Python 依赖检查】")
    print()
    
    dependencies = [
        ("pandas", "数据处理"),
        ("numpy", "数值计算"),
        ("scipy", "科学计算（StockTradebyZ 需要）"),
        ("tqdm", "进度条（StockTradebyZ 需要）"),
        ("akshare", "数据源"),
        ("google.generativeai", "Gemini AI"),
        ("dotenv", "环境变量"),
        ("sqlalchemy", "数据库"),
    ]
    
    for module, desc in dependencies:
        success, msg = check_import(module, desc)
        all_checks.append(success)
        print(msg)
    
    print()
    
    # 4. 检查配置
    print("【4. 配置检查】")
    print()
    
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env 文件存在")
        
        # 读取并检查关键配置
        with open(env_file, 'r') as f:
            content = f.read()
            
        if "GEMINI_API_KEY" in content:
            print("✅ 已配置 GEMINI_API_KEY")
        else:
            print("⚠️  未配置 GEMINI_API_KEY（AI 分析将不可用）")
            
        if any(key in content for key in ["WECHAT_WEBHOOK_URL", "FEISHU_WEBHOOK_URL", "TELEGRAM_BOT_TOKEN"]):
            print("✅ 已配置通知渠道")
        else:
            print("⚠️  未配置通知渠道（将不发送推送）")
    else:
        print("⚠️  .env 文件不存在（请创建并配置）")
        all_checks.append(False)
    
    print()
    
    # 5. 检查数据目录
    print("【5. 数据目录检查】")
    print()
    
    data_dir = Path("data")
    if data_dir.exists():
        csv_files = list(data_dir.glob("*.csv"))
        if csv_files:
            print(f"✅ 找到 {len(csv_files)} 个 CSV 数据文件")
            # 显示前 5 个
            for f in csv_files[:5]:
                print(f"   - {f.name}")
            if len(csv_files) > 5:
                print(f"   ... 还有 {len(csv_files) - 5} 个文件")
        else:
            print("⚠️  data 目录为空，请添加 K 线数据")
            all_checks.append(False)
    else:
        print("❌ data 目录不存在")
        all_checks.append(False)
    
    print()
    
    # 6. 测试导入
    print("【6. 模块导入测试】")
    print()
    
    try:
        from strategy_screener import StrategyScreener
        print("✅ 成功导入 StrategyScreener")
        
        # 尝试列出策略
        screener = StrategyScreener(data_dir="./data")
        strategies = list(screener.strategies.keys())
        print(f"✅ 加载了 {len(strategies)} 个策略:")
        for strategy in strategies:
            enabled = screener.strategies[strategy].get('enabled', True)
            status = "启用" if enabled else "禁用"
            print(f"   - {strategy} ({status})")
    except Exception as e:
        print(f"❌ 导入测试失败: {e}")
        all_checks.append(False)
    
    print()
    
    # 总结
    print("=" * 80)
    if all(all_checks):
        print("🎉 整合验证通过！所有检查都成功")
        print()
        print("你可以开始使用了：")
        print("  ./run.sh")
        print("  或")
        print("  python auto_screen_and_analyze.py")
        return 0
    else:
        print("⚠️  部分检查未通过，请根据上述提示完成整合")
        print()
        print("参考文档：")
        print("  cat INTEGRATION_COMPLETE.md")
        print("  cat INTEGRATION_GUIDE.md")
        return 1
    print("=" * 80)

if __name__ == "__main__":
    sys.exit(main())
