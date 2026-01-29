# 📈 A股智能分析系统

[![GitHub stars](https://img.shields.io/github/stars/ZhuLinsen/daily_stock_analysis?style=social)](https://github.com/ZhuLinsen/daily_stock_analysis/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Ready-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)

> 🤖 基于 AI 大模型的 A 股智能分析系统，整合多种选股策略，每日自动分析并推送「决策仪表盘」到企业微信/飞书/Telegram/邮箱

![运行效果演示](./sources/2026-01-10_155341_daily_analysis.gif)

## ✨ 功能特性

### 🎯 核心功能

#### AI 智能分析
- **AI 决策仪表盘** - 一句话核心结论 + 精确买卖点位 + 检查清单
- **多维度分析** - 技术面 + 筹码分布 + 與情情报 + 实时行情
- **大盘复盘** - 每日市场概览、板块涨跌、北向资金

#### 策略选股（整合 StockTradebyZ）
- **6种战法选股** - 少妇战法、SuperB1、填坑战法、补票战法、上穿60放量、暴力K战法
- **技术指标筛选** - 趋势强度、乖离率、量比等多维度过滤
- **AI 深度精选** - 对选出的股票进行 AI 深度分析
- **一键运行** - 自动选股 + 分析 + 报告 + 推送

#### 通知推送
- **多渠道推送** - 企业微信、飞书、Telegram、邮件
- **自定义 Webhook** - 支持钉钉、Discord、Slack、Bark 等
- **自动识别** - 邮箱 SMTP 服务器自动识别

#### 部署方式
- **零成本部署** - GitHub Actions 免费运行，无需服务器
- **Docker 支持** - 一键部署到本地或云服务器
- **定时任务** - 支持内置调度器和系统 cron

### 📊 数据来源

| 类型 | 来源 | 说明 |
|------|------|------|
| **行情数据** | AkShare | 免费开源 |
| **行情数据** | Tushare Pro | 需要 Token |
| **行情数据** | Baostock | 免费备用 |
| **行情数据** | YFinance | 国际市场 |
| **新闻搜索** | Tavily | 推荐 |
| **新闻搜索** | SerpAPI | 备用 |
| **AI 分析** | Google Gemini | 免费额度 |
| **AI 分析** | OpenAI 兼容 | DeepSeek、通义等 |

### 🛡️ 交易理念

- ❌ **严禁追高** - 乖离率 > 5% 自动标记「危险」
- ✅ **趋势交易** - MA5 > MA10 > MA20 多头排列
- 📍 **精确点位** - 买入价、止损价、目标价
- 📋 **检查清单** - 每项条件用 ✅⚠️❌ 标记

## 🚀 快速开始

### 方式一：GitHub Actions（推荐，零成本）

**无需服务器，每天自动运行！**

#### 1. Fork 本仓库

点击右上角 `Fork` 按钮

#### 2. 配置 Secrets

进入你 Fork 的仓库 → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

**必填配置**

| Secret 名称 | 说明 | 获取方式 |
|------------|------|----------|
| `GEMINI_API_KEY` | Google AI Studio 免费 Key | [获取](https://aistudio.google.com/) |
| `STOCK_LIST` | 自选股代码，如 `600519,300750,002594` | 自己选择 |

**通知配置（至少配置一个）**

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `WECHAT_WEBHOOK_URL` | 企业微信 Webhook | `https://qyapi.weixin.qq.com/...` |
| `FEISHU_WEBHOOK_URL` | 飞书 Webhook | `https://open.feishu.cn/...` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | `@BotFather 获取` |
| `EMAIL_SENDER` | 发件人邮箱 | `your@qq.com` |
| `EMAIL_PASSWORD` | 邮箱授权码 | QQ邮箱获取 |
| `CUSTOM_WEBHOOK_URLS` | 自定义 Webhook | 钉钉/Discord 等 |

**可选配置**

| Secret 名称 | 说明 |
|------------|------|
| `TAVILY_API_KEYS` | 新闻搜索 API |
| `TUSHARE_TOKEN` | Tushare Pro Token |
| `OPENAI_API_KEY` | OpenAI 兼容 API Key |
| `OPENAI_BASE_URL` | OpenAI 兼容 API 地址 |

#### 3. 启用 Actions

`Actions` 标签 → 点击 `I understand my workflows, go ahead and enable them`

#### 4. 手动测试

`Actions` → `每日股票分析` → `Run workflow` → `Run workflow`

#### 5. 完成！

默认每个工作日 **18:00（北京时间）** 自动执行

### 方式二：本地运行

```bash
# 克隆仓库
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git
cd daily_stock_analysis

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
vim .env  # 填入你的 API Key

# 运行分析
python main.py                    # 完整分析
python main.py --market-review    # 仅大盘复盘
python main.py --schedule         # 定时任务模式

# 策略选股
python main.py --strategy-screen                    # 运行所有策略
python main.py --strategy-screen --strategy 少妇战法  # 运行指定策略
python main.py --strategy-screen --auto-analyze      # 选股后自动分析

# 使用快速启动脚本
./run.sh
```

### 方式三：Docker 部署

```bash
# 配置环境变量
cp .env.example .env
vim .env

# 一键启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 📖 使用指南

### 1. 自选股分析

最常用的功能，分析你关注的股票：

```bash
python main.py
```

**输出结果：**
- 决策仪表盘（买入/观望/卖出建议）
- 精确点位（买入价、止损价、目标价）
- 检查清单（趋势、乖离率、量能等）
- 推送到配置的通知渠道

### 2. 策略选股（6种战法）

使用技术战法自动筛选股票：

```bash
# 方式1：使用 main.py
python main.py --strategy-screen                    # 所有策略
python main.py --strategy-screen --strategy 少妇战法  # 指定策略

# 方式2：使用一体化脚本
python scripts/auto_screen_and_analyze.py           # 选股+分析
python scripts/auto_screen_and_analyze.py --strategy 少妇战法  # 指定策略

# 方式3：使用 run.sh
./run.sh  # 选择模式1
```

**支持的策略：**

| 策略名称 | 核心逻辑 | 适用场景 |
|---------|---------|---------|
| 少妇战法 | BBI上升 + KDJ低位 | 趋势初期 |
| SuperB1战法 | 少妇战法增强版 | 趋势确认 |
| 填坑战法 | 峰值回调 + KDJ低位 | 回调买入 |
| 补票战法 | BBI + 短长期RSV | 补仓时机 |
| 上穿60放量战法 | MA60上穿 + 放量 | 突破买入 |
| 暴力K战法 | 大阳线 + 放量 | 强势追涨 |

**注意：** 策略选股需要先准备 K 线数据，参考下方「数据准备」章节。

### 3. 全市场选股

使用技术指标筛选全市场股票：

```bash
python main.py --screen --auto-analyze
```

**筛选条件：**
- 趋势强度 > 60
- 乖离率 < 5%
- 量比 0.8-3.0
- 价格区间 5-1000元

### 3.1 指定日期选股

支持使用历史日期进行选股分析：

```bash
# 使用指定日期选股
python main.py --screen --date 2024-01-15

# 指定日期选股 + 自动分析
python main.py --screen --date 2024-01-15 --auto-analyze

# 指定日期 + 技术筛选模式
python main.py --screen --date 2024-01-15 --screen-mode tech_only
```

**注意事项：**
- 历史日期选股需要确保数据库中有对应日期的数据
- 日期格式必须为 YYYY-MM-DD
- 不能指定未来日期

### 4. 仅大盘复盘

只分析大盘，不分析个股：

```bash
python main.py --market-review
```

**输出内容：**
- 主要指数表现
- 市场概况（涨跌家数）
- 板块表现
- 北向资金

### 5. 命令行参数

```bash
python main.py --help

# 常用参数
--debug              # 调试模式，输出详细日志
--dry-run            # 仅获取数据，不进行 AI 分析
--stocks STOCKS      # 指定股票代码（覆盖配置）
--no-notify          # 不发送推送通知
--workers N          # 并发线程数
--screen             # 运行全市场选股
--strategy-screen    # 使用策略选股
--market-review      # 仅大盘复盘
```

## 📁 项目结构

```
daily_stock_analysis/
├── main.py                      # 主程序入口
├── config.py                    # 配置管理
│
├── core/                        # 核心业务模块
│   ├── storage.py               # 数据存储层
│   ├── analyzer.py              # AI 分析模块
│   ├── stock_analyzer.py        # 趋势分析器
│   └── market_analyzer.py       # 大盘复盘
│
├── screeners/                   # 选股模块
│   ├── stock_screener.py        # 技术指标选股
│   ├── strategy_screener.py     # 战法选股
│   ├── Selector.py              # 战法实现
│   ├── select_stock.py          # 选股执行
│   ├── SectorShift.py           # 行业分析
│   └── configs/                 # 选股配置
│       └── selector_configs.json
│
├── services/                    # 服务模块
│   ├── notification.py          # 通知服务
│   ├── search_service.py        # 搜索服务
│   └── scheduler.py             # 定时任务
│
├── data_provider/               # 数据源
│   ├── akshare_fetcher.py       # AkShare 数据源
│   ├── tushare_fetcher.py       # Tushare 数据源
│   ├── baostock_fetcher.py      # Baostock 数据源
│   └── yfinance_fetcher.py      # YFinance 数据源
│
├── scripts/                     # 脚本工具
│   ├── auto_screen_and_analyze.py  # 自动选股+分析
│   └── verify_integration.py        # 验证脚本
│
├── docs/                        # 文档
│   ├── INTEGRATION.md           # 整合指南
│   └── 使用指南.md
│
└── run.sh                       # 快速启动脚本
```

## ⚙️ 配置说明

### 环境变量（.env）

```bash
# ==================== 必填配置 ====================
# AI 模型（二选一）
GEMINI_API_KEY=your_gemini_key          # Google AI Studio（推荐，免费）
OPENAI_API_KEY=your_openai_key          # OpenAI 兼容 API
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 自选股列表
STOCK_LIST=600519,300750,002594

# ==================== 通知配置（至少配置一个） ====================
# 企业微信
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# 飞书
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 邮件
EMAIL_SENDER=your@qq.com
EMAIL_PASSWORD=your_auth_code
EMAIL_RECEIVERS=receiver1@qq.com,receiver2@gmail.com

# 自定义 Webhook（钉钉、Discord、Slack、Bark 等）
CUSTOM_WEBHOOK_URLS=https://oapi.dingtalk.com/robot/send?access_token=xxx,https://discord.com/api/webhooks/xxx

# ==================== 推荐配置 ====================
# 搜索服务（用于获取新闻）
TAVILY_API_KEYS=your_tavily_key
SERPAPI_API_KEYS=your_serpapi_key

# 数据源
TUSHARE_TOKEN=your_tushare_token

# AI 模型配置
GEMINI_MODEL=gemini-3-flash-preview
GEMINI_MODEL_FALLBACK=gemini-2.5-flash
```

### 策略配置（screeners/configs/selector_configs.json）

```json
{
  "selectors": [
    {
      "class": "BBIKDJSelector",
      "alias": "少妇战法",
      "activate": true,
      "params": {
        "j_threshold": 15,
        "bbi_min_window": 20,
        "max_window": 120,
        "price_range_pct": 1,
        "bbi_q_threshold": 0.2,
        "j_q_threshold": 0.10
      }
    }
  ]
}
```

## 📊 数据准备

### 策略选股数据准备

策略选股需要 K 线数据（CSV 格式）：

#### 方式1：使用 AkShare 下载

```python
# scripts/download_data.py
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def download_stock_data(stock_code, save_path='./data'):
    """下载单只股票的 K 线数据"""
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

    df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                           start_date=start_date, end_date=end_date)
    df.to_csv(f'{save_path}/{stock_code}.csv', index=False)
    print(f'✅ {stock_code} 数据下载完成')

# 下载沪深300成分股
from akshare import stock_zh_index_spot
df = stock_zh_index_spot(symbol="000300")
for code in df['代码'].head(50):  # 下载前50只
    download_stock_data(code)
```

#### 方式2：使用 StockTradebyZ 的数据获取脚本

```bash
# 如果你有 StockTradebyZ 项目
cd ../StockTradebyZ
python fetch_kline.py --codes 000001,600519,300750
```

#### 数据格式要求

```
data/
├── 000001.csv  # 平安银行
├── 600519.csv  # 贵州茅台
└── 300750.csv  # 宁德时代
```

每 CSV 文件需包含以下列：
- `date` - 日期（YYYY-MM-DD 格式）
- `open` - 开盘价
- `high` - 最高价
- `low` - 最低价
- `close` - 收盘价
- `volume` - 成交量

## 📱 推送效果

### 决策仪表盘

```
📊 2026-01-10 决策仪表盘
3只股票 | 🟢买入:1 🟡观望:2 🔴卖出:0

🟢 买入 | 贵州茅台(600519)
📌 缩量回踩MA5支撑，乖离率1.2%处于最佳买点
💰 狙击: 买入1800 | 止损1750 | 目标1900
✅多头排列 ✅乖离安全 ✅量能配合

🟡 观望 | 宁德时代(300750)
📌 乖离率7.8%超过5%警戒线，严禁追高
⚠️ 等待回调至MA5附近再考虑

---
生成时间: 18:00
```

### 策略选股报告

```
📊 策略选股结果 (2026-01-29)

少妇战法: 000001, 600519, 300750
SuperB1战法: 000001, 002594
填坑战法: 603259

共振分析:
- 2次共振: 000001
- 1次共振: 600519, 300750, 002594, 603259
```

### 大盘复盘

```
🎯 2026-01-10 大盘复盘

📊 主要指数
- 上证指数: 3250.12 (🟢+0.85%)
- 深证成指: 10521.36 (🟢+1.02%)
- 创业板指: 2156.78 (🟢+1.35%)

📈 市场概况
上涨: 3920 | 下跌: 1349 | 涨停: 155 | 跌停: 3

🔥 板块表现
领涨: 互联网服务、文化传媒、小金属
领跌: 保险、航空机场、光伏设备
```

## 🔧 高级配置

### 定时任务配置

#### 使用 GitHub Actions

编辑 `.github/workflows/daily_analysis.yml`:

```yaml
schedule:
  # UTC 时间，北京时间 = UTC + 8
  - cron: '0 10 * * 1-5'   # 周一到周五 18:00（北京时间）
```

| 北京时间 | UTC cron |
|---------|----------|
| 09:30 开盘 | `'30 1 * * 1-5'` |
| 15:00 收盘 | `'0 7 * * 1-5'` |
| 18:00 盘后 | `'0 10 * * 1-5'` |

#### 使用系统 cron

```bash
crontab -e

# 每个交易日 18:00 执行
0 18 * * 1-5 cd /path/to/daily_stock_analysis && python main.py
```

#### 使用内置调度器

在 `.env` 中配置：

```bash
SCHEDULE_ENABLED=true
SCHEDULE_TIME=18:00
```

然后运行：

```bash
python main.py --schedule
```

### 自定义 Webhook 配置

支持任意接受 POST JSON 的 Webhook：

```bash
# 钉钉
CUSTOM_WEBHOOK_URLS=https://oapi.dingtalk.com/robot/send?access_token=xxx

# Discord
CUSTOM_WEBHOOK_URLS=https://discord.com/api/webhooks/xxx

# Slack
CUSTOM_WEBHOOK_URLS=https://hooks.slack.com/services/xxx

# Bark (iOS)
CUSTOM_WEBHOOK_URLS=https://api.day.app/your bark key/标题/内容

# 多个 Webhook（逗号分隔）
CUSTOM_WEBHOOK_URLS=https://oapi.dingtalk.com/xxx,https://discord.com/api/webhooks/xxx
```

## ❓ 常见问题

### Q1: 选股结果为空？

**原因：**
- data 目录为空或数据不足（需要至少 120 天历史数据）
- 策略参数过于严格
- 当前市场不符合策略条件

**解决：**
1. 检查数据：`ls data/*.csv | wc -l`
2. 调整策略参数（编辑 `screeners/configs/selector_configs.json`）
3. 尝试不同的策略

### Q2: AI 分析失败？

**原因：** 未配置 API Key 或 API 额度用完

**解决：**
```bash
# 检查 .env 文件
cat .env | grep GEMINI_API_KEY

# 或配置 OpenAI 兼容 API
echo "OPENAI_API_KEY=your_key" >> .env
echo "OPENAI_BASE_URL=https://api.deepseek.com/v1" >> .env
```

### Q3: 导入模块错误？

**原因：** 项目结构已重构，导入路径变化

**解决：** 确保使用正确的导入路径：
```python
from core.storage import DatabaseManager
from core.analyzer import GeminiAnalyzer
from screeners.stock_screener import StockScreener
from services.notification import NotificationService
```

### Q4: 邮件发送失败？

**常见原因：**
1. 邮箱授权码错误（不是登录密码）
2. SMTP 端口被防火墙阻止
3. 发送频率过高被限制

**解决：**
```bash
# QQ 邮箱获取授权码
# 设置 -> 账户 -> SMTP -> 开启服务 -> 生成授权码

# 163 邮箱获取授权码
# 设置 -> POP3/SMTP/IMAP -> 开启服务
```

### Q5: 如何添加自己的选股策略？

1. 在 `screeners/Selector.py` 中创建新的 Selector 类
2. 在 `screeners/configs/selector_configs.json` 中添加配置

```python
# screeners/Selector.py
class MyCustomSelector(BBIKDJSelector):
    def _passes_filters(self, hist):
        # 自定义过滤逻辑
        if not super()._passes_filters(hist):
            return False
        # 添加你的条件
        return True
```

## 🗺️ Roadmap

- [x] 多策略选股（6种战法）
- [x] AI 深度分析
- [x] 多渠道推送
- [ ] Web 管理界面
- [ ] 历史回测功能
- [ ] 港股/美股支持
- [ ] 自选股动态管理 API
- [ ] 策略参数优化

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

详见 [贡献指南](CONTRIBUTING.md)

## 📄 License

[MIT License](LICENSE) © 2026 ZhuLinsen

## ⚠️ 免责声明

本项目仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。作者不对使用本项目产生的任何损失负责。

---

**如果觉得有用，请给个 ⭐ Star 支持一下！**
