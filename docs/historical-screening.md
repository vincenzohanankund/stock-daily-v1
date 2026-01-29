# 历史日期选股功能说明

## 功能概述

支持指定任意历史交易日进行选股分析，用于：
- 回测选股策略效果
- 分析历史选股结果
- 验证策略在不同市场环境下的表现

## 使用方法

### 基本用法

```bash
python main.py --screen --date YYYY-MM-DD
```

### 完整示例

```bash
# 2024年1月15日选股
python main.py --screen --date 2024-01-15

# 指定日期 + 技术筛选
python main.py --screen --date 2024-01-15 --screen-mode tech_only

# 指定日期 + 自动分析
python main.py --screen --date 2024-01-15 --auto-analyze
```

## 数据要求

历史日期选股需要：
1. 数据库中存在该日期的股票行情数据
2. 如果数据不存在，系统会尝试从API获取（取决于数据源的历史数据支持）

## 限制

- 不支持未来日期
- 日期格式必须严格为 YYYY-MM-DD
- 非交易日可能导致数据缺失
