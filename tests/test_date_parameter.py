#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试指定日期选股功能
"""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import parse_target_date
from screeners.stock_screener import StockScreener
from config import get_config


def test_parse_target_date():
    """测试日期解析"""
    print("Testing parse_target_date...")

    # Test valid date
    result = parse_target_date("2024-01-15")
    assert result == date(2024, 1, 15), f"Expected 2024-01-15, got {result}"
    print("  ✓ Valid date parsing works")

    # Test None
    result = parse_target_date(None)
    assert result is None, f"Expected None, got {result}"
    print("  ✓ None handling works")

    # Test invalid format
    try:
        parse_target_date("invalid")
        assert False, "Should have raised ValueError"
    except ValueError:
        print("  ✓ Invalid format raises error")

    # Test future date
    future = (date.today() + timedelta(days=10)).strftime('%Y-%m-%d')
    try:
        parse_target_date(future)
        assert False, "Should have raised ValueError for future date"
    except ValueError:
        print("  ✓ Future date raises error")


def test_screener_with_date():
    """测试选股器接受日期参数"""
    print("\nTesting StockScreener with target_date...")

    config = get_config()
    screener = StockScreener()

    # Check that screen_market accepts target_date parameter
    import inspect
    sig = inspect.signature(screener.screen_market)
    params = list(sig.parameters.keys())

    assert 'target_date' in params, f"target_date not in parameters: {params}"
    print("  ✓ screen_market has target_date parameter")


def test_historical_date_parsing():
    """测试历史日期解析"""
    print("\nTesting historical date parsing...")

    test_dates = [
        "2024-01-15",
        "2023-12-31",
        "2022-06-30",
    ]

    for date_str in test_dates:
        result = parse_target_date(date_str)
        expected = datetime.strptime(date_str, '%Y-%m-%d').date()
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"  ✓ {date_str} -> {result}")


if __name__ == "__main__":
    print("=" * 60)
    print("Running Date Parameter Tests")
    print("=" * 60)

    try:
        test_parse_target_date()
        test_screener_with_date()
        test_historical_date_parsing()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
