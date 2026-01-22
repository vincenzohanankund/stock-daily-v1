# -*- coding: utf-8 -*-
"""
===================================
股票名称获取服务
===================================

职责：
1. 提供健壮的股票名称获取功能
2. 启动时批量加载所有A股股票名称（5000+）
3. 多数据源支持（优先级：缓存 > 东方财富 > 雪球 > 硬编码字典）
4. 失败自动降级，确保始终返回可用名称

设计理念：
- 启动时批量加载：大幅提升缓存命中率（>99%）
- 解耦股票名称获取和实时行情获取
- 提供简单的 get_stock_name(code) 接口
- 失败时返回友好的 fallback 名称
- 增强容错：超时重试机制，高并发场景下更稳定
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

    多层容错策略（按优先级）：
    0. 启动时批量加载（Tushare Pro > AkShare）→ 预缓存 5000+ 股票
    1. 优先使用内存缓存（命中率 >99%）
    2. 缓存未命中 → 从东财单个获取（ak.stock_individual_info_em，超时5秒+重试2次）
    3. 东财失败 → 从雪球单个获取（ak.stock_individual_basic_info_xq，超时5秒+重试2次）
    4. 雪球失败 → 硬编码字典（15个常用股票）
    5. 最终 fallback → "股票{code}"（保证非空）

    增强特性：
    - 启动时批量加载：大幅提升缓存命中率
    - 双源批量获取：Tushare（稳定）+ AkShare（免费）
    - 多层降级机制：东财 → 雪球 → 字典 → fallback
    - 超时和重试：避免接口无响应时长时间等待
    """

    def __init__(self):
        """初始化股票名称服务"""
        self._name_cache: Dict[str, str] = {}  # 缓存：code -> name

        # Step 1: 批量加载所有A股股票名称
        loaded_count = self._bulk_load_stock_names()

        if loaded_count > 0:
            logger.info(f"股票名称服务初始化完成，已加载 {loaded_count} 个股票")
        else:
            # Step 2: 批量加载失败，使用硬编码字典作为 fallback
            logger.warning("批量加载失败，使用硬编码字典作为初始缓存")
            self._name_cache.update(STOCK_NAME_MAP)
            logger.info(f"股票名称服务初始化完成，预缓存 {len(STOCK_NAME_MAP)} 个股票")

    def _has_tushare_token(self) -> bool:
        """检查是否配置了 Tushare Token"""
        try:
            import os
            token = os.getenv('TUSHARE_TOKEN')
            return bool(token and token.strip())
        except:
            return False

    def _bulk_load_stock_names(self) -> int:
        """
        批量加载所有A股股票名称（启动时调用）

        数据源优先级：
        1. Tushare Pro API（如果配置了 TUSHARE_TOKEN）
        2. AkShare stock_info_a_code_name（免费备选）

        Returns:
            成功加载的股票数量
        """
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("批量加载超时")

        # 设置 30 秒超时
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
        except (ValueError, AttributeError):
            # Windows 不支持 signal.SIGALRM
            pass

        try:
            # 方案1: 尝试 Tushare（优先，最稳定）
            if self._has_tushare_token():
                try:
                    import tushare as ts

                    logger.debug("[批量加载] 尝试从 Tushare 获取股票列表...")
                    pro = ts.pro_api()

                    df = pro.stock_basic(
                        exchange='',        # 空表示所有交易所
                        list_status='L',    # L=上市
                        fields='symbol,name'
                    )

                    stock_dict = dict(zip(df['symbol'], df['name']))
                    self._name_cache.update(stock_dict)

                    # 取消超时
                    try:
                        signal.alarm(0)
                    except (ValueError, AttributeError):
                        pass

                    logger.info(f"[批量加载] 从 Tushare 获取 {len(stock_dict)} 个股票名称")
                    return len(stock_dict)

                except Exception as e:
                    logger.warning(f"[批量加载] Tushare 失败: {e}，降级到 AkShare")

            # 方案2: AkShare 批量获取（降级）
            try:
                import akshare as ak

                logger.debug("[批量加载] 尝试从 AkShare 获取股票列表...")

                # 尝试获取股票列表，忽略北交所等网络错误
                try:
                    df = ak.stock_info_a_code_name()
                except Exception as fetch_error:
                    # 如果是网络错误（北交所等），尝试只获取沪深股票
                    logger.warning(f"[批量加载] AkShare 完整获取失败: {fetch_error}")

                    # 返回空列表，让硬编码字典作为 fallback
                    # 取消超时
                    try:
                        signal.alarm(0)
                    except (ValueError, AttributeError):
                        pass

                    return 0

                if df is not None and not df.empty:
                    stock_dict = dict(zip(df['code'], df['name']))
                    self._name_cache.update(stock_dict)

                    # 取消超时
                    try:
                        signal.alarm(0)
                    except (ValueError, AttributeError):
                        pass

                    logger.info(f"[批量加载] 从 AkShare 获取 {len(stock_dict)} 个股票名称")
                    return len(stock_dict)
                else:
                    logger.warning("[批量加载] AkShare 返回空数据")

                    # 取消超时
                    try:
                        signal.alarm(0)
                    except (ValueError, AttributeError):
                        pass

                    return 0

            except Exception as e:
                logger.error(f"[批量加载] AkShare 失败: {e}，批量加载终止")

                # 取消超时
                try:
                    signal.alarm(0)
                except (ValueError, AttributeError):
                    pass

                return 0

        except TimeoutError:
            logger.error("[批量加载] 超时（30秒），跳过批量加载")

            # 取消超时
            try:
                signal.alarm(0)
            except (ValueError, AttributeError):
                pass

            return 0

    def get_stock_name(self, code: str, force_refresh: bool = False) -> str:
        """
        获取股票名称（带缓存）

        流程：
        1. 检查内存缓存（启动时已批量加载 5000+）
        2. 缓存未命中 → 尝试东财接口
        3. 东财失败 → 尝试雪球接口
        4. 雪球失败 → 使用硬编码字典
        5. 最终 fallback → f'股票{code}'

        Args:
            code: 股票代码
            force_refresh: 是否强制刷新缓存

        Returns:
            股票名称（保证非空）
        """
        # Step 1: 检查缓存（除非强制刷新）
        if not force_refresh and code in self._name_cache:
            return self._name_cache[code]

        # Step 2: 尝试从东财获取（带超时和重试）
        name = self._fetch_from_eastmoney(code)

        if name:
            self._name_cache[code] = name
            return name

        # Step 2.5: 尝试从雪球获取（新增备用数据源）
        name = self._fetch_from_xueqiu(code)

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

    def _fetch_from_eastmoney(self, code: str, max_retries: int = 2, timeout: int = 5) -> Optional[str]:
        """
        从东方财富获取股票名称（带重试和超时）

        使用 ak.stock_individual_info_em() 接口

        优化策略：
        - 设置超时时间，避免长时间等待
        - 失败后重试，提高成功率

        Args:
            code: 股票代码
            max_retries: 最大重试次数（默认2次）
            timeout: 超时时间（秒，默认5秒）

        Returns:
            股票名称，失败返回 None
        """
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("API 调用超时")

        for attempt in range(1, max_retries + 1):
            try:
                import akshare as ak

                logger.debug(f"[API调用] ak.stock_individual_info_em(symbol={code}) 获取股票名称... (尝试 {attempt}/{max_retries})")

                # 设置超时（仅在 Unix 系统上）
                try:
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout)
                except (ValueError, AttributeError):
                    # Windows 不支持 signal.SIGALRM
                    pass

                # 获取个股信息
                df = ak.stock_individual_info_em(symbol=code)

                # 取消超时
                try:
                    signal.alarm(0)
                except (ValueError, AttributeError):
                    pass

                if df.empty:
                    logger.debug(f"[API返回] 东财接口返回空数据")
                    continue

                # 提取股票名称
                # df 格式：item | value
                # 查找 item='股票简称' 的行
                name_row = df[df['item'] == '股票简称']

                if name_row.empty:
                    logger.debug(f"[API返回] 东财接口未找到'股票简称'字段")
                    continue

                name = str(name_row.iloc[0]['value']).strip()

                if name:
                    logger.info(f"[{code}] 成功获取股票名称: {name}")
                    return name

            except TimeoutError:
                logger.debug(f"[{code}] 东财接口超时 (尝试 {attempt}/{max_retries})")
                try:
                    signal.alarm(0)
                except (ValueError, AttributeError):
                    pass
                continue

            except Exception as e:
                logger.debug(f"[{code}] 东财接口失败: {e} (尝试 {attempt}/{max_retries})")
                continue

        logger.debug(f"[{code}] 东财接口所有尝试均失败")
        return None

    def _convert_code_to_xueqiu_symbol(self, code: str) -> str:
        """
        将A股代码转换为雪球格式

        规则：
        - 上交所（60xxxx）: SH + 代码 -> SH600519
        - 深交所（00xxxx, 30xxxx）: SZ + 代码 -> SZ000001
        - 北交所（4xxxxx, 8xxxxx）: BJ + 代码

        Args:
            code: 6位股票代码

        Returns:
            雪球格式代码（带市场前缀）

        Examples:
            >>> _convert_code_to_xueqiu_symbol('600519')
            'SH600519'
            >>> _convert_code_to_xueqiu_symbol('000001')
            'SZ000001'
        """
        if code.startswith('6'):
            return f'SH{code}'
        elif code.startswith(('0', '3')):
            return f'SZ{code}'
        elif code.startswith(('4', '8')):
            return f'BJ{code}'
        else:
            # 未知格式，直接返回
            logger.debug(f"[代码转换] 未知股票代码格式: {code}")
            return code

    def _fetch_from_xueqiu(self, code: str, max_retries: int = 2, timeout: int = 5) -> Optional[str]:
        """
        从雪球获取股票名称（带重试和超时）

        使用 ak.stock_individual_basic_info_xq() 接口

        优化策略：
        - 设置超时时间，避免长时间等待
        - 失败后重试，提高成功率

        Args:
            code: 股票代码（6位数字）
            max_retries: 最大重试次数（默认2次）
            timeout: 超时时间（秒，默认5秒）

        Returns:
            股票名称，失败返回 None
        """
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("API 调用超时")

        for attempt in range(1, max_retries + 1):
            try:
                import akshare as ak

                # 转换代码格式
                xueqiu_symbol = self._convert_code_to_xueqiu_symbol(code)

                logger.debug(f"[API调用] ak.stock_individual_basic_info_xq(symbol={xueqiu_symbol}) 获取股票名称... (尝试 {attempt}/{max_retries})")

                # 设置超时（仅在 Unix 系统上）
                try:
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout)
                except (ValueError, AttributeError):
                    # Windows 不支持 signal.SIGALRM
                    pass

                # 获取雪球个股信息
                df = ak.stock_individual_basic_info_xq(symbol=xueqiu_symbol)

                # 取消超时
                try:
                    signal.alarm(0)
                except (ValueError, AttributeError):
                    pass

                if df.empty:
                    logger.debug(f"[API返回] 雪球接口返回空数据")
                    continue

                # 提取股票名称
                # df 格式：item | value
                # 查找 item='org_short_name_cn' 的行
                name_row = df[df['item'] == 'org_short_name_cn']

                if name_row.empty:
                    logger.debug(f"[API返回] 雪球接口未找到'org_short_name_cn'字段")
                    continue

                name = str(name_row.iloc[0]['value']).strip()

                if name and name != 'None':
                    logger.info(f"[{code}] 成功从雪球获取股票名称: {name}")
                    return name

            except TimeoutError:
                logger.debug(f"[{code}] 雪球接口超时 (尝试 {attempt}/{max_retries})")
                try:
                    signal.alarm(0)
                except (ValueError, AttributeError):
                    pass
                continue

            except Exception as e:
                logger.debug(f"[{code}] 雪球接口失败: {e} (尝试 {attempt}/{max_retries})")
                continue

        logger.debug(f"[{code}] 雪球接口所有尝试均失败")
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

    # 测试 1: 查看批量加载结果
    print(f"\n1. 批量加载统计: 缓存中共 {len(service._name_cache)} 个股票")
    if len(service._name_cache) > 0:
        print(f"   示例股票: {list(service._name_cache.items())[:5]}")

    # 测试 2: 缓存命中（批量加载的股票）
    print(f"\n2. 测试缓存命中:")
    print(f"   600519 -> {service.get_stock_name('600519')}")
    print(f"   000001 -> {service.get_stock_name('000001')}")
    print(f"   300750 -> {service.get_stock_name('300750')}")

    # 测试 3: 代码转换
    print(f"\n3. 测试代码转换:")
    print(f"   600519 -> {service._convert_code_to_xueqiu_symbol('600519')}")  # SH600519
    print(f"   000001 -> {service._convert_code_to_xueqiu_symbol('000001')}")  # SZ000001
    print(f"   300750 -> {service._convert_code_to_xueqiu_symbol('300750')}")  # SZ300750

    # 测试 4: 雪球接口（强制刷新测试）
    print(f"\n4. 测试雪球接口:")
    print(f"   601127 -> {service.get_stock_name('601127', force_refresh=True)}")

    # 测试 5: 无效代码（fallback）
    print(f"\n5. 测试 fallback: 999999 -> {service.get_stock_name('999999')}")

    # 测试 6: 批量更新
    print(f"\n6. 测试批量更新:")
    codes = ['002594', '600036', '601318']
    names = service.batch_update_names(codes)
    for code, name in names.items():
        print(f"   {code} -> {name}")

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
