#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===================================
自动选股+分析一体化脚本
===================================

功能：
1. 使用 StockTradebyZ 的多种战法自动选股
2. 对选出的股票进行 AI 深度分析
3. 生成综合分析报告并推送通知

使用方式：
    python auto_screen_and_analyze.py
    python auto_screen_and_analyze.py --data-dir ./data
    python auto_screen_and_analyze.py --strategy 少妇战法
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from main import StockAnalysisPipeline, setup_logging
from screeners.strategy_screener import StrategyScreener
from services.notification import NotificationService

logger = logging.getLogger(__name__)


class AutoScreenAndAnalyze:
    """自动选股+分析一体化控制器"""
    
    def __init__(
        self,
        data_dir: str = "./data",
        strategy_config: str = None,
        specific_strategy: str = None
    ):
        """
        初始化
        
        Args:
            data_dir: K线数据目录
            strategy_config: 策略配置文件
            specific_strategy: 指定运行的策略名称（可选）
        """
        self.config = get_config()
        self.data_dir = Path(data_dir)
        self.strategy_config = strategy_config
        self.specific_strategy = specific_strategy
        
        # 初始化各模块
        self.screener = StrategyScreener(
            data_dir=str(self.data_dir),
            config_file=strategy_config
        )
        self.pipeline = StockAnalysisPipeline(config=self.config)
        self.notifier = NotificationService()
        
        logger.info("自动选股+分析系统初始化完成")
    
    def run(self, send_notification: bool = True) -> Dict:
        """
        执行完整流程
        
        Args:
            send_notification: 是否发送通知
        
        Returns:
            执行结果字典
        """
        start_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info("🚀 开始自动选股+分析流程")
        logger.info(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        # Step 1: 策略选股
        logger.info("\n📊 Step 1: 执行策略选股...")
        
        if self.specific_strategy:
            # 运行指定策略
            selected_stocks = self.screener.run_strategy(self.specific_strategy)
            strategy_results = {self.specific_strategy: selected_stocks}
        else:
            # 运行所有策略
            strategy_results = self.screener.run_all_strategies()
        
        # 获取所有选中的股票（去重）
        all_selected = set()
        for stocks in strategy_results.values():
            all_selected.update(stocks)
        
        all_selected = sorted(list(all_selected))
        
        logger.info(f"✅ 选股完成: 共选出 {len(all_selected)} 只股票")
        
        if not all_selected:
            logger.warning("⚠️ 未选出任何股票，流程结束")
            return {
                'success': True,
                'selected_stocks': [],
                'strategy_results': strategy_results,
                'analysis_results': [],
                'elapsed_time': (datetime.now() - start_time).total_seconds()
            }
        
        # Step 2: AI 深度分析
        logger.info(f"\n🤖 Step 2: 对选中的 {len(all_selected)} 只股票进行 AI 深度分析...")
        
        analysis_results = self.pipeline.run(
            stock_codes=all_selected,
            dry_run=False,
            send_notification=False  # 稍后统一发送
        )
        
        logger.info(f"✅ 分析完成: 成功分析 {len(analysis_results)} 只股票")
        
        # Step 3: 生成综合报告
        logger.info("\n📝 Step 3: 生成综合报告...")
        
        report = self._generate_comprehensive_report(
            strategy_results,
            analysis_results
        )
        
        # 保存报告
        report_file = self._save_report(report)
        logger.info(f"✅ 报告已保存: {report_file}")
        
        # Step 4: 发送通知
        if send_notification and self.notifier.is_available():
            logger.info("\n📢 Step 4: 发送通知...")
            
            # 生成精简版报告用于推送
            notification_content = self._generate_notification_content(
                strategy_results,
                analysis_results
            )
            
            success = self.notifier.send(notification_content)
            if success:
                logger.info("✅ 通知发送成功")
            else:
                logger.warning("⚠️ 通知发送失败")
        
        # 统计
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "=" * 80)
        logger.info("🎉 自动选股+分析流程完成")
        logger.info(f"⏱️ 总耗时: {elapsed_time:.1f} 秒")
        logger.info(f"📊 选股数量: {len(all_selected)}")
        logger.info(f"✅ 分析成功: {len(analysis_results)}")
        logger.info("=" * 80)
        
        return {
            'success': True,
            'selected_stocks': all_selected,
            'strategy_results': strategy_results,
            'analysis_results': analysis_results,
            'elapsed_time': elapsed_time,
            'report_file': report_file
        }
    
    def _generate_comprehensive_report(
        self,
        strategy_results: Dict[str, List[str]],
        analysis_results: List
    ) -> str:
        """生成综合报告"""
        lines = [
            "=" * 80,
            "📊 自动选股+AI分析综合报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            ""
        ]
        
        # Part 1: 策略选股结果
        lines.append("【第一部分：策略选股结果】")
        lines.append("")
        
        all_stocks = set()
        for stocks in strategy_results.values():
            all_stocks.update(stocks)
        
        lines.append(f"📈 总计: {len(strategy_results)} 个策略，选出 {len(all_stocks)} 只不重复股票")
        lines.append("")
        
        # 各策略详情
        for strategy_name, stocks in strategy_results.items():
            lines.append(f"🎯 {strategy_name}")
            lines.append(f"   选中: {len(stocks)} 只")
            if stocks:
                lines.append(f"   代码: {', '.join(stocks)}")
            lines.append("")
        
        # 股票出现频次
        stock_count = {}
        for stocks in strategy_results.values():
            for stock in stocks:
                stock_count[stock] = stock_count.get(stock, 0) + 1
        
        if stock_count:
            lines.append("📊 股票出现频次（多策略共振）")
            sorted_stocks = sorted(stock_count.items(), key=lambda x: x[1], reverse=True)
            for stock, count in sorted_stocks:
                if count > 1:
                    lines.append(f"   {stock}: {count} 个策略共同选中 ⭐")
            lines.append("")
        
        # Part 2: AI 分析结果
        lines.append("")
        lines.append("【第二部分：AI 深度分析结果】")
        lines.append("")
        
        if not analysis_results:
            lines.append("⚠️ 暂无分析结果")
        else:
            lines.append(f"✅ 成功分析 {len(analysis_results)} 只股票")
            lines.append("")
            
            # 按评分排序
            sorted_results = sorted(
                analysis_results,
                key=lambda x: x.sentiment_score,
                reverse=True
            )
            
            for i, result in enumerate(sorted_results, 1):
                emoji = result.get_emoji()
                lines.append(f"{i}. {emoji} {result.name}({result.code})")
                lines.append(f"   操作建议: {result.operation_advice}")
                lines.append(f"   综合评分: {result.sentiment_score}/100")
                lines.append(f"   趋势预测: {result.trend_prediction}")
                
                # 显示该股票被哪些策略选中
                selected_by = [
                    name for name, stocks in strategy_results.items()
                    if result.code in stocks
                ]
                if selected_by:
                    lines.append(f"   选中策略: {', '.join(selected_by)}")
                
                if result.analysis_summary:
                    summary = result.analysis_summary[:200]
                    lines.append(f"   分析摘要: {summary}...")
                
                lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _generate_notification_content(
        self,
        strategy_results: Dict[str, List[str]],
        analysis_results: List
    ) -> str:
        """生成推送通知内容（精简版）"""
        lines = [
            "🎯 自动选股+分析日报",
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ""
        ]
        
        # 选股统计
        all_stocks = set()
        for stocks in strategy_results.values():
            all_stocks.update(stocks)
        
        lines.append(f"📊 选股: {len(all_stocks)} 只")
        lines.append(f"🤖 分析: {len(analysis_results)} 只")
        lines.append("")
        
        # Top 3 推荐
        if analysis_results:
            sorted_results = sorted(
                analysis_results,
                key=lambda x: x.sentiment_score,
                reverse=True
            )[:3]
            
            lines.append("⭐ Top 3 推荐:")
            for i, result in enumerate(sorted_results, 1):
                emoji = result.get_emoji()
                lines.append(
                    f"{i}. {emoji} {result.name}({result.code}) "
                    f"{result.operation_advice} {result.sentiment_score}分"
                )
            lines.append("")
        
        # 多策略共振
        stock_count = {}
        for stocks in strategy_results.values():
            for stock in stocks:
                stock_count[stock] = stock_count.get(stock, 0) + 1
        
        multi_strategy = [
            stock for stock, count in stock_count.items()
            if count > 1
        ]
        
        if multi_strategy:
            lines.append(f"🔥 多策略共振: {', '.join(multi_strategy)}")
            lines.append("")
        
        lines.append("详细报告已保存到本地")
        
        return "\n".join(lines)
    
    def _save_report(self, report: str) -> Path:
        """保存报告到文件"""
        report_dir = Path("./reports")
        report_dir.mkdir(exist_ok=True)
        
        filename = f"auto_screen_analyze_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = report_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return filepath


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='自动选股+AI分析一体化脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python auto_screen_and_analyze.py                    # 运行所有策略
  python auto_screen_and_analyze.py --strategy 少妇战法  # 运行指定策略
  python auto_screen_and_analyze.py --no-notify        # 不发送通知
  python auto_screen_and_analyze.py --debug            # 调试模式
        '''
    )
    
    parser.add_argument(
        '--data-dir',
        default='./data',
        help='K线数据目录（默认: ./data）'
    )
    
    parser.add_argument(
        '--config',
        help='策略配置文件路径（可选）'
    )
    
    parser.add_argument(
        '--strategy',
        help='指定运行单个策略（可选）'
    )
    
    parser.add_argument(
        '--no-notify',
        action='store_true',
        help='不发送推送通知'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式'
    )
    
    args = parser.parse_args()
    
    # 配置日志
    config = get_config()
    setup_logging(debug=args.debug, log_dir=config.log_dir)
    
    try:
        # 创建控制器
        controller = AutoScreenAndAnalyze(
            data_dir=args.data_dir,
            strategy_config=args.config,
            specific_strategy=args.strategy
        )
        
        # 执行流程
        result = controller.run(send_notification=not args.no_notify)
        
        if result['success']:
            logger.info("\n✅ 执行成功")
            return 0
        else:
            logger.error("\n❌ 执行失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断")
        return 130
    except Exception as e:
        logger.exception(f"\n❌ 执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
