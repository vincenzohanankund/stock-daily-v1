# -*- coding: utf-8 -*-
"""
===================================
A股自選股智能分析系統 - 搜索服務模塊
===================================

職責：
1. 提供統一的新聞搜索接口
2. 支持 Tavily 和 SerpAPI 兩種搜索引擎
3. 多 Key 負載均衡和故障轉移
4. 搜索結果緩存和格式化
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from itertools import cycle

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索結果數據類"""
    title: str
    snippet: str  # 摘要
    url: str
    source: str  # 來源網站
    published_date: Optional[str] = None
    
    def to_text(self) -> str:
        """轉換為文本格式"""
        date_str = f" ({self.published_date})" if self.published_date else ""
        return f"【{self.source}】{self.title}{date_str}\n{self.snippet}"


@dataclass 
class SearchResponse:
    """搜索響應"""
    query: str
    results: List[SearchResult]
    provider: str  # 使用的搜索引擎
    success: bool = True
    error_message: Optional[str] = None
    search_time: float = 0.0  # 搜索耗時（秒）
    
    def to_context(self, max_results: int = 5) -> str:
        """將搜索結果轉換為可用於 AI 分析的上下文"""
        if not self.success or not self.results:
            return f"搜索 '{self.query}' 未找到相關結果。"
        
        lines = [f"【{self.query} 搜索結果】（來源：{self.provider}）"]
        for i, result in enumerate(self.results[:max_results], 1):
            lines.append(f"\n{i}. {result.to_text()}")
        
        return "\n".join(lines)


class BaseSearchProvider(ABC):
    """搜索引擎基類"""
    
    def __init__(self, api_keys: List[str], name: str):
        """
        初始化搜索引擎
        
        Args:
            api_keys: API Key 列表（支持多個 key 負載均衡）
            name: 搜索引擎名稱
        """
        self._api_keys = api_keys
        self._name = name
        self._key_cycle = cycle(api_keys) if api_keys else None
        self._key_usage: Dict[str, int] = {key: 0 for key in api_keys}
        self._key_errors: Dict[str, int] = {key: 0 for key in api_keys}
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_available(self) -> bool:
        """檢查是否有可用的 API Key"""
        return bool(self._api_keys)
    
    def _get_next_key(self) -> Optional[str]:
        """
        獲取下一個可用的 API Key（負載均衡）
        
        策略：輪詢 + 跳過錯誤過多的 key
        """
        if not self._key_cycle:
            return None
        
        # 最多嘗試所有 key
        for _ in range(len(self._api_keys)):
            key = next(self._key_cycle)
            # 跳過錯誤次數過多的 key（超過 3 次）
            if self._key_errors.get(key, 0) < 3:
                return key
        
        # 所有 key 都有問題，重置錯誤計數並返回第一個
        logger.warning(f"[{self._name}] 所有 API Key 都有錯誤記錄，重置錯誤計數")
        self._key_errors = {key: 0 for key in self._api_keys}
        return self._api_keys[0] if self._api_keys else None
    
    def _record_success(self, key: str) -> None:
        """記錄成功使用"""
        self._key_usage[key] = self._key_usage.get(key, 0) + 1
        # 成功後減少錯誤計數
        if key in self._key_errors and self._key_errors[key] > 0:
            self._key_errors[key] -= 1
    
    def _record_error(self, key: str) -> None:
        """記錄錯誤"""
        self._key_errors[key] = self._key_errors.get(key, 0) + 1
        logger.warning(f"[{self._name}] API Key {key[:8]}... 錯誤計數: {self._key_errors[key]}")
    
    @abstractmethod
    def _do_search(self, query: str, api_key: str, max_results: int) -> SearchResponse:
        """執行搜索（子類實現）"""
        pass
    
    def search(self, query: str, max_results: int = 5) -> SearchResponse:
        """
        執行搜索
        
        Args:
            query: 搜索關鍵詞
            max_results: 最大返回結果數
            
        Returns:
            SearchResponse 對象
        """
        api_key = self._get_next_key()
        if not api_key:
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=f"{self._name} 未配置 API Key"
            )
        
        start_time = time.time()
        try:
            response = self._do_search(query, api_key, max_results)
            response.search_time = time.time() - start_time
            
            if response.success:
                self._record_success(api_key)
                logger.info(f"[{self._name}] 搜索 '{query}' 成功，返回 {len(response.results)} 條結果，耗時 {response.search_time:.2f}s")
            else:
                self._record_error(api_key)
            
            return response
            
        except Exception as e:
            self._record_error(api_key)
            elapsed = time.time() - start_time
            logger.error(f"[{self._name}] 搜索 '{query}' 失敗: {e}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self._name,
                success=False,
                error_message=str(e),
                search_time=elapsed
            )


