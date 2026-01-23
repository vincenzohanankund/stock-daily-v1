# -*- coding: utf-8 -*-
"""
===================================
大盤覆盤分析模塊
===================================

職責：
1. 獲取大盤指數數據（上證、深證、創業板）
2. 搜索市場新聞形成覆盤情報
3. 使用大模型生成每日大盤覆盤報告
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

import akshare as ak
import pandas as pd

from config import get_config
from search_service import SearchService

logger = logging.getLogger(__name__)


@dataclass
class MarketIndex:
    """大盤指數數據"""
    code: str                    # 指數代碼
    name: str                    # 指數名稱
    current: float = 0.0         # 當前點位
    change: float = 0.0          # 漲跌點數
    change_pct: float = 0.0      # 漲跌幅(%)
    open: float = 0.0            # 開盤點位
    high: float = 0.0            # 最高點位
    low: float = 0.0             # 最低點位
    prev_close: float = 0.0      # 昨收點位
    volume: float = 0.0          # 成交量（手）
    amount: float = 0.0          # 成交額（元）
    amplitude: float = 0.0       # 振幅(%)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'current': self.current,
            'change': self.change,
            'change_pct': self.change_pct,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'amount': self.amount,
            'amplitude': self.amplitude,
        }


@dataclass
class MarketOverview:
    """市場概覽數據"""
    date: str                           # 日期
    indices: List[MarketIndex] = field(default_factory=list)  # 主要指數
    up_count: int = 0                   # 上漲家數
    down_count: int = 0                 # 下跌家數
    flat_count: int = 0                 # 平盤家數
    limit_up_count: int = 0             # 漲停家數
    limit_down_count: int = 0           # 跌停家數
    total_amount: float = 0.0           # 兩市成交額（億元）
    north_flow: float = 0.0             # 北向資金淨流入（億元）
    
    # 板塊漲幅榜
    top_sectors: List[Dict] = field(default_factory=list)     # 漲幅前5板塊
    bottom_sectors: List[Dict] = field(default_factory=list)  # 跌幅前5板塊


class MarketAnalyzer:
    """
    大盤覆盤分析器
    
    功能：
    1. 獲取大盤指數實時行情
    2. 獲取市場漲跌統計
    3. 獲取板塊漲跌榜
    4. 搜索市場新聞
    5. 生成大盤覆盤報告
    """
    
    # 主要指數代碼
    MAIN_INDICES = {
        'sh000001': '上證指數',
        'sz399001': '深證成指',
        'sz399006': '創業板指',
        'sh000688': '科創50',
        'sh000016': '上證50',
        'sh000300': '滬深300',
    }
    
    def __init__(self, search_service: Optional[SearchService] = None, analyzer=None):
        """
        初始化大盤分析器
        
        Args:
            search_service: 搜索服務實例
            analyzer: AI分析器實例（用於調用LLM）
        """
        self.config = get_config()
        self.search_service = search_service
        self.analyzer = analyzer
        
    def get_market_overview(self) -> MarketOverview:
        """
        獲取市場概覽數據
        
        Returns:
            MarketOverview: 市場概覽數據對象
        """
        today = datetime.now().strftime('%Y-%m-%d')
        overview = MarketOverview(date=today)
        
        # 1. 獲取主要指數行情
        overview.indices = self._get_main_indices()
        
        # 2. 獲取漲跌統計
        self._get_market_statistics(overview)
        
        # 3. 獲取板塊漲跌榜
        self._get_sector_rankings(overview)
        
        # 4. 獲取北向資金（可選）
        # self._get_north_flow(overview)
        
        return overview

    def _call_akshare_with_retry(self, fn, name: str, attempts: int = 2):
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                return fn()
            except Exception as e:
                last_error = e
                logger.warning(f"[大盤] {name} 獲取失敗 (attempt {attempt}/{attempts}): {e}")
                if attempt < attempts:
                    time.sleep(min(2 ** attempt, 5))
        logger.error(f"[大盤] {name} 最終失敗: {last_error}")
        return None
    
    def _get_main_indices(self) -> List[MarketIndex]:
        """獲取主要指數實時行情"""
        indices = []
        
        try:
            logger.info("[大盤] 獲取主要指數實時行情...")
            
            # 使用 akshare 獲取指數行情（新浪財經接口，包含深市指數）
            df = self._call_akshare_with_retry(ak.stock_zh_index_spot_sina, "指數行情", attempts=2)
            
            if df is not None and not df.empty:
                for code, name in self.MAIN_INDICES.items():
                    # 查找對應指數
                    row = df[df['代碼'] == code]
                    if row.empty:
                        # 嘗試帶前綴查找
                        row = df[df['代碼'].str.contains(code)]
                    
                    if not row.empty:
                        row = row.iloc[0]
                        index = MarketIndex(
                            code=code,
                            name=name,
                            current=float(row.get('最新價', 0) or 0),
                            change=float(row.get('漲跌額', 0) or 0),
                            change_pct=float(row.get('漲跌幅', 0) or 0),
                            open=float(row.get('今開', 0) or 0),
                            high=float(row.get('最高', 0) or 0),
                            low=float(row.get('最低', 0) or 0),
                            prev_close=float(row.get('昨收', 0) or 0),
                            volume=float(row.get('成交量', 0) or 0),
                            amount=float(row.get('成交額', 0) or 0),
                        )
                        # 計算振幅
                        if index.prev_close > 0:
                            index.amplitude = (index.high - index.low) / index.prev_close * 100
                        indices.append(index)
                        
                logger.info(f"[大盤] 獲取到 {len(indices)} 個指數行情")
                
        except Exception as e:
            logger.error(f"[大盤] 獲取指數行情失敗: {e}")
        
        return indices
    
    def _get_market_statistics(self, overview: MarketOverview):
        """獲取市場漲跌統計"""
        try:
            logger.info("[大盤] 獲取市場漲跌統計...")
            
            # 獲取全部A股實時行情
            df = self._call_akshare_with_retry(ak.stock_zh_a_spot_em, "A股實時行情", attempts=2)
            
            if df is not None and not df.empty:
                # 漲跌統計
                change_col = '漲跌幅'
                if change_col in df.columns:
                    df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
                    overview.up_count = len(df[df[change_col] > 0])
                    overview.down_count = len(df[df[change_col] < 0])
                    overview.flat_count = len(df[df[change_col] == 0])
                    
                    # 漲停跌停統計（漲跌幅 >= 9.9% 或 <= -9.9%）
                    overview.limit_up_count = len(df[df[change_col] >= 9.9])
                    overview.limit_down_count = len(df[df[change_col] <= -9.9])
                
                # 兩市成交額
                amount_col = '成交額'
                if amount_col in df.columns:
                    df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
                    overview.total_amount = df[amount_col].sum() / 1e8  # 轉為億元
                
                logger.info(f"[大盤] 漲:{overview.up_count} 跌:{overview.down_count} 平:{overview.flat_count} "
                          f"漲停:{overview.limit_up_count} 跌停:{overview.limit_down_count} "
                          f"成交額:{overview.total_amount:.0f}億")
                
        except Exception as e:
            logger.error(f"[大盤] 獲取漲跌統計失敗: {e}")
    
    def _get_sector_rankings(self, overview: MarketOverview):
        """獲取板塊漲跌榜"""
        try:
            logger.info("[大盤] 獲取板塊漲跌榜...")
            
            # 獲取行業板塊行情
            df = self._call_akshare_with_retry(ak.stock_board_industry_name_em, "行業板塊行情", attempts=2)
            
            if df is not None and not df.empty:
                change_col = '漲跌幅'
                if change_col in df.columns:
                    df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
                    df = df.dropna(subset=[change_col])
                    
                    # 漲幅前5
                    top = df.nlargest(5, change_col)
                    overview.top_sectors = [
                        {'name': row['板塊名稱'], 'change_pct': row[change_col]}
                        for _, row in top.iterrows()
                    ]
                    
                    # 跌幅前5
                    bottom = df.nsmallest(5, change_col)
                    overview.bottom_sectors = [
                        {'name': row['板塊名稱'], 'change_pct': row[change_col]}
                        for _, row in bottom.iterrows()
                    ]
                    
                    logger.info(f"[大盤] 領漲板塊: {[s['name'] for s in overview.top_sectors]}")
                    logger.info(f"[大盤] 領跌板塊: {[s['name'] for s in overview.bottom_sectors]}")
                    
        except Exception as e:
            logger.error(f"[大盤] 獲取板塊漲跌榜失敗: {e}")
    
    # def _get_north_flow(self, overview: MarketOverview):
    #     """獲取北向資金流入"""
    #     try:
    #         logger.info("[大盤] 獲取北向資金...")
            
    #         # 獲取北向資金數據
    #         df = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")
            
    #         if df is not None and not df.empty:
    #             # 取最新一條數據
    #             latest = df.iloc[-1]
    #             if '當日淨流入' in df.columns:
    #                 overview.north_flow = float(latest['當日淨流入']) / 1e8  # 轉為億元
    #             elif '淨流入' in df.columns:
    #                 overview.north_flow = float(latest['淨流入']) / 1e8
                    
    #             logger.info(f"[大盤] 北向資金淨流入: {overview.north_flow:.2f}億")
                
    #     except Exception as e:
    #         logger.warning(f"[大盤] 獲取北向資金失敗: {e}")
    
    def search_market_news(self) -> List[Dict]:
        """
        搜索市場新聞
        
        Returns:
            新聞列表
        """
        if not self.search_service:
            logger.warning("[大盤] 搜索服務未配置，跳過新聞搜索")
            return []
        
        all_news = []
        today = datetime.now()
        month_str = f"{today.year}年{today.month}月"
        
        # 多維度搜索
        search_queries = [
            f"A股 大盤 覆盤 {month_str}",
            f"股市 行情 分析 今日 {month_str}",
            f"A股 市場 熱點 板塊 {month_str}",
        ]
        
        try:
            logger.info("[大盤] 開始搜索市場新聞...")
            
            for query in search_queries:
                # 使用 search_stock_news 方法，傳入"大盤"作為股票名
                response = self.search_service.search_stock_news(
                    stock_code="market",
                    stock_name="大盤",
                    max_results=3,
                    focus_keywords=query.split()
                )
                if response and response.results:
                    all_news.extend(response.results)
                    logger.info(f"[大盤] 搜索 '{query}' 獲取 {len(response.results)} 條結果")
            
            logger.info(f"[大盤] 共獲取 {len(all_news)} 條市場新聞")
            
        except Exception as e:
            logger.error(f"[大盤] 搜索市場新聞失敗: {e}")
        
        return all_news
    
    def generate_market_review(self, overview: MarketOverview, news: List) -> str:
        """
        使用大模型生成大盤覆盤報告
        
        Args:
            overview: 市場概覽數據
            news: 市場新聞列表 (SearchResult 對象列表)
            
        Returns:
            大盤覆盤報告文本
        """
        if not self.analyzer or not self.analyzer.is_available():
            logger.warning("[大盤] AI分析器未配置或不可用，使用模板生成報告")
            return self._generate_template_review(overview, news)
        
        # 構建 Prompt
        prompt = self._build_review_prompt(overview, news)
        
        try:
            logger.info("[大盤] 調用大模型生成覆盤報告...")
            
            generation_config = {
                'temperature': 0.7,
                'max_output_tokens': 2048,
            }
            
            # 根據 analyzer 使用的 API 類型調用
            if self.analyzer._use_openai:
                # 使用 OpenAI 兼容 API
                review = self.analyzer._call_openai_api(prompt, generation_config)
            else:
                # 使用 Gemini API
                response = self.analyzer._model.generate_content(
                    prompt,
                    generation_config=generation_config,
                )
                review = response.text.strip() if response and response.text else None
            
            if review:
                logger.info(f"[大盤] 覆盤報告生成成功，長度: {len(review)} 字符")
                return review
            else:
                logger.warning("[大盤] 大模型返回為空")
                return self._generate_template_review(overview, news)
                
        except Exception as e:
            logger.error(f"[大盤] 大模型生成覆盤報告失敗: {e}")
            return self._generate_template_review(overview, news)
    
    def _build_review_prompt(self, overview: MarketOverview, news: List) -> str:
        """構建覆盤報告 Prompt"""
        # 指數行情信息（簡潔格式，不用emoji）
        indices_text = ""
        for idx in overview.indices:
            direction = "↑" if idx.change_pct > 0 else "↓" if idx.change_pct < 0 else "-"
            indices_text += f"- {idx.name}: {idx.current:.2f} ({direction}{abs(idx.change_pct):.2f}%)\n"
        
        # 板塊信息
        top_sectors_text = ", ".join([f"{s['name']}({s['change_pct']:+.2f}%)" for s in overview.top_sectors[:3]])
        bottom_sectors_text = ", ".join([f"{s['name']}({s['change_pct']:+.2f}%)" for s in overview.bottom_sectors[:3]])
        
        # 新聞信息 - 支持 SearchResult 對象或字典
        news_text = ""
        for i, n in enumerate(news[:6], 1):
            # 兼容 SearchResult 對象和字典
            if hasattr(n, 'title'):
                title = n.title[:50] if n.title else ''
                snippet = n.snippet[:100] if n.snippet else ''
            else:
                title = n.get('title', '')[:50]
                snippet = n.get('snippet', '')[:100]
            news_text += f"{i}. {title}\n   {snippet}\n"
        
        prompt = f"""你是一位專業的A股市場分析師，請根據以下數據生成一份簡潔的大盤覆盤報告。

