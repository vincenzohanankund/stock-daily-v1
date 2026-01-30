# -*- coding: utf-8 -*-
"""
===================================
股票名称服务模块
===================================

职责：
1. 管理股票代码到名称的映射
2. 从 akshare 加载 A股/港股/美股 列表
3. 检测新股上市并自动更新映射
4. 提供本地缓存机制

接口来源：
- A股：ak.stock_zh_a_spot_em() - 东方财富沪深京A股实时行情
- 港股：ak.stock_hk_spot_em() - 东方财富港股实时行情
- 美股：ak.stock_us_spot_em() - 东方财富美股实时行情
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Set, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 缓存文件路径
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
STOCK_NAME_CACHE_FILE = CACHE_DIR / "stock_names.json"


@dataclass
class StockNameCache:
    """股票名称缓存数据结构"""
    a_stocks: Dict[str, str] = field(default_factory=dict)   # A股: {code: name}
    hk_stocks: Dict[str, str] = field(default_factory=dict)  # 港股: {code: name}
    us_stocks: Dict[str, str] = field(default_factory=dict)  # 美股: {code: name}
    last_update: str = ""                                     # 最后更新时间
    version: str = "1.0"                                      # 缓存版本


class StockNameService:
    """
    股票名称服务

    功能：
    1. 获取股票名称（优先本地缓存，fallback 到 akshare）
    2. 定期刷新股票列表
    3. 检测新股上市
    """

    # 缓存有效期（小时）
    CACHE_TTL_HOURS = 24

    # 内存缓存
    _instance: Optional['StockNameService'] = None
    _cache: Optional[StockNameCache] = None
    _last_load_time: Optional[datetime] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化服务"""
        if self._cache is None:
            self._ensure_cache_dir()
            self._load_cache()

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> bool:
        """
        从文件加载缓存

        Returns:
            是否成功加载
        """
        try:
            if STOCK_NAME_CACHE_FILE.exists():
                with open(STOCK_NAME_CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._cache = StockNameCache(
                        a_stocks=data.get('a_stocks', {}),
                        hk_stocks=data.get('hk_stocks', {}),
                        us_stocks=data.get('us_stocks', {}),
                        last_update=data.get('last_update', ''),
                        version=data.get('version', '1.0')
                    )
                    self._last_load_time = datetime.now()
                    logger.info(f"[股票名称] 从缓存加载成功: A股 {len(self._cache.a_stocks)} 只, "
                              f"港股 {len(self._cache.hk_stocks)} 只, 美股 {len(self._cache.us_stocks)} 只")
                    return True
        except Exception as e:
            logger.warning(f"[股票名称] 加载缓存失败: {e}")

        # 初始化空缓存
        self._cache = StockNameCache()
        return False

    def _save_cache(self):
        """保存缓存到文件"""
        try:
            self._cache.last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(STOCK_NAME_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'a_stocks': self._cache.a_stocks,
                    'hk_stocks': self._cache.hk_stocks,
                    'us_stocks': self._cache.us_stocks,
                    'last_update': self._cache.last_update,
                    'version': self._cache.version
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"[股票名称] 缓存已保存: {STOCK_NAME_CACHE_FILE}")
        except Exception as e:
            logger.error(f"[股票名称] 保存缓存失败: {e}")

    def _is_cache_expired(self) -> bool:
        """检查缓存是否过期"""
        if not self._cache or not self._cache.last_update:
            return True

        try:
            last_update = datetime.strptime(self._cache.last_update, '%Y-%m-%d %H:%M:%S')
            return datetime.now() - last_update > timedelta(hours=self.CACHE_TTL_HOURS)
        except Exception:
            return True

    def get_stock_name(self, code: str) -> Optional[str]:
        """
        获取股票名称

        Args:
            code: 股票代码

        Returns:
            股票名称，未找到返回 None
        """
        if not self._cache:
            self._load_cache()

        # 标准化代码
        code = code.upper().strip()

        # 尝试从缓存获取
        # A股
        if code in self._cache.a_stocks:
            return self._cache.a_stocks[code]

        # 港股（可能带前缀 hk 或不带）
        hk_code = code.replace('HK', '').lstrip('0').zfill(5)
        if hk_code in self._cache.hk_stocks:
            return self._cache.hk_stocks[hk_code]
        if code in self._cache.hk_stocks:
            return self._cache.hk_stocks[code]

        # 美股
        if code in self._cache.us_stocks:
            return self._cache.us_stocks[code]

        return None

    def refresh_all_stocks(self, force: bool = False) -> Dict[str, int]:
        """
        刷新所有股票列表

        Args:
            force: 是否强制刷新（忽略缓存有效期）

        Returns:
            各市场股票数量统计
        """
        if not force and not self._is_cache_expired():
            logger.info("[股票名称] 缓存未过期，跳过刷新")
            return {
                'a_stocks': len(self._cache.a_stocks),
                'hk_stocks': len(self._cache.hk_stocks),
                'us_stocks': len(self._cache.us_stocks),
            }

        logger.info("[股票名称] 开始刷新股票列表...")
        stats = {}

        # 刷新 A股
        a_count = self._refresh_a_stocks()
        stats['a_stocks'] = a_count

        # 刷新 港股
        hk_count = self._refresh_hk_stocks()
        stats['hk_stocks'] = hk_count

        # 刷新 美股
        us_count = self._refresh_us_stocks()
        stats['us_stocks'] = us_count

        # 保存缓存
        self._save_cache()

        logger.info(f"[股票名称] 刷新完成: A股 {a_count}, 港股 {hk_count}, 美股 {us_count}")
        return stats

    def _refresh_a_stocks(self) -> int:
        """刷新 A股列表"""
        try:
            import akshare as ak
            logger.info("[股票名称] 正在获取 A股列表...")

            # 随机休眠避免限流
            time.sleep(2)

            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                # 提取代码和名称
                for _, row in df.iterrows():
                    code = str(row.get('代码', ''))
                    name = str(row.get('名称', ''))
                    if code and name:
                        self._cache.a_stocks[code] = name

                logger.info(f"[股票名称] A股列表获取成功: {len(self._cache.a_stocks)} 只")
                return len(self._cache.a_stocks)

        except Exception as e:
            logger.error(f"[股票名称] 获取 A股列表失败: {e}")

        return len(self._cache.a_stocks)

    def _refresh_hk_stocks(self) -> int:
        """刷新港股列表"""
        try:
            import akshare as ak
            logger.info("[股票名称] 正在获取港股列表...")

            # 随机休眠避免限流
            time.sleep(2)

            df = ak.stock_hk_spot_em()
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    code = str(row.get('代码', ''))
                    name = str(row.get('名称', ''))
                    if code and name:
                        # 标准化为5位
                        code = code.zfill(5)
                        self._cache.hk_stocks[code] = name

                logger.info(f"[股票名称] 港股列表获取成功: {len(self._cache.hk_stocks)} 只")
                return len(self._cache.hk_stocks)

        except Exception as e:
            logger.error(f"[股票名称] 获取港股列表失败: {e}")

        return len(self._cache.hk_stocks)

    def _refresh_us_stocks(self) -> int:
        """刷新美股列表"""
        try:
            import akshare as ak
            logger.info("[股票名称] 正在获取美股列表...")

            # 随机休眠避免限流
            time.sleep(2)

            df = ak.stock_us_spot_em()
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    raw_code = str(row.get('代码', ''))
                    name = str(row.get('名称', ''))
                    if raw_code and name:
                        # 美股代码格式: "105.AAPL" -> "AAPL"
                        code = raw_code.split('.')[-1] if '.' in raw_code else raw_code
                        self._cache.us_stocks[code] = name

                logger.info(f"[股票名称] 美股列表获取成功: {len(self._cache.us_stocks)} 只")
                return len(self._cache.us_stocks)

        except Exception as e:
            logger.error(f"[股票名称] 获取美股列表失败: {e}")

        return len(self._cache.us_stocks)

    def check_new_stocks(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        检测新股上市

        比较当前列表和缓存列表，返回新增的股票

        Returns:
            各市场新股列表 {market: [(code, name), ...]}
        """
        logger.info("[股票名称] 检测新股上市...")

        # 保存旧的股票代码集合
        old_a_codes = set(self._cache.a_stocks.keys())
        old_hk_codes = set(self._cache.hk_stocks.keys())
        old_us_codes = set(self._cache.us_stocks.keys())

        # 刷新列表
        self.refresh_all_stocks(force=True)

        # 比较差异
        new_stocks = {
            'a_stocks': [],
            'hk_stocks': [],
            'us_stocks': [],
        }

        # 检测 A股新股
        new_a_codes = set(self._cache.a_stocks.keys()) - old_a_codes
        for code in new_a_codes:
            new_stocks['a_stocks'].append((code, self._cache.a_stocks[code]))

        # 检测港股新股
        new_hk_codes = set(self._cache.hk_stocks.keys()) - old_hk_codes
        for code in new_hk_codes:
            new_stocks['hk_stocks'].append((code, self._cache.hk_stocks[code]))

        # 检测美股新股
        new_us_codes = set(self._cache.us_stocks.keys()) - old_us_codes
        for code in new_us_codes:
            new_stocks['us_stocks'].append((code, self._cache.us_stocks[code]))

        # 记录结果
        total_new = sum(len(v) for v in new_stocks.values())
        if total_new > 0:
            logger.info(f"[股票名称] 检测到新股上市: A股 {len(new_stocks['a_stocks'])} 只, "
                      f"港股 {len(new_stocks['hk_stocks'])} 只, 美股 {len(new_stocks['us_stocks'])} 只")

            # 记录具体新股
            for market, stocks in new_stocks.items():
                if stocks:
                    market_name = {'a_stocks': 'A股', 'hk_stocks': '港股', 'us_stocks': '美股'}[market]
                    for code, name in stocks[:10]:  # 最多显示10只
                        logger.info(f"  [新股] {market_name}: {code} - {name}")
                    if len(stocks) > 10:
                        logger.info(f"  ... 共 {len(stocks)} 只新股")
        else:
            logger.info("[股票名称] 未检测到新股上市")

        return new_stocks

    def export_to_dict(self) -> Dict[str, str]:
        """
        导出为 STOCK_NAME_MAP 格式的字典

        用于更新 analyzer.py 中的静态映射表

        Returns:
            合并后的股票名称映射字典
        """
        result = {}

        # 合并所有市场
        result.update(self._cache.a_stocks)

        # 港股保持5位格式
        for code, name in self._cache.hk_stocks.items():
            result[code.zfill(5)] = name

        # 美股保持原始格式
        result.update(self._cache.us_stocks)

        return result

    def get_statistics(self) -> Dict[str, any]:
        """获取统计信息"""
        return {
            'a_stocks_count': len(self._cache.a_stocks),
            'hk_stocks_count': len(self._cache.hk_stocks),
            'us_stocks_count': len(self._cache.us_stocks),
            'total_count': len(self._cache.a_stocks) + len(self._cache.hk_stocks) + len(self._cache.us_stocks),
            'last_update': self._cache.last_update,
            'cache_file': str(STOCK_NAME_CACHE_FILE),
        }


# 全局单例
_service_instance: Optional[StockNameService] = None


def get_stock_name_service() -> StockNameService:
    """获取股票名称服务单例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = StockNameService()
    return _service_instance


def get_stock_name(code: str) -> Optional[str]:
    """
    便捷函数：获取股票名称

    Args:
        code: 股票代码

    Returns:
        股票名称，未找到返回 None
    """
    return get_stock_name_service().get_stock_name(code)


def refresh_stock_names(force: bool = False) -> Dict[str, int]:
    """
    便捷函数：刷新股票名称缓存

    Args:
        force: 是否强制刷新

    Returns:
        各市场股票数量统计
    """
    return get_stock_name_service().refresh_all_stocks(force=force)


def check_new_stocks() -> Dict[str, List[Tuple[str, str]]]:
    """
    便捷函数：检测新股上市

    Returns:
        各市场新股列表
    """
    return get_stock_name_service().check_new_stocks()


# ========== 测试入口 ==========
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )

    print("=" * 60)
    print("股票名称服务测试")
    print("=" * 60)

    service = get_stock_name_service()

    # 1. 获取统计信息
    stats = service.get_statistics()
    print(f"\n当前缓存统计:")
    print(f"  A股: {stats['a_stocks_count']} 只")
    print(f"  港股: {stats['hk_stocks_count']} 只")
    print(f"  美股: {stats['us_stocks_count']} 只")
    print(f"  最后更新: {stats['last_update'] or '从未更新'}")

    # 2. 测试获取名称
    test_codes = ['600519', '000001', '00700', 'AAPL', 'TSLA']
    print(f"\n测试获取股票名称:")
    for code in test_codes:
        name = service.get_stock_name(code)
        print(f"  {code} -> {name or '未找到'}")

    # 3. 询问是否刷新
    user_input = input("\n是否刷新股票列表? (y/n): ")
    if user_input.lower() == 'y':
        stats = service.refresh_all_stocks(force=True)
        print(f"\n刷新完成:")
        print(f"  A股: {stats['a_stocks']} 只")
        print(f"  港股: {stats['hk_stocks']} 只")
        print(f"  美股: {stats['us_stocks']} 只")

        # 再次测试
        print(f"\n刷新后测试获取股票名称:")
        for code in test_codes:
            name = service.get_stock_name(code)
            print(f"  {code} -> {name or '未找到'}")