class TavilySearchProvider(BaseSearchProvider):
    """
    Tavily 搜索引擎
    
    特點：
    - 專為 AI/LLM 優化的搜索 API
    - 免費版每月 1000 次請求
    - 返回結構化的搜索結果
    
    文檔：https://docs.tavily.com/
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Tavily")
    
    def _do_search(self, query: str, api_key: str, max_results: int) -> SearchResponse:
        """執行 Tavily 搜索"""
        try:
            from tavily import TavilyClient
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="tavily-python 未安裝，請運行: pip install tavily-python"
            )
        
        try:
            client = TavilyClient(api_key=api_key)
            
            # 執行搜索（優化：使用advanced深度、限制最近7天）
            response = client.search(
                query=query,
                search_depth="advanced",  # advanced 獲取更多結果
                max_results=max_results,
                include_answer=False,
                include_raw_content=False,
                days=7,  # 只搜索最近7天的內容
            )
            
            # 記錄原始響應到日誌
            logger.info(f"[Tavily] 搜索完成，query='{query}', 返回 {len(response.get('results', []))} 條結果")
            logger.debug(f"[Tavily] 原始響應: {response}")
            
            # 解析結果
            results = []
            for item in response.get('results', []):
                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=item.get('content', '')[:500],  # 截取前500字
                    url=item.get('url', ''),
                    source=self._extract_domain(item.get('url', '')),
                    published_date=item.get('published_date'),
                ))
            
            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except Exception as e:
            error_msg = str(e)
            # 檢查是否是配額問題
            if 'rate limit' in error_msg.lower() or 'quota' in error_msg.lower():
                error_msg = f"API 配額已用盡: {error_msg}"
            
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """從 URL 提取域名作為來源"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or '未知來源'
        except:
            return '未知來源'


class SerpAPISearchProvider(BaseSearchProvider):
    """
    SerpAPI 搜索引擎
    
    特點：
    - 支持 Google、Bing、百度等多種搜索引擎
    - 免費版每月 100 次請求
    - 返回真實的搜索結果
    
    文檔：https://serpapi.com/
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "SerpAPI")
    
    def _do_search(self, query: str, api_key: str, max_results: int) -> SearchResponse:
        """執行 SerpAPI 搜索"""
        try:
            from serpapi import GoogleSearch
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="google-search-results 未安裝，請運行: pip install google-search-results"
            )
        
        try:
            # 使用百度搜索（對中文股票新聞更友好）
            params = {
                "engine": "baidu",  # 使用百度搜索
                "q": query,
                "api_key": api_key,
            }
            
            search = GoogleSearch(params)
            response = search.get_dict()
            
            # 記錄原始響應到日誌
            logger.debug(f"[SerpAPI] 原始響應 keys: {response.keys()}")
            
            # 解析結果
            results = []
            organic_results = response.get('organic_results', [])
            
            for item in organic_results[:max_results]:
                results.append(SearchResult(
                    title=item.get('title', ''),
                    snippet=item.get('snippet', '')[:500],
                    url=item.get('link', ''),
                    source=item.get('source', self._extract_domain(item.get('link', ''))),
                    published_date=item.get('date'),
                ))
            
            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except Exception as e:
            error_msg = str(e)
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """從 URL 提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '') or '未知來源'
        except:
            return '未知來源'