【重要】輸出要求：
- 必須輸出純 Markdown 文本格式
- 禁止輸出 JSON 格式
- 禁止輸出代碼塊
- emoji 僅在標題處少量使用（每個標題最多1個）

---

# 今日市場數據

## 日期
{overview.date}

## 主要指數
{indices_text}

## 市場概況
- 上漲: {overview.up_count} 家 | 下跌: {overview.down_count} 家 | 平盤: {overview.flat_count} 家
- 漲停: {overview.limit_up_count} 家 | 跌停: {overview.limit_down_count} 家
- 兩市成交額: {overview.total_amount:.0f} 億元
- 北向資金: {overview.north_flow:+.2f} 億元

## 板塊表現
領漲: {top_sectors_text}
領跌: {bottom_sectors_text}

## 市場新聞
{news_text if news_text else "暫無相關新聞"}

---

# 輸出格式模板（請嚴格按此格式輸出）

## 📊 {overview.date} 大盤覆盤

### 一、市場總結
（2-3句話概括今日市場整體表現，包括指數漲跌、成交量變化）

### 二、指數點評
（分析上證、深證、創業板等各指數走勢特點）

### 三、資金動向
（解讀成交額和北向資金流向的含義）

### 四、熱點解讀
（分析領漲領跌板塊背後的邏輯和驅動因素）

