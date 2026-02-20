# -*- coding: utf-8 -*-
"""
===================================
股票数据服务层
===================================

职责：
1. 封装股票数据获取逻辑
2. 提供实时行情和历史数据接口
"""

import logging
import json
import re
import time
import uuid
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List

from src.repositories.stock_repo import StockRepository
from src.config import get_config, Config, setup_env
from src.core.config_manager import ConfigManager
from src.analyzer import STOCK_NAME_MAP
from src.storage import get_db

logger = logging.getLogger(__name__)


class StockService:
    """
    股票数据服务
    
    封装股票数据获取的业务逻辑
    """
    
    _quote_cache: Dict[str, Dict[str, Any]] = {}
    _quote_cache_lock = threading.Lock()
    _quote_cache_ttl_seconds = 300
    _watchlist_quote_budget_seconds = 8.0

    _watchlist_refresh_state_lock = threading.Lock()
    _watchlist_refresh_state: Dict[str, Any] = {
        'task_id': None,
        'status': 'idle',
        'completed': True,
        'is_new_task': False,
        'progress_total': 0,
        'progress_done': 0,
        'started_at': None,
        'finished_at': None,
        'error': None,
    }

    def __init__(self):
        """初始化股票数据服务"""
        self.repo = StockRepository()
        self.db = get_db()
        self.config_manager = ConfigManager()

    @classmethod
    def _get_quote_cache(cls, code: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        with cls._quote_cache_lock:
            entry = cls._quote_cache.get(code)
            if not entry:
                return None

            if now - entry.get('ts', 0) > cls._quote_cache_ttl_seconds:
                cls._quote_cache.pop(code, None)
                return None

            return {
                'stock_name': entry.get('stock_name'),
                'last_price': entry.get('last_price'),
                'change_pct': entry.get('change_pct'),
            }

    @classmethod
    def _set_quote_cache(cls, code: str, payload: Dict[str, Any]) -> None:
        if payload.get('last_price') is None and payload.get('change_pct') is None and not payload.get('stock_name'):
            return

        with cls._quote_cache_lock:
            cls._quote_cache[code] = {
                'ts': time.time(),
                'stock_name': payload.get('stock_name'),
                'last_price': payload.get('last_price'),
                'change_pct': payload.get('change_pct'),
            }

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.utcnow().isoformat()

    @classmethod
    def _serialize_watchlist_refresh_state(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            'task_id': state.get('task_id'),
            'status': state.get('status', 'idle'),
            'completed': bool(state.get('completed', False)),
            'is_new_task': bool(state.get('is_new_task', False)),
            'progress_total': int(state.get('progress_total', 0) or 0),
            'progress_done': int(state.get('progress_done', 0) or 0),
            'started_at': state.get('started_at'),
            'finished_at': state.get('finished_at'),
            'error': state.get('error'),
        }
        if payload['status'] in ('idle', 'completed', 'failed', 'not_found'):
            payload['completed'] = True
        return payload

    @classmethod
    def _read_watchlist_refresh_state(cls) -> Dict[str, Any]:
        with cls._watchlist_refresh_state_lock:
            return cls._serialize_watchlist_refresh_state(dict(cls._watchlist_refresh_state))

    @classmethod
    def _mark_watchlist_refresh_state(
        cls,
        updates: Dict[str, Any],
        task_id: Optional[str] = None,
    ) -> bool:
        with cls._watchlist_refresh_state_lock:
            if task_id and cls._watchlist_refresh_state.get('task_id') != task_id:
                return False
            cls._watchlist_refresh_state.update(updates)
            return True

    @classmethod
    def _update_watchlist_refresh_progress(cls, task_id: str, progress_done: int) -> None:
        with cls._watchlist_refresh_state_lock:
            if cls._watchlist_refresh_state.get('task_id') != task_id:
                return
            total = int(cls._watchlist_refresh_state.get('progress_total', 0) or 0)
            cls._watchlist_refresh_state['progress_done'] = min(max(progress_done, 0), total)

    def _run_watchlist_refresh_worker(self, task_id: str, stock_codes: List[str]) -> None:
        try:
            from data_provider.base import DataFetcherManager

            fetcher_manager = DataFetcherManager()
            if stock_codes and len(stock_codes) >= 5:
                fetcher_manager.prefetch_realtime_quotes(stock_codes)

            realtime_payload_map = self._fetch_realtime_quotes_batch(fetcher_manager, stock_codes)

            progress_done = 0
            for code in stock_codes:
                payload = realtime_payload_map.get(code)
                if payload is None:
                    fallback_item = {
                        'stock_name': STOCK_NAME_MAP.get(code.upper()) or STOCK_NAME_MAP.get(code),
                        'last_price': None,
                        'change_pct': None,
                    }
                    self._fill_quote_from_daily_fallback(fetcher_manager, code, fallback_item)
                    payload = {
                        'stock_name': fallback_item.get('stock_name'),
                        'last_price': fallback_item.get('last_price'),
                        'change_pct': fallback_item.get('change_pct'),
                    }
                    self._set_quote_cache(code, payload)

                progress_done += 1
                self._update_watchlist_refresh_progress(task_id, progress_done)

            self._mark_watchlist_refresh_state(
                updates={
                    'status': 'completed',
                    'completed': True,
                    'is_new_task': False,
                    'finished_at': self._utcnow_iso(),
                    'error': None,
                    'progress_done': len(stock_codes),
                },
                task_id=task_id,
            )
        except Exception as exc:
            logger.error(f"watchlist 行情异步刷新失败(task_id={task_id}): {exc}", exc_info=True)
            self._mark_watchlist_refresh_state(
                updates={
                    'status': 'failed',
                    'completed': True,
                    'is_new_task': False,
                    'finished_at': self._utcnow_iso(),
                    'error': str(exc),
                },
                task_id=task_id,
            )

    def start_watchlist_refresh(self, force: bool = False) -> Dict[str, Any]:
        stock_codes = self._get_watchlist_codes()

        with self._watchlist_refresh_state_lock:
            current_state = self._serialize_watchlist_refresh_state(dict(self._watchlist_refresh_state))
            if current_state.get('status') == 'processing' and not force:
                current_state['is_new_task'] = False
                return current_state

            task_id = uuid.uuid4().hex
            self._watchlist_refresh_state.update(
                {
                    'task_id': task_id,
                    'status': 'processing',
                    'completed': False,
                    'is_new_task': False,
                    'progress_total': len(stock_codes),
                    'progress_done': 0,
                    'started_at': self._utcnow_iso(),
                    'finished_at': None,
                    'error': None,
                }
            )

        worker = threading.Thread(
            target=self._run_watchlist_refresh_worker,
            args=(task_id, stock_codes),
            daemon=True,
            name=f"watchlist-refresh-{task_id[:8]}",
        )
        worker.start()

        created_state = self.get_watchlist_refresh_status(task_id=task_id)
        created_state['is_new_task'] = True
        return created_state

    def get_watchlist_refresh_status(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        current_state = self._read_watchlist_refresh_state()
        if task_id and current_state.get('task_id') != task_id:
            return {
                'task_id': task_id,
                'status': 'not_found',
                'completed': True,
                'is_new_task': False,
                'progress_total': 0,
                'progress_done': 0,
                'started_at': None,
                'finished_at': self._utcnow_iso(),
                'error': 'watchlist_refresh_task_not_found',
            }
        return current_state

    def _fetch_realtime_quotes_batch(
        self,
        fetcher_manager: Any,
        stock_codes: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        if not stock_codes:
            return {}

        result_map: Dict[str, Dict[str, Any]] = {}
        max_workers = min(8, len(stock_codes))

        def _fetch_one(code: str):
            return code, fetcher_manager.get_realtime_quote(code)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_fetch_one, code) for code in stock_codes]
            for future in as_completed(futures):
                try:
                    code, quote = future.result()
                except Exception as exc:
                    logger.debug(f"批量获取实时行情失败: {exc}")
                    continue

                if not quote:
                    continue

                payload = {
                    'stock_name': getattr(quote, 'name', None),
                    'last_price': self._to_float(getattr(quote, 'price', None)),
                    'change_pct': self._to_float(getattr(quote, 'change_pct', None)),
                }
                result_map[code] = payload
                self._set_quote_cache(code, payload)

        return result_map

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _deduplicate_keep_order(codes: List[str]) -> List[str]:
        deduped: List[str] = []
        seen = set()
        for code in codes:
            if not code or code in seen:
                continue
            deduped.append(code)
            seen.add(code)
        return deduped

    def _normalize_and_validate_code(self, stock_code: str) -> str:
        """Normalize and validate a stock code."""
        from data_provider.base import normalize_stock_code

        raw = (stock_code or '').strip().upper()
        if not raw:
            raise ValueError("股票代码不能为空")

        normalized = normalize_stock_code(raw)
        if normalized.startswith('HK') and len(normalized) == 7 and normalized[2:].isdigit():
            normalized = f"hk{normalized[2:]}"

        patterns = (
            r'^\d{6}$',                  # A股
            r'^\d{5}$',                  # 港股纯数字
            r'^hk\d{5}$',                # 港股 hk 前缀
            r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$',  # 美股
        )
        if not any(re.match(pattern, normalized) for pattern in patterns):
            raise ValueError(f"无效的股票代码: {stock_code}")

        return normalized

    def _get_watchlist_codes(self) -> List[str]:
        config = get_config()
        config.refresh_stock_list()

        normalized_codes: List[str] = []
        for code in config.stock_list:
            try:
                normalized_codes.append(self._normalize_and_validate_code(code))
            except ValueError:
                logger.warning(f"检测到无效股票代码，已跳过: {code}")

        return self._deduplicate_keep_order(normalized_codes)

    def _save_watchlist_codes(self, codes: List[str]) -> List[str]:
        clean_codes = self._deduplicate_keep_order([
            self._normalize_and_validate_code(code)
            for code in codes
            if str(code).strip()
        ])

        stock_list_str = ','.join(clean_codes)
        self.config_manager.apply_updates(
            updates=[('STOCK_LIST', stock_list_str)],
            sensitive_keys=set(),
            mask_token='******',
        )

        Config.reset_instance()
        setup_env(override=True)
        refreshed = get_config()
        refreshed.refresh_stock_list()
        return self._deduplicate_keep_order(refreshed.stock_list)

    def _extract_price_from_context(self, context_snapshot: Any) -> Dict[str, Optional[float]]:
        """Extract snapshot price info from context_snapshot."""
        parsed = context_snapshot
        if isinstance(context_snapshot, str):
            try:
                parsed = json.loads(context_snapshot)
            except (TypeError, ValueError):
                return {'last_price': None, 'change_pct': None}

        if not isinstance(parsed, dict):
            return {'last_price': None, 'change_pct': None}

        enhanced_context = parsed.get('enhanced_context') or {}
        realtime = enhanced_context.get('realtime') or {}
        realtime_quote_raw = parsed.get('realtime_quote_raw') or {}

        last_price = self._to_float(realtime.get('price'))
        if last_price is None:
            last_price = self._to_float(realtime_quote_raw.get('price'))

        change_pct = self._to_float(realtime.get('change_pct'))
        if change_pct is None:
            change_pct = self._to_float(realtime_quote_raw.get('change_pct'))
        if change_pct is None:
            change_pct = self._to_float(realtime_quote_raw.get('pct_chg'))

        return {
            'last_price': last_price,
            'change_pct': change_pct,
        }

    def _fill_quote_from_daily_fallback(self, fetcher_manager: Any, code: str, item: Dict[str, Any]) -> None:
        """Backfill quote fields from latest daily bar when realtime quote is unavailable."""
        if fetcher_manager is None:
            return

        if item.get('last_price') is not None and item.get('change_pct') is not None:
            return

        try:
            df, source = fetcher_manager.get_daily_data(code, days=5)
            if df is None or df.empty:
                return

            latest = df.iloc[-1]
            if item.get('last_price') is None:
                item['last_price'] = self._to_float(latest.get('close'))
            if item.get('change_pct') is None:
                item['change_pct'] = self._to_float(latest.get('pct_chg'))

            logger.debug(f"{code} 使用日线数据补全行情字段 (source={source})")
        except Exception as exc:
            logger.debug(f"{code} 使用日线数据补全失败: {exc}")

    def get_watchlist(self, include_quote: bool = False) -> Dict[str, Any]:
        """Get watchlist items with latest analysis summary."""
        codes = self._get_watchlist_codes()
        items: List[Dict[str, Any]] = []

        fetcher_manager = None
        quote_fetch_started = time.time()
        quote_payload_map: Dict[str, Dict[str, Any]] = {}

        if include_quote and codes:
            pending_codes: List[str] = []
            for code in codes:
                cached = self._get_quote_cache(code)
                if cached:
                    quote_payload_map[code] = cached
                else:
                    pending_codes.append(code)

            if pending_codes:
                try:
                    from data_provider.base import DataFetcherManager
                    fetcher_manager = DataFetcherManager()
                    if len(pending_codes) >= 5:
                        fetcher_manager.prefetch_realtime_quotes(pending_codes)
                    quote_payload_map.update(
                        self._fetch_realtime_quotes_batch(fetcher_manager, pending_codes)
                    )
                except Exception as exc:
                    logger.warning(f"初始化实时行情服务失败，降级处理: {exc}")

        for code in codes:
            item: Dict[str, Any] = {
                'stock_code': code,
                'stock_name': STOCK_NAME_MAP.get(code.upper()) or STOCK_NAME_MAP.get(code),
                'last_analysis_time': None,
                'last_price': None,
                'change_pct': None,
                'trend_prediction': None,
                'operation_advice': None,
            }

            history = self.db.get_analysis_history(code=code, days=3650, limit=1)
            if history:
                latest = history[0]
                item['stock_name'] = item['stock_name'] or latest.name
                item['last_analysis_time'] = latest.created_at.isoformat() if latest.created_at else None
                item['trend_prediction'] = latest.trend_prediction
                item['operation_advice'] = latest.operation_advice

                snapshot_price = self._extract_price_from_context(latest.context_snapshot)
                item['last_price'] = snapshot_price['last_price']
                item['change_pct'] = snapshot_price['change_pct']

            quote_payload = quote_payload_map.get(code)
            if quote_payload:
                if quote_payload.get('stock_name'):
                    item['stock_name'] = quote_payload.get('stock_name')
                if quote_payload.get('last_price') is not None:
                    item['last_price'] = quote_payload.get('last_price')
                if quote_payload.get('change_pct') is not None:
                    item['change_pct'] = quote_payload.get('change_pct')

            elif include_quote and fetcher_manager is not None:
                elapsed = time.time() - quote_fetch_started
                if elapsed <= self._watchlist_quote_budget_seconds:
                    self._fill_quote_from_daily_fallback(fetcher_manager, code, item)
                    self._set_quote_cache(
                        code,
                        {
                            'stock_name': item.get('stock_name'),
                            'last_price': item.get('last_price'),
                            'change_pct': item.get('change_pct'),
                        },
                    )
                else:
                    logger.debug(
                        f"watchlist 行情获取超过预算 {self._watchlist_quote_budget_seconds}s，跳过 {code} 的回填"
                    )

            items.append(item)

        return {
            'total': len(items),
            'items': items,
        }

    def get_watchlist_cached_snapshot(self, include_quote: bool = True) -> Dict[str, Any]:
        codes = self._get_watchlist_codes()
        quote_payload_map: Dict[str, Dict[str, Any]] = {}

        if include_quote:
            for code in codes:
                cached = self._get_quote_cache(code)
                if cached:
                    quote_payload_map[code] = cached

        items: List[Dict[str, Any]] = []
        for code in codes:
            item: Dict[str, Any] = {
                'stock_code': code,
                'stock_name': STOCK_NAME_MAP.get(code.upper()) or STOCK_NAME_MAP.get(code),
                'last_analysis_time': None,
                'last_price': None,
                'change_pct': None,
                'trend_prediction': None,
                'operation_advice': None,
            }

            history = self.db.get_analysis_history(code=code, days=3650, limit=1)
            if history:
                latest = history[0]
                item['stock_name'] = item['stock_name'] or latest.name
                item['last_analysis_time'] = latest.created_at.isoformat() if latest.created_at else None
                item['trend_prediction'] = latest.trend_prediction
                item['operation_advice'] = latest.operation_advice

                snapshot_price = self._extract_price_from_context(latest.context_snapshot)
                item['last_price'] = snapshot_price['last_price']
                item['change_pct'] = snapshot_price['change_pct']

            quote_payload = quote_payload_map.get(code)
            if quote_payload:
                if quote_payload.get('stock_name'):
                    item['stock_name'] = quote_payload.get('stock_name')
                if quote_payload.get('last_price') is not None:
                    item['last_price'] = quote_payload.get('last_price')
                if quote_payload.get('change_pct') is not None:
                    item['change_pct'] = quote_payload.get('change_pct')

            items.append(item)

        return {
            'total': len(items),
            'items': items,
        }

    def add_watchlist_stock(self, stock_code: str) -> Dict[str, Any]:
        """Add one stock to watchlist and persist STOCK_LIST."""
        normalized = self._normalize_and_validate_code(stock_code)
        current_codes = self._get_watchlist_codes()
        if normalized in current_codes:
            return {
                'success': True,
                'added': False,
                'stock_code': normalized,
                'stock_list': current_codes,
            }

        updated_codes = [normalized] + current_codes
        final_codes = self._save_watchlist_codes(updated_codes)
        return {
            'success': True,
            'added': True,
            'stock_code': normalized,
            'stock_list': final_codes,
        }

    def remove_watchlist_stock(self, stock_code: str) -> Dict[str, Any]:
        """Remove one stock from watchlist and persist STOCK_LIST."""
        normalized = self._normalize_and_validate_code(stock_code)
        current_codes = self._get_watchlist_codes()
        if normalized not in current_codes:
            return {
                'success': True,
                'removed': False,
                'stock_code': normalized,
                'stock_list': current_codes,
            }

        updated_codes = [code for code in current_codes if code != normalized]
        final_codes = self._save_watchlist_codes(updated_codes)
        return {
            'success': True,
            'removed': True,
            'stock_code': normalized,
            'stock_list': final_codes,
        }

    def replace_watchlist(self, stock_codes: List[str]) -> Dict[str, Any]:
        """Replace the whole watchlist with provided stock codes."""
        final_codes = self._save_watchlist_codes(stock_codes)
        return {
            'success': True,
            'stock_list': final_codes,
            'total': len(final_codes),
        }
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票实时行情
        
        Args:
            stock_code: 股票代码
            
        Returns:
            实时行情数据字典
        """
        try:
            # 调用数据获取器获取实时行情
            from data_provider.base import DataFetcherManager
            
            manager = DataFetcherManager()
            quote = manager.get_realtime_quote(stock_code)
            
            if quote is None:
                logger.warning(f"获取 {stock_code} 实时行情失败")
                return None
            
            # UnifiedRealtimeQuote 是 dataclass，使用 getattr 安全访问字段
            # 字段映射: UnifiedRealtimeQuote -> API 响应
            # - code -> stock_code
            # - name -> stock_name
            # - price -> current_price
            # - change_amount -> change
            # - change_pct -> change_percent
            # - open_price -> open
            # - high -> high
            # - low -> low
            # - pre_close -> prev_close
            # - volume -> volume
            # - amount -> amount
            return {
                "stock_code": getattr(quote, "code", stock_code),
                "stock_name": getattr(quote, "name", None),
                "current_price": getattr(quote, "price", 0.0) or 0.0,
                "change": getattr(quote, "change_amount", None),
                "change_percent": getattr(quote, "change_pct", None),
                "open": getattr(quote, "open_price", None),
                "high": getattr(quote, "high", None),
                "low": getattr(quote, "low", None),
                "prev_close": getattr(quote, "pre_close", None),
                "volume": getattr(quote, "volume", None),
                "amount": getattr(quote, "amount", None),
                "update_time": datetime.now().isoformat(),
            }
            
        except ImportError:
            logger.warning("DataFetcherManager 未找到，使用占位数据")
            return self._get_placeholder_quote(stock_code)
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}", exc_info=True)
            return None
    
    def get_history_data(
        self,
        stock_code: str,
        period: str = "daily",
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取股票历史行情
        
        Args:
            stock_code: 股票代码
            period: K 线周期 (daily/weekly/monthly)
            days: 获取天数
            
        Returns:
            历史行情数据字典
            
        Raises:
            ValueError: 当 period 不是 daily 时抛出（weekly/monthly 暂未实现）
        """
        # 验证 period 参数，只支持 daily
        if period != "daily":
            raise ValueError(
                f"暂不支持 '{period}' 周期，目前仅支持 'daily'。"
                "weekly/monthly 聚合功能将在后续版本实现。"
            )
        
        try:
            # 调用数据获取器获取历史数据
            from data_provider.base import DataFetcherManager
            
            manager = DataFetcherManager()
            df, source = manager.get_daily_data(stock_code, days=days)
            
            if df is None or df.empty:
                logger.warning(f"获取 {stock_code} 历史数据失败")
                return {"stock_code": stock_code, "period": period, "data": []}
            
            # 获取股票名称
            stock_name = manager.get_stock_name(stock_code)
            
            # 转换为响应格式
            data = []
            for _, row in df.iterrows():
                date_val = row.get("date")
                if hasattr(date_val, "strftime"):
                    date_str = date_val.strftime("%Y-%m-%d")
                else:
                    date_str = str(date_val)
                
                data.append({
                    "date": date_str,
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": float(row.get("volume", 0)) if row.get("volume") else None,
                    "amount": float(row.get("amount", 0)) if row.get("amount") else None,
                    "change_percent": float(row.get("pct_chg", 0)) if row.get("pct_chg") else None,
                })
            
            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "period": period,
                "data": data,
            }
            
        except ImportError:
            logger.warning("DataFetcherManager 未找到，返回空数据")
            return {"stock_code": stock_code, "period": period, "data": []}
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}", exc_info=True)
            return {"stock_code": stock_code, "period": period, "data": []}
    
    def _get_placeholder_quote(self, stock_code: str) -> Dict[str, Any]:
        """
        获取占位行情数据（用于测试）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            占位行情数据
        """
        return {
            "stock_code": stock_code,
            "stock_name": f"股票{stock_code}",
            "current_price": 0.0,
            "change": None,
            "change_percent": None,
            "open": None,
            "high": None,
            "low": None,
            "prev_close": None,
            "volume": None,
            "amount": None,
            "update_time": datetime.now().isoformat(),
        }