class BochaSearchProvider(BaseSearchProvider):
    """
    博查搜索引擎
    
    特點：
    - 專為AI優化的中文搜索API
    - 結果準確、摘要完整
    - 支持時間範圍過濾和AI摘要
    - 兼容Bing Search API格式
    
    文檔：https://bocha-ai.feishu.cn/wiki/RXEOw02rFiwzGSkd9mUcqoeAnNK
    """
    
    def __init__(self, api_keys: List[str]):
        super().__init__(api_keys, "Bocha")
    
    def _do_search(self, query: str, api_key: str, max_results: int) -> SearchResponse:
        """執行博查搜索"""
        try:
            import requests
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message="requests 未安裝，請運行: pip install requests"
            )
        
        try:
            # API 端點
            url = "https://api.bocha.cn/v1/web-search"
            
            # 請求頭
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 請求參數（嚴格按照API文檔）
            payload = {
                "query": query,
                "freshness": "oneMonth",  # 搜索近一個月，適合捕獲財報、公告等信息
                "summary": True,  # 啟用AI摘要
                "count": min(max_results, 50)  # 最大50條
            }
            
            # 執行搜索
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            # 檢查HTTP狀態碼
            if response.status_code != 200:
                # 嘗試解析錯誤信息
                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        error_data = response.json()
                        error_message = error_data.get('message', response.text)
                    else:
                        error_message = response.text
                except:
                    error_message = response.text
                
                # 根據錯誤碼處理
                if response.status_code == 403:
                    error_msg = f"餘額不足: {error_message}"
                elif response.status_code == 401:
                    error_msg = f"API KEY無效: {error_message}"
                elif response.status_code == 400:
                    error_msg = f"請求參數錯誤: {error_message}"
                elif response.status_code == 429:
                    error_msg = f"請求頻率達到限制: {error_message}"
                else:
                    error_msg = f"HTTP {response.status_code}: {error_message}"
                
                logger.warning(f"[Bocha] 搜索失敗: {error_msg}")
                
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # 解析響應
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"響應JSON解析失敗: {str(e)}"
                logger.error(f"[Bocha] {error_msg}")
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # 檢查響應code
            if data.get('code') != 200:
                error_msg = data.get('msg') or f"API返回錯誤碼: {data.get('code')}"
                return SearchResponse(
                    query=query,
                    results=[],
                    provider=self.name,
                    success=False,
                    error_message=error_msg
                )
            
            # 記錄原始響應到日誌
            logger.info(f"[Bocha] 搜索完成，query='{query}'")
            logger.debug(f"[Bocha] 原始響應: {data}")
            
            # 解析搜索結果
            results = []
            web_pages = data.get('data', {}).get('webPages', {})
            value_list = web_pages.get('value', [])
            
            for item in value_list[:max_results]:
                # 優先使用summary（AI摘要），fallback到snippet
                snippet = item.get('summary') or item.get('snippet', '')
                
                # 截取摘要長度
                if snippet:
                    snippet = snippet[:500]
                
                results.append(SearchResult(
                    title=item.get('name', ''),
                    snippet=snippet,
                    url=item.get('url', ''),
                    source=item.get('siteName') or self._extract_domain(item.get('url', '')),
                    published_date=item.get('datePublished'),  # UTC+8格式，無需轉換
                ))
            
            logger.info(f"[Bocha] 成功解析 {len(results)} 條結果")
            
            return SearchResponse(
                query=query,
                results=results,
                provider=self.name,
                success=True,
            )
            
        except requests.exceptions.Timeout:
            error_msg = "請求超時"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"網絡請求失敗: {str(e)}"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"未知錯誤: {str(e)}"
            logger.error(f"[Bocha] {error_msg}")
            return SearchResponse(
                query=query,
                results=[],
                provider=self.name,
                success=False,
                error_message=error_msg
            )
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """從 URL 提取域名作為來源"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain or '未知來源'
        except:
            return '未知來源'


class SearchService:
    """
    搜索服務
    
    功能：
    1. 管理多個搜索引擎
    2. 自動故障轉移
    3. 結果聚合和格式化
    """
    
    def __init__(
        self,
        bocha_keys: Optional[List[str]] = None,
        tavily_keys: Optional[List[str]] = None,
        serpapi_keys: Optional[List[str]] = None,
    ):
        """
        初始化搜索服務
        
        Args:
            bocha_keys: 博查搜索 API Key 列表
            tavily_keys: Tavily API Key 列表
            serpapi_keys: SerpAPI Key 列表
        """
        self._providers: List[BaseSearchProvider] = []
        
        # 初始化搜索引擎（按優先級排序）
        # 1. Bocha 優先（中文搜索優化，AI摘要）
        if bocha_keys:
            self._providers.append(BochaSearchProvider(bocha_keys))
            logger.info(f"已配置 Bocha 搜索，共 {len(bocha_keys)} 個 API Key")
        
        # 2. Tavily（免費額度更多，每月 1000 次）
        if tavily_keys:
            self._providers.append(TavilySearchProvider(tavily_keys))
            logger.info(f"已配置 Tavily 搜索，共 {len(tavily_keys)} 個 API Key")
        
        # 3. SerpAPI 作為備選（每月 100 次）
        if serpapi_keys:
            self._providers.append(SerpAPISearchProvider(serpapi_keys))
            logger.info(f"已配置 SerpAPI 搜索，共 {len(serpapi_keys)} 個 API Key")
        
        if not self._providers:
            logger.warning("未配置任何搜索引擎 API Key，新聞搜索功能將不可用")
    
    @property
    def is_available(self) -> bool:
        """檢查是否有可用的搜索引擎"""
        return any(p.is_available for p in self._providers)
    
    def search_stock_news(
        self,
        stock_code: str,
        stock_name: str,
        max_results: int = 5,
        focus_keywords: Optional[List[str]] = None
    ) -> SearchResponse:
        """
        搜索股票相關新聞
        
        Args:
            stock_code: 股票代碼
            stock_name: 股票名稱
            max_results: 最大返回結果數
            focus_keywords: 重點關注的關鍵詞列表
            
        Returns:
            SearchResponse 對象
        """
        # 默認重點關注關鍵詞（基於交易理念）
        if focus_keywords is None:
            focus_keywords = [
                "年報預告", "業績預告", "業績快報",  # 業績相關
                "減持", "增持", "回購",              # 股東動向
                "機構調研", "機構評級",              # 機構動向
                "利好", "利空",                      # 消息面
                "合同", "訂單", "中標",              # 業務進展
            ]
        
        # 構建搜索查詢（優化搜索效果）
        # 主查詢：股票名稱 + 核心關鍵詞
        query = f"{stock_name} {stock_code} 股票 最新消息"
        
        logger.info(f"搜索股票新聞: {stock_name}({stock_code})")
        
        # 依次嘗試各個搜索引擎
        for provider in self._providers:
            if not provider.is_available:
                continue
            
            response = provider.search(query, max_results)
            
            if response.success and response.results:
                logger.info(f"使用 {provider.name} 搜索成功")
                return response
            else:
                logger.warning(f"{provider.name} 搜索失敗: {response.error_message}，嘗試下一個引擎")
        
        # 所有引擎都失敗
        return SearchResponse(
            query=query,
            results=[],
            provider="None",
            success=False,
            error_message="所有搜索引擎都不可用或搜索失敗"
        )
    
    def search_stock_events(
        self,
        stock_code: str,
        stock_name: str,
        event_types: Optional[List[str]] = None
    ) -> SearchResponse:
        """
        搜索股票特定事件（年報預告、減持等）
        
        專門針對交易決策相關的重要事件進行搜索
        
        Args:
            stock_code: 股票代碼
            stock_name: 股票名稱
            event_types: 事件類型列表
            
        Returns:
            SearchResponse 對象
        """
        if event_types is None:
            event_types = ["年報預告", "減持公告", "業績快報"]
        
        # 構建針對性查詢
        event_query = " OR ".join(event_types)
        query = f"{stock_name} ({event_query})"
        
        logger.info(f"搜索股票事件: {stock_name}({stock_code}) - {event_types}")
        
        # 依次嘗試各個搜索引擎
        for provider in self._providers:
            if not provider.is_available:
                continue
            
            response = provider.search(query, max_results=5)
            
            if response.success:
                return response
        
        return SearchResponse(
            query=query,
            results=[],
            provider="None",
            success=False,
            error_message="事件搜索失敗"
        )
    
    def search_comprehensive_intel(
        self,
        stock_code: str,
        stock_name: str,
        max_searches: int = 3
    ) -> Dict[str, SearchResponse]:
        """
        多維度情報搜索（同時使用多個引擎、多個維度）
        
        搜索維度：
        1. 最新消息 - 近期新聞動態
        2. 風險排查 - 減持、處罰、利空
        3. 業績預期 - 年報預告、業績快報
        
        Args:
            stock_code: 股票代碼
            stock_name: 股票名稱
            max_searches: 最大搜索次數
            
        Returns:
            {維度名稱: SearchResponse} 字典
        """
        results = {}
        search_count = 0
        
        # 定義搜索維度
        search_dimensions = [
            {
                'name': 'latest_news',
                'query': f"{stock_name} {stock_code} 最新 新聞 2026年1月",
                'desc': '最新消息'
            },
            {
                'name': 'risk_check', 
                'query': f"{stock_name} 減持 處罰 利空 風險",
                'desc': '風險排查'
            },
            {
                'name': 'earnings',
                'query': f"{stock_name} 年報預告 業績預告 業績快報 2025年報",
                'desc': '業績預期'
            },
        ]
        
        logger.info(f"開始多維度情報搜索: {stock_name}({stock_code})")
        
        # 輪流使用不同的搜索引擎
        provider_index = 0
        
        for dim in search_dimensions:
            if search_count >= max_searches:
                break
            
            # 選擇搜索引擎（輪流使用）
            available_providers = [p for p in self._providers if p.is_available]
            if not available_providers:
                break
            
            provider = available_providers[provider_index % len(available_providers)]
            provider_index += 1
            
            logger.info(f"[情報搜索] {dim['desc']}: 使用 {provider.name}")
            
            response = provider.search(dim['query'], max_results=3)
            results[dim['name']] = response
            search_count += 1
            
            if response.success:
                logger.info(f"[情報搜索] {dim['desc']}: 獲取 {len(response.results)} 條結果")
            else:
                logger.warning(f"[情報搜索] {dim['desc']}: 搜索失敗 - {response.error_message}")
            
            # 短暫延遲避免請求過快
            time.sleep(0.5)
        
        return results
    
    def format_intel_report(self, intel_results: Dict[str, SearchResponse], stock_name: str) -> str:
        """
        格式化情報搜索結果為報告
        
        Args:
            intel_results: 多維度搜索結果
            stock_name: 股票名稱
            
        Returns:
            格式化的情報報告文本
        """
        lines = [f"【{stock_name} 情報搜索結果】"]
        
        # 最新消息
        if 'latest_news' in intel_results:
            resp = intel_results['latest_news']
            lines.append(f"\n📰 最新消息 (來源: {resp.provider}):")
            if resp.success and resp.results:
                for i, r in enumerate(resp.results[:3], 1):
                    date_str = f" [{r.published_date}]" if r.published_date else ""
                    lines.append(f"  {i}. {r.title}{date_str}")
                    lines.append(f"     {r.snippet[:100]}...")
            else:
                lines.append("  未找到相關消息")
        
        # 風險排查
        if 'risk_check' in intel_results:
            resp = intel_results['risk_check']
            lines.append(f"\n⚠️ 風險排查 (來源: {resp.provider}):")
            if resp.success and resp.results:
                for i, r in enumerate(resp.results[:3], 1):
                    lines.append(f"  {i}. {r.title}")
                    lines.append(f"     {r.snippet[:100]}...")
            else:
                lines.append("  未發現明顯風險信號")
        
        # 業績預期
        if 'earnings' in intel_results:
            resp = intel_results['earnings']
            lines.append(f"\n📊 業績預期 (來源: {resp.provider}):")
            if resp.success and resp.results:
                for i, r in enumerate(resp.results[:3], 1):
                    lines.append(f"  {i}. {r.title}")
                    lines.append(f"     {r.snippet[:100]}...")
            else:
                lines.append("  未找到業績相關信息")
        
        return "\n".join(lines)
    
    def batch_search(
        self,
        stocks: List[Dict[str, str]],
        max_results_per_stock: int = 3,
        delay_between: float = 1.0
    ) -> Dict[str, SearchResponse]:
        """
        批量搜索多隻股票新聞
        
        Args:
            stocks: 股票列表 [{"code": "300389", "name": "艾比森"}, ...]
            max_results_per_stock: 每隻股票的最大結果數
            delay_between: 每次搜索之間的延遲（秒）
            
        Returns:
            {股票代碼: SearchResponse} 字典
        """
        results = {}
        
        for i, stock in enumerate(stocks):
            if i > 0:
                time.sleep(delay_between)
            
            code = stock.get('code', '')
            name = stock.get('name', '')
            
            response = self.search_stock_news(code, name, max_results_per_stock)
            results[code] = response
        
        return results


# === 便捷函數 ===
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """獲取搜索服務單例"""
    global _search_service
    
    if _search_service is None:
        from config import get_config
        config = get_config()
        
        _search_service = SearchService(
            bocha_keys=config.bocha_api_keys,
            tavily_keys=config.tavily_api_keys,
            serpapi_keys=config.serpapi_keys,
        )
    
    return _search_service


def reset_search_service() -> None:
    """重置搜索服務（用於測試）"""
    global _search_service
    _search_service = None


if __name__ == "__main__":
    # 測試搜索服務
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
    )
    
    # 手動測試（需要配置 API Key）
    service = get_search_service()
    
    if service.is_available:
        print("=== 測試股票新聞搜索 ===")
        response = service.search_stock_news("300389", "艾比森")
        print(f"搜索狀態: {'成功' if response.success else '失敗'}")
        print(f"搜索引擎: {response.provider}")
        print(f"結果數量: {len(response.results)}")
        print(f"耗時: {response.search_time:.2f}s")
        print("\n" + response.to_context())
    else:
        print("未配置搜索引擎 API Key，跳過測試")
