# A股自选股智能分析系统 - 配置与部署指南

本指南详细说明了如何配置环境变量、设置 Discord 机器人以及在不同环境下部署本系统。

## 1. 环境变量配置 (.env)

在项目根目录下创建 `.env` 文件，参考以下配置：

### 核心配置
- `STOCK_LIST`: 初始自选股列表（逗号分隔，如 `600519,000001`）。后续可通过 Discord 指令动态增删。
- `DATABASE_PATH`: 数据库存储路径（默认 `./data/stock_analysis.db`）。
- `LOG_LEVEL`: 日志级别（`INFO` 或 `DEBUG`）。

### AI 分析配置
- `GEMINI_API_KEY`: Google Gemini API Key（必须）。
- `GEMINI_MODEL`: 使用的主模型（建议 `gemini-1.5-flash`）。
- `OPENAI_API_KEY`: OpenAI 兼容 API Key（备选）。

### 搜索与情报
- `TAVILY_API_KEYS`: Tavily 搜索 API Key（用于获取个股新闻）。
- `SERPAPI_API_KEYS`: SerpAPI Key（备选）。

### 扩展数据源 (可选)
- `TUSHARE_TOKEN`: [Tushare Pro](https://tushare.pro/) Token，用于获取更丰富的行情数据。

### 飞书云文档配置 (可选)
- `FEISHU_APP_ID`: 飞书应用 ID。
- `FEISHU_APP_SECRET`: 飞书应用 Secret。
- `FEISHU_FOLDER_TOKEN`: 飞书云盘文件夹 Token，用于自动生成不截断的飞书文档报告。

### Discord 配置 (新增)
- `DISCORD_BOT_TOKEN`: Discord 机器人令牌（从 [Discord Developer Portal](https://discord.com/developers/applications) 获取）。
- `DISCORD_MAIN_CHANNEL_ID`: 机器人推送日报的默认频道 ID。
- `DISCORD_WEBHOOK_URL`: Discord Webhook 地址（用于 Github Actions 快速通知）。

### 其他通知渠道 (按需)
- `WECHAT_WEBHOOK_URL`: 企业微信机器人 Webhook。
- `FEISHU_WEBHOOK_URL`: 飞书机器人 Webhook。
- `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`: Telegram 机器人配置。
- `EMAIL_SENDER`/`EMAIL_PASSWORD`/`EMAIL_RECEIVERS`: 邮件通知配置。

### 高级系统配置 (可选/隐藏项)
- `MAX_WORKERS`: 并发抓取股票的数量（默认 3，不建议设置过高）。
- `DEBUG`: 设置为 `true` 以开启调试模式。
- `GEMINI_REQUEST_DELAY`: Gemini 请求间隔（默认 2.0s），防止 429 报错。
- `FEISHU_MAX_BYTES`/`WECHAT_MAX_BYTES`: 消息分段阈值，超长报告会自动分批发送。
- `LOG_LEVEL`: 日志级别（DEBUG, INFO, WARNING, ERROR）。

---

## 2. Discord 机器人设置

### 创建 Bot
1. 访问 [Discord Developer Portal](https://discord.com/developers/applications)。
2. 创建新 Application，进入 **Bot** 选项卡。
3. 开启 `MESSAGE CONTENT INTENT` 权限。
4. 获取 `Token` 并填入 `.env` 的 `DISCORD_BOT_TOKEN`。

### 邀请 Bot
1. 进入 **OAuth2 -> URL Generator**。
2. 勾选 `bot` 和 `applications.commands`。
3. 勾选 Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`。
4. 使用生成的链接将机器人邀请到你的服务器。

### 常用指令
- `/watchlist_add <code> [name]`: 添加自选股。
- `/watchlist_list`: 查看当前所有自选股。
- `/analysis <code>`: 立即执行特定股票深度分析。
- `/market`: 获取市场今日实时快照。
- `!sync`: (Prefix 指令) 手动同步所有 Slash Commands 到 Discord 服务器（推荐在机器人首次部署或运行 `/` 指令无效时使用）。

---

## 3. 部署指南

### Zeabur 镜像部署
Zeabur 部署时会自动读取项目中的 `Dockerfile`。

### Zeabur 部署详解

Zeabur 是部署本项目的理想平台，支持从源码部署或从镜像部署。

#### 1. 环境变量 (Variables)
在 Zeabur 服务的 **Variables** 界面添加以下关键变量：
- `MODE`: 设置为 `BOT` (常驻机器人) 或 `SCHEDULE` (定时任务)。
- `GEMINI_API_KEY`: 你的 AI 密钥。
- `DISCORD_BOT_TOKEN`: 机器人令牌。
- `STOCK_LIST`: 初始股票列表。
- `DATABASE_PATH`: **务必设置为** `/app/data/stock_analysis.db` (配合下方的存储挂载)。

#### 2. 持久化存储 (Volumes)
由于本项目使用 SQLite 存储自选股，容器重启会导致数据丢失。请按以下步骤操作：
1. 在服务设置中找到 **Volumes** 或 **Storage**。
2. 添加一个新的挂载卷。
3. **挂载路径 (Mount Path)** 填入: `/app/data`。
4. 这样你的数据库文件就会安全保存在磁盘上，即使更新代码数据也不会丢失。

#### 3. 部署方式选择
- **方式 A (推荐)**: 从镜像部署。填入 `ghcr.io/你的用户名/daily_stock_analysis:latest`。
- **方式 B**: 直接连接 Github 仓库部署。Zeabur 会自动识别 `Dockerfile` 并开始构建。

### Docker 镜像自动发布 (新)
本项目已集成 Docker 自动构建工作流：
- **触发条件**: 每次推送至 `main` 分支或发布新的 Git Tag（通过 `Version Bump`）。
- **镜像托管**: 自动推送至 `ghcr.io/${{ github.repository }}:latest`。
- **Zeabur 使用**: 你可以直接在 Zeabur 中选择 "Deploy from Image"，填入 `ghcr.io/你的用户名/daily_stock_analysis:latest`，这样部署速度极快且不需要在 Zeabur 中消耗编译资源。

> [!TIP]
> 建议在 Zeabur 中部署两个服务：一个 `MODE=BOT` 用于常驻交互，一个 `MODE=SCHEDULE` 用于每日定时推送（或者使用 Github Actions 触发分析）。

### Github Actions 部署
本项目已包含 `.github/workflows/daily_analysis.yml`。
1. 在 Github 项目设置中进入 **Secrets and variables -> Actions**。
2. 将上述所有环境变量添加为 **New repository secret**。
3. Workflow 会在每天北京时间 18:00 自动运行并推送报告。

---

## 4. 自动化版本管理 (Version Bump)
每当合并代码到 `main` 分支时，`Version Bump` 工作流会自动：
1. 更新 `version.txt` 中的版本号。
2. 自动打上 Git Tag（如 `v1.0.1`）。
3. 推送更新到仓库。