### 五、後市展望
（結合當前走勢和新聞，給出明日市場預判）

### 六、風險提示
（需要關注的風險點）

---

請直接輸出覆盤報告內容，不要輸出其他說明文字。
"""
        return prompt
    
    def _generate_template_review(self, overview: MarketOverview, news: List) -> str:
        """使用模板生成覆盤報告（無大模型時的備選方案）"""
        
        # 判斷市場走勢
        sh_index = next((idx for idx in overview.indices if idx.code == '000001'), None)
        if sh_index:
            if sh_index.change_pct > 1:
                market_mood = "強勢上漲"
            elif sh_index.change_pct > 0:
                market_mood = "小幅上漲"
            elif sh_index.change_pct > -1:
                market_mood = "小幅下跌"
            else:
                market_mood = "明顯下跌"
        else:
            market_mood = "震盪整理"
        
        # 指數行情（簡潔格式）
        indices_text = ""
        for idx in overview.indices[:4]:
            direction = "↑" if idx.change_pct > 0 else "↓" if idx.change_pct < 0 else "-"
            indices_text += f"- **{idx.name}**: {idx.current:.2f} ({direction}{abs(idx.change_pct):.2f}%)\n"
        
        # 板塊信息
        top_text = "、".join([s['name'] for s in overview.top_sectors[:3]])
        bottom_text = "、".join([s['name'] for s in overview.bottom_sectors[:3]])
        
        report = f"""## 📊 {overview.date} 大盤覆盤

