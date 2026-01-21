# 📈 A股智能分析系统使用指南

## 项目简介

A股智能分析系统是一个基于AI大模型的股票分析工具，能够自动分析自选股并生成决策仪表盘，支持多种通知渠道推送。

### 核心功能
- **AI决策仪表盘** - 一句话核心结论 + 精确买卖点位 + 检查清单
- **多维度分析** - 技术面 + 筹码分布 + 舆情情报 + 实时行情
- **大盘复盘** - 每日市场概览、板块涨跌、北向资金
- **多渠道推送** - 企业微信、飞书、Telegram、邮件等
- **零成本部署** - GitHub Actions免费运行，无需服务器

## 🚀 快速开始

### 方式一：GitHub Actions（推荐，零成本）

#### 1. Fork仓库
1. 访问 https://github.com/ZhuLinsen/daily_stock_analysis
2. 点击右上角 `Fork` 按钮
3. 顺便点个⭐支持一下

#### 2. 配置Secrets
进入你Fork的仓库 → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

**必填配置（最小配置）：**

| Secret名称 | 说明 | 获取方式 |
|-----------|------|---------|
| `GEMINI_API_KEY` | Google AI Studio免费Key | [点击获取](https://aistudio.google.com/) |
| `STOCK_LIST` | 自选股代码 | 如：`600519,300750,002594` |
| `WECHAT_WEBHOOK_URL` | 企业微信推送 | 企业微信群→设置→群机器人→添加 |
| `TAVILY_API_KEYS` | 新闻搜索API | [点击获取](https://tavily.com/) |

**可选配置（增强功能）：**

| Secret名称 | 说明 | 用途 |
|-----------|------|------|
| `FEISHU_WEBHOOK_URL` | 飞书机器人 | 飞书群推送 |
| `TELEGRAM_BOT_TOKEN` | Telegram机器人 | Telegram推送 |
| `TELEGRAM_CHAT_ID` | Telegram聊天ID | 配合上面使用 |
| `EMAIL_SENDER` | 发件邮箱 | 邮件推送 |
| `EMAIL_PASSWORD` | 邮箱授权码 | 邮件推送 |
| `TUSHARE_TOKEN` | Tushare Pro | 增强数据源 |

#### 3. 启用Actions
1. 进入 `Actions` 标签
2. 点击 `I understand my workflows, go ahead and enable them`

#### 4. 手动测试
1. `Actions` → `每日股票分析` → `Run workflow`
2. 选择模式 → `Run workflow`

#### 5. 完成！
默认每个工作日18:00（北京时间）自动执行

### 方式二：本地运行

#### 1. 环境准备
```bash
# 克隆仓库
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git
cd daily_stock_analysis

# 安装Python依赖
pip install -r requirements.txt
```

#### 2. 配置环境变量
```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
vim .env  # 或使用其他编辑器
```

**必填配置：**
```bash
# 自选股列表
STOCK_LIST=600519,300750,002594

# AI模型（二选一）
GEMINI_API_KEY=your_gemini_key_here
# 或者
OPENAI_API_KEY=your_openai_key_here
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 通知渠道（至少配置一个）
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
# 或者
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
# 或者
EMAIL_SENDER=your_email@qq.com
EMAIL_PASSWORD=your_email_auth_code

# 搜索API（推荐）
TAVILY_API_KEYS=your_tavily_key_here
```

#### 3. 运行程序
```bash
# 正常运行（完整分析+推送）
python main.py

# 调试模式
python main.py --debug

# 仅获取数据，不分析
python main.py --dry-run

# 指定特定股票
python main.py --stocks 600519,000001

# 不发送通知
python main.py --no-notify

# 单股推送模式（每分析完一只立即推送）
python main.py --single-notify

# 启动WebUI管理界面
python main.py --webui

# 仅启动WebUI（不自动分析）
python main.py --webui-only

# 定时任务模式
python main.py --schedule

# 仅大盘复盘
python main.py --market-review
```

### 方式三：Docker部署

#### 1. 快速启动
```bash
# 克隆仓库
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git
cd daily_stock_analysis

# 配置环境变量
cp .env.example .env
vim .env  # 填入配置

# 启动WebUI模式（推荐）
docker-compose up -d webui

# 或启动定时任务模式
docker-compose up -d analyzer

# 访问WebUI
# http://localhost:8000
```

#### 2. 查看日志
```bash
# 查看WebUI日志
docker-compose logs -f webui

# 查看定时任务日志
docker-compose logs -f analyzer
```

## 📱 通知渠道配置详解

### 企业微信机器人
1. 在企业微信群中点击右上角设置
2. 选择"群机器人" → "添加机器人"
3. 复制Webhook地址到 `WECHAT_WEBHOOK_URL`

### 飞书机器人
1. 在飞书群中点击设置
2. 选择"群机器人" → "添加机器人" → "自定义机器人"
3. 复制Webhook地址到 `FEISHU_WEBHOOK_URL`

### Telegram机器人
1. 在Telegram中找到 @BotFather
2. 发送 `/newbot` 创建机器人，获取Bot Token
3. 发送消息给 @userinfobot 获取Chat ID
4. 配置 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID`

### 邮件推送
支持QQ邮箱、163邮箱、Gmail等主流邮箱：
1. 开启邮箱的SMTP服务
2. 获取授权码（不是登录密码）
3. 配置 `EMAIL_SENDER` 和 `EMAIL_PASSWORD`

## 🎯 WebUI管理界面

### 启动WebUI
```bash
# 启动WebUI + 执行一次分析
python main.py --webui

# 仅启动WebUI，手动触发分析
python main.py --webui-only
```

### 功能特性
- **配置管理** - 查看/修改自选股列表
- **快速分析** - 输入股票代码，一键分析
- **实时进度** - 分析任务状态实时更新
- **多任务并行** - 支持同时分析多只股票

### API接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 配置管理页面 |
| `/health` | GET | 健康检查 |
| `/analysis?code=xxx` | GET | 触发单只股票分析 |
| `/tasks` | GET | 查询所有任务状态 |
| `/task?id=xxx` | GET | 查询单个任务状态 |

## 📊 推送效果示例

### 决策仪表盘
```
📊 2026-01-21 决策仪表盘
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

### 大盘复盘
```
🎯 2026-01-21 大盘复盘

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

## ⚙️ 高级配置

### 定时任务配置
```bash
# 启用定时任务
SCHEDULE_ENABLED=true
# 每日执行时间（24小时制）
SCHEDULE_TIME=18:00
# 启用大盘复盘
MARKET_REVIEW_ENABLED=true
```

### 单股推送模式
```bash
# 启用单股推送（每分析完一只立即推送）
SINGLE_STOCK_NOTIFY=true
```

### 并发控制
```bash
# 最大并发线程数（防封禁）
MAX_WORKERS=3
```

### 日志配置
```bash
# 日志目录
LOG_DIR=./logs
# 日志级别
LOG_LEVEL=INFO
# 调试模式
DEBUG=false
```

## 🔧 常见问题

### Q: 如何获取Gemini API Key？
A: 访问 https://aistudio.google.com/ ，登录Google账号即可免费获取。

### Q: 企业微信机器人如何配置？
A: 在企业微信群中添加群机器人，复制Webhook地址即可。

### Q: 支持哪些股票代码格式？
A: 支持沪深两市标准代码：
- 沪市：600xxx, 601xxx, 603xxx
- 深市：000xxx, 002xxx, 300xxx

### Q: 如何添加更多通知渠道？
A: 可以同时配置多个通知渠道，系统会自动推送到所有已配置的渠道。

### Q: GitHub Actions如何修改执行时间？
A: 编辑 `.github/workflows/daily_analysis.yml` 文件中的 `cron` 表达式。

### Q: 如何查看详细日志？
A: 
- 本地运行：查看 `./logs/` 目录
- Docker：使用 `docker-compose logs -f`
- GitHub Actions：在Actions页面查看运行日志

## 📁 项目结构

```
daily_stock_analysis/
├── main.py              # 主程序入口
├── analyzer.py          # AI分析器
├── market_analyzer.py   # 大盘复盘分析
├── search_service.py    # 新闻搜索服务
├── notification.py      # 消息推送
├── scheduler.py         # 定时任务
├── storage.py           # 数据存储
├── config.py            # 配置管理
├── webui.py             # WebUI入口
├── data_provider/       # 数据源适配器
├── web/                 # WebUI模块
├── .github/workflows/   # GitHub Actions
├── Dockerfile           # Docker镜像
└── docker-compose.yml   # Docker编排
```

## ⚠️ 免责声明

本项目仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。作者不对使用本项目产生的任何损失负责。

---

**如果觉得有用，请给个 ⭐ Star 支持一下！**