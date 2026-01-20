# -*- coding: utf-8 -*-
"""
===================================
股票名称获取服务
===================================

职责：
1. 提供健壮的股票名称获取功能
2. 多数据源支持（优先级：实时行情 > AkShare > 硬编码字典）
3. 带缓存机制，避免重复请求
4. 失败自动降级，确保始终返回可用名称

设计理念：
- 解耦股票名称获取和实时行情获取
- 提供简单的 get_stock_name(code) 接口
- 失败时返回友好的 fallback 名称
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# 常用股票名称字典（作为 fallback）
STOCK_NAME_MAP = {
    '600519': '贵州茅台',
    '000001': '平安银行',
    '300750': '宁德时代',
    '002594': '比亚迪',
    '600036': '招商银行',
    '601318': '中国平安',
    '000858': '五粮液',
    '600276': '恒瑞医药',
    '601012': '隆基绿能',
    '002475': '立讯精密',
    '300059': '东方财富',
    '002415': '海康威视',
    '600900': '长江电力',
    '601166': '兴业银行',
    '600028': '中国石化',
}


class StockNameService:
    """
    股票名称获取服务

    策略：
    1. 优先使用缓存
    2. 尝试从 AkShare 获取（调用 stock_individual_info_em）
    3. 回退到硬编码字典
    4. 最终 fallback 到 "股票{code}"
    """

    def __init__(self):
        """初始化股票名称服务"""
        self._name_cache: Dict[str, str] = {}  # 缓存：code -> name

        # 预填充缓存（硬编码字典）
        self._name_cache.update(STOCK_NAME_MAP)
        logger.debug(f"股票名称服务初始化完成，预缓存 {len(STOCK_NAME_MAP)} 个股票")

    def get_stock_name(self, code: str, force_refresh: bool = False) -> str:
        """
        获取股票名称（带缓存）

        Args:
            code: 股票代码
            force_refresh: 是否强制刷新缓存

        Returns:
            股票名称（保证非空）
        """
        # Step 1: 检查缓存（除非强制刷新）
        if not force_refresh and code in self._name_cache:
            return self._name_cache[code]

        # Step 2: 尝试从 AkShare 获取
        name = self._fetch_from_akshare(code)

        if name:
            self._name_cache[code] = name
            return name

        # Step 3: 回退到硬编码字典
        if code in STOCK_NAME_MAP:
            fallback_name = STOCK_NAME_MAP[code]
            logger.debug(f"[{code}] 使用硬编码字典: {fallback_name}")
            self._name_cache[code] = fallback_name
            return fallback_name

        # Step 4: 最终 fallback
        fallback_name = f'股票{code}'
        logger.warning(f"[{code}] 无法获取股票名称，使用 fallback: {fallback_name}")
        self._name_cache[code] = fallback_name
        return fallback_name

    def _fetch_from_akshare(self, code: str) -> Optional[str]:
        """
        从 AkShare 获取股票名称

        使用 ak.stock_individual_info_em() 接口获取个股信息
        这个接口比实时行情接口更轻量，只返回基本信息

        Args:
            code: 股票代码

        Returns:
            股票名称，失败返回 None
        """
        try:
            import akshare as ak

            logger.debug(f"[API调用] ak.stock_individual_info_em(symbol={code}) 获取股票名称...")

            # 获取个股信息
            df = ak.stock_individual_info_em(symbol=code)

            if df.empty:
                logger.warning(f"[API返回] ak.stock_individual_info_em 返回空数据")
                return None

            # 提取股票名称
            # df 格式：item | value
            # 查找 item='股票简称' 的行
            name_row = df[df['item'] == '股票简称']

            if name_row.empty:
                logger.warning(f"[API返回] 未找到'股票简称'字段")
                return None

            name = str(name_row.iloc[0]['value']).strip()

            if name:
                logger.info(f"[{code}] 成功获取股票名称: {name}")
                return name

            return None

        except Exception as e:
            logger.debug(f"[{code}] 从 AkShare 获取股票名称失败: {e}")
            return None

    def batch_update_names(self, codes: list[str]) -> Dict[str, str]:
        """
        批量更新股票名称（可选功能）

        Args:
            codes: 股票代码列表

        Returns:
            code -> name 映射字典
        """
        result = {}

        for code in codes:
            name = self.get_stock_name(code)
            result[code] = name

        logger.info(f"批量更新 {len(codes)} 个股票名称完成")
        return result

    def clear_cache(self) -> None:
        """清空缓存（保留硬编码字典）"""
        self._name_cache.clear()
        self._name_cache.update(STOCK_NAME_MAP)
        logger.info("股票名称缓存已清空")


# 全局单例
_stock_name_service: Optional[StockNameService] = None


def get_stock_name_service() -> StockNameService:
    """获取股票名称服务单例"""
    global _stock_name_service

    if _stock_name_service is None:
        _stock_name_service = StockNameService()

    return _stock_name_service


def get_stock_name(code: str, force_refresh: bool = False) -> str:
    """
    快捷函数：获取股票名称

    Args:
        code: 股票代码
        force_refresh: 是否强制刷新缓存

    Returns:
        股票名称
    """
    service = get_stock_name_service()
    return service.get_stock_name(code, force_refresh)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)

    service = StockNameService()

    print("=" * 50)
    print("测试股票名称获取")
    print("=" * 50)

    # 测试 1: 硬编码字典中的股票
    print(f"\n1. 测试硬编码字典: 600519 -> {service.get_stock_name('600519')}")

    # 测试 2: 不在字典中的股票（需要从 AkShare 获取）
    print(f"\n2. 测试 AkShare 获取: 300058 -> {service.get_stock_name('300058')}")

    # 测试 3: 缓存命中
    print(f"\n3. 测试缓存命中: 300058 -> {service.get_stock_name('300058')}")

    # 测试 4: 无效代码（fallback）
    print(f"\n4. 测试 fallback: 999999 -> {service.get_stock_name('999999')}")

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