### 一、市場總結
今日A股市場整體呈現**{market_mood}**態勢。

### 二、主要指數
{indices_text}

### 三、漲跌統計
| 指標 | 數值 |
|------|------|
| 上漲家數 | {overview.up_count} |
| 下跌家數 | {overview.down_count} |
| 漲停 | {overview.limit_up_count} |
| 跌停 | {overview.limit_down_count} |
| 兩市成交額 | {overview.total_amount:.0f}億 |
| 北向資金 | {overview.north_flow:+.2f}億 |

### 四、板塊表現
- **領漲**: {top_text}
- **領跌**: {bottom_text}

### 五、風險提示
市場有風險，投資需謹慎。以上數據僅供參考，不構成投資建議。

---
*覆盤時間: {datetime.now().strftime('%H:%M')}*
"""
        return report
    
    def run_daily_review(self) -> str:
        """
        執行每日大盤覆盤流程
        
        Returns:
            覆盤報告文本
        """
        logger.info("========== 開始大盤覆盤分析 ==========")
        
        # 1. 獲取市場概覽
        overview = self.get_market_overview()
        
        # 2. 搜索市場新聞
        news = self.search_market_news()
        
        # 3. 生成覆盤報告
        report = self.generate_market_review(overview, news)
        
        logger.info("========== 大盤覆盤分析完成 ==========")
        
        return report


# 測試入口
if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )
    
    analyzer = MarketAnalyzer()
    
    # 測試獲取市場概覽
    overview = analyzer.get_market_overview()
    print(f"\n=== 市場概覽 ===")
    print(f"日期: {overview.date}")
    print(f"指數數量: {len(overview.indices)}")
    for idx in overview.indices:
        print(f"  {idx.name}: {idx.current:.2f} ({idx.change_pct:+.2f}%)")
    print(f"上漲: {overview.up_count} | 下跌: {overview.down_count}")
    print(f"成交額: {overview.total_amount:.0f}億")
    
    # 測試生成模板報告
    report = analyzer._generate_template_review(overview, [])
    print(f"\n=== 覆盤報告 ===")
    print(report)
