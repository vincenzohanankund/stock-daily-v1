# 📖 完整配置與部署指南

本文檔包含台股智能分析系統的完整配置說明，適合需要高級功能或特殊部署方式的用戶。

> 💡 快速上手請參考 [README.md](../README.md)，本文檔為進階配置。

## 📑 目錄

- [GitHub Actions 詳細配置](#github-actions-詳細配置)
- [環境變量完整列表](#環境變量完整列表)
- [Docker 部署](#docker-部署)
- [本地運行詳細配置](#本地運行詳細配置)
- [定時任務配置](#定時任務配置)
- [通知渠道詳細配置](#通知渠道詳細配置)
- [數據源配置](#數據源配置)
- [高級功能](#高級功能)
- [本地 WebUI 管理界面](#本地-webui-管理界面)

---

## GitHub Actions 詳細配置

### 1. Fork 本倉庫

點擊右上角 `Fork` 按鈕

### 2. 配置 Secrets

進入你 Fork 的倉庫 → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

<div align="center">
  <img src="../sources/secret_config.png" alt="GitHub Secrets 配置示意圖" width="600">
</div>

#### AI 模型配置（二選一）

| Secret 名稱 | 說明 | 必填 |
|------------|------|:----:|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) 獲取免費 Key | ✅* |
| `OPENAI_API_KEY` | OpenAI 兼容 API Key（支持 DeepSeek、通義千問等） | 可選 |
| `OPENAI_BASE_URL` | OpenAI 兼容 API 地址（如 `https://api.deepseek.com/v1`） | 可選 |
| `OPENAI_MODEL` | 模型名稱（如 `deepseek-chat`） | 可選 |

> *注：`GEMINI_API_KEY` 和 `OPENAI_API_KEY` 至少配置一個

#### 通知渠道配置（可同時配置多個，全部推送）

| Secret 名稱 | 說明 | 必填 |
|------------|------|:----:|
| `WECHAT_WEBHOOK_URL` | 企業微信 Webhook URL | 可選 |
| `FEISHU_WEBHOOK_URL` | 飛書 Webhook URL | 可選 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（@BotFather 獲取） | 可選 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 可選 |
| `EMAIL_SENDER` | 發件人郵箱（如 `xxx@qq.com`） | 可選 |
| `EMAIL_PASSWORD` | 郵箱授權碼（非登錄密碼） | 可選 |
| `EMAIL_RECEIVERS` | 收件人郵箱（多個用逗號分隔，留空則發給自己） | 可選 |
| `CUSTOM_WEBHOOK_URLS` | 自定義 Webhook（支持釘釘等，多個用逗號分隔） | 可選 |
| `CUSTOM_WEBHOOK_BEARER_TOKEN` | 自定義 Webhook 的 Bearer Token（用於需要認證的 Webhook） | 可選 |
| `SINGLE_STOCK_NOTIFY` | 單股推送模式：設為 `true` 則每分析完一隻股票立即推送 | 可選 |

> *注：至少配置一個渠道，配置多個則同時推送

#### 其他配置

| Secret 名稱 | 說明 | 必填 |
|------------|------|:----:|
| `STOCK_LIST` | 自選股代碼，如 `600519,300750,002594` | ✅ |
| `TAVILY_API_KEYS` | [Tavily](https://tavily.com/) 搜索 API（新聞搜索） | 推薦 |
| `BOCHA_API_KEYS` | [博查搜索](https://open.bocha.cn/) Web Search API（中文搜索優化，支持AI摘要，多個key用逗號分隔） | 可選 |
| `SERPAPI_API_KEYS` | [SerpAPI](https://serpapi.com/) 備用搜索 | 可選 |
| `TUSHARE_TOKEN` | [Tushare Pro](https://tushare.pro/) Token | 可選 |

#### ✅ 最小配置示例

如果你想快速開始，最少需要配置以下項：

1. **AI 模型**：`GEMINI_API_KEY`（推薦）或 `OPENAI_API_KEY`
2. **通知渠道**：至少配置一個，如 `WECHAT_WEBHOOK_URL` 或 `EMAIL_SENDER` + `EMAIL_PASSWORD`
3. **股票列表**：`STOCK_LIST`（必填）
4. **搜索 API**：`TAVILY_API_KEYS`（強烈推薦，用於新聞搜索）

> 💡 配置完以上 4 項即可開始使用！

### 3. 啟用 Actions

1. 進入你 Fork 的倉庫
2. 點擊頂部的 `Actions` 標籤
3. 如果看到提示，點擊 `I understand my workflows, go ahead and enable them`

### 4. 手動測試

1. 進入 `Actions` 標籤
2. 左側選擇 `每日股票分析` workflow
3. 點擊右側的 `Run workflow` 按鈕
4. 選擇運行模式
5. 點擊綠色的 `Run workflow` 確認

### 5. 完成！

默認每個工作日 **18:00（北京時間）** 自動執行。

---

## 環境變量完整列表

### AI 模型配置

| 變量名 | 說明 | 默認值 | 必填 |
|--------|------|--------|:----:|
| `GEMINI_API_KEY` | Google Gemini API Key | - | ✅* |
| `GEMINI_MODEL` | 主模型名稱 | `gemini-3-flash-preview` | 否 |
| `GEMINI_MODEL_FALLBACK` | 備選模型 | `gemini-2.5-flash` | 否 |
| `OPENAI_API_KEY` | OpenAI 兼容 API Key | - | 可選 |
| `OPENAI_BASE_URL` | OpenAI 兼容 API 地址 | - | 可選 |
| `OPENAI_MODEL` | OpenAI 模型名稱 | `gpt-4o` | 可選 |

> *注：`GEMINI_API_KEY` 和 `OPENAI_API_KEY` 至少配置一個

### 通知渠道配置

| 變量名 | 說明 | 必填 |
|--------|------|:----:|
| `WECHAT_WEBHOOK_URL` | 企業微信機器人 Webhook URL | 可選 |
| `FEISHU_WEBHOOK_URL` | 飛書機器人 Webhook URL | 可選 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 可選 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 可選 |
| `EMAIL_SENDER` | 發件人郵箱 | 可選 |
| `EMAIL_PASSWORD` | 郵箱授權碼（非登錄密碼） | 可選 |
| `EMAIL_RECEIVERS` | 收件人郵箱（逗號分隔，留空發給自己） | 可選 |
| `CUSTOM_WEBHOOK_URLS` | 自定義 Webhook（逗號分隔） | 可選 |
| `CUSTOM_WEBHOOK_BEARER_TOKEN` | 自定義 Webhook Bearer Token | 可選 |
| `PUSHOVER_USER_KEY` | Pushover 用戶 Key | 可選 |
| `PUSHOVER_API_TOKEN` | Pushover API Token | 可選 |

#### 飛書雲文檔配置（可選，解決消息截斷問題）

| 變量名 | 說明 | 必填 |
|--------|------|:----:|
| `FEISHU_APP_ID` | 飛書應用 ID | 可選 |
| `FEISHU_APP_SECRET` | 飛書應用 Secret | 可選 |
| `FEISHU_FOLDER_TOKEN` | 飛書雲盤文件夾 Token | 可選 |

> 飛書雲文檔配置步驟：
> 1. 在 [飛書開發者後臺](https://open.feishu.cn/app) 創建應用
> 2. 配置 GitHub Secrets
> 3. 創建群組並添加應用機器人
> 4. 在雲盤文件夾中添加群組為協作者（可管理權限）

### 搜索服務配置

| 變量名 | 說明 | 必填 |
|--------|------|:----:|
| `TAVILY_API_KEYS` | Tavily 搜索 API Key（推薦） | 推薦 |
| `BOCHA_API_KEYS` | 博查搜索 API Key（中文優化） | 可選 |
| `SERPAPI_API_KEYS` | SerpAPI 備用搜索 | 可選 |

### 數據源配置

| 變量名 | 說明 | 必填 |
|--------|------|:----:|
| `TUSHARE_TOKEN` | Tushare Pro Token | 可選 |

### 其他配置

| 變量名 | 說明 | 默認值 |
|--------|------|--------|
| `STOCK_LIST` | 自選股代碼（逗號分隔） | - |
| `MAX_WORKERS` | 併發線程數 | `3` |
| `MARKET_REVIEW_ENABLED` | 啟用大盤覆盤 | `true` |
| `SCHEDULE_ENABLED` | 啟用定時任務 | `false` |
| `SCHEDULE_TIME` | 定時執行時間 | `18:00` |
| `LOG_DIR` | 日誌目錄 | `./logs` |

---

## Docker 部署

### 快速啟動

```bash
# 1. 克隆倉庫
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git
cd daily_stock_analysis

# 2. 配置環境變量
cp .env.example .env
vim .env  # 填入 API Key 和配置

# 3. 啟動容器
docker-compose up -d webui      # WebUI 模式（推薦）
docker-compose up -d analyzer   # 定時任務模式
docker-compose up -d            # 同時啟動兩種模式

# 4. 訪問 WebUI
# http://localhost:8000

# 5. 查看日誌
docker-compose logs -f webui
```

### 運行模式說明

| 命令 | 說明 | 端口 |
|------|------|------|
| `docker-compose up -d webui` | WebUI 模式，手動觸發分析 | 8000 |
| `docker-compose up -d analyzer` | 定時任務模式，每日自動執行 | - |
| `docker-compose up -d` | 同時啟動兩種模式 | 8000 |

### Docker Compose 配置

`docker-compose.yml` 使用 YAML 錨點複用配置：

```yaml
version: '3.8'

x-common: &common
  build: .
  restart: unless-stopped
  env_file:
    - .env
  environment:
    - TZ=Asia/Shanghai
  volumes:
    - ./data:/app/data
    - ./logs:/app/logs
    - ./reports:/app/reports
    - ./.env:/app/.env

services:
  # 定時任務模式
  analyzer:
    <<: *common
    container_name: stock-analyzer

  # WebUI 模式
  webui:
    <<: *common
    container_name: stock-webui
    command: ["python", "main.py", "--webui-only"]
    ports:
      - "8000:8000"
```

### 常用命令

```bash
# 查看運行狀態
docker-compose ps

# 查看日誌
docker-compose logs -f webui

# 停止服務
docker-compose down

# 重建鏡像（代碼更新後）
docker-compose build --no-cache
docker-compose up -d webui
```

### 手動構建鏡像

```bash
docker build -t stock-analysis .
docker run -d --env-file .env -p 8000:8000 -v ./data:/app/data stock-analysis python main.py --webui-only
```

---

## 本地運行詳細配置

### 安裝依賴

```bash
# Python 3.10+ 推薦
pip install -r requirements.txt

# 或使用 conda
conda create -n stock python=3.10
conda activate stock
pip install -r requirements.txt
```

### 命令行參數

```bash
python main.py                        # 完整分析（個股 + 大盤覆盤）
python main.py --market-review        # 僅大盤覆盤
python main.py --no-market-review     # 僅個股分析
python main.py --stocks 600519,300750 # 指定股票
python main.py --dry-run              # 僅獲取數據，不 AI 分析
python main.py --no-notify            # 不發送推送
python main.py --schedule             # 定時任務模式
python main.py --debug                # 調試模式（詳細日誌）
python main.py --workers 5            # 指定併發數
```

---

## 定時任務配置

### GitHub Actions 定時

編輯 `.github/workflows/daily_analysis.yml`:

```yaml
schedule:
  # UTC 時間，北京時間 = UTC + 8
  - cron: '0 10 * * 1-5'   # 週一到週五 18:00（北京時間）
```

常用時間對照：

| 北京時間 | UTC cron 表達式 |
|---------|----------------|
| 09:30 | `'30 1 * * 1-5'` |
| 12:00 | `'0 4 * * 1-5'` |
| 15:00 | `'0 7 * * 1-5'` |
| 18:00 | `'0 10 * * 1-5'` |
| 21:00 | `'0 13 * * 1-5'` |

### 本地定時任務

```bash
# 啟動定時模式（默認 18:00 執行）
python main.py --schedule

# 或使用 crontab
crontab -e
# 添加：0 18 * * 1-5 cd /path/to/project && python main.py
```

---

## 通知渠道詳細配置

### 企業微信

1. 在企業微信群聊中添加"群機器人"
2. 複製 Webhook URL
3. 設置 `WECHAT_WEBHOOK_URL`

### 飛書

1. 在飛書群聊中添加"自定義機器人"
2. 複製 Webhook URL
3. 設置 `FEISHU_WEBHOOK_URL`

### Telegram

1. 與 @BotFather 對話創建 Bot
2. 獲取 Bot Token
3. 獲取 Chat ID（可通過 @userinfobot）
4. 設置 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID`

### 郵件

1. 開啟郵箱的 SMTP 服務
2. 獲取授權碼（非登錄密碼）
3. 設置 `EMAIL_SENDER`、`EMAIL_PASSWORD`、`EMAIL_RECEIVERS`

支持的郵箱：
- QQ 郵箱：smtp.qq.com:465
- 163 郵箱：smtp.163.com:465
- Gmail：smtp.gmail.com:587

### 自定義 Webhook

支持任意 POST JSON 的 Webhook，包括：
- 釘釘機器人
- Discord Webhook
- Slack Webhook
- Bark（iOS 推送）
- 自建服務

設置 `CUSTOM_WEBHOOK_URLS`，多個用逗號分隔。

### Pushover（iOS/Android 推送）

[Pushover](https://pushover.net/) 是一個跨平臺的推送服務，支持 iOS 和 Android。

1. 註冊 Pushover 賬號並下載 App
2. 在 [Pushover Dashboard](https://pushover.net/) 獲取 User Key
3. 創建 Application 獲取 API Token
4. 配置環境變量：

```bash
PUSHOVER_USER_KEY=your_user_key
PUSHOVER_API_TOKEN=your_api_token
```

特點：
- 支持 iOS/Android 雙平臺
- 支持通知優先級和聲音設置
- 免費額度足夠個人使用（每月 10,000 條）
- 消息可保留 7 天

---

## 數據源配置

系統默認使用 AkShare（免費），也支持其他數據源：

### AkShare（默認）
- 免費，無需配置
- 數據來源：東方財富爬蟲

### Tushare Pro
- 需要註冊獲取 Token
- 更穩定，數據更全
- 設置 `TUSHARE_TOKEN`

### Baostock
- 免費，無需配置
- 作為備用數據源

### YFinance
- 免費，無需配置
- 支持美股/港股數據

---

## 高級功能

### 港股支持

使用 `hk` 前綴指定港股代碼：

```bash
STOCK_LIST=600519,hk00700,hk01810
```

### 多模型切換

配置多個模型，系統自動切換：

```bash
# Gemini（主力）
GEMINI_API_KEY=xxx
GEMINI_MODEL=gemini-3-flash-preview

# OpenAI 兼容（備選）
OPENAI_API_KEY=xxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

### 調試模式

```bash
python main.py --debug
```

日誌文件位置：
- 常規日誌：`logs/stock_analysis_YYYYMMDD.log`
- 調試日誌：`logs/stock_analysis_debug_YYYYMMDD.log`

---

## 本地 WebUI 管理界面

WebUI 提供配置管理和快速分析功能，支持頁面觸發單隻股票分析。

### 啟動方式

| 命令 | 說明 |
|------|------|
| `python main.py --webui` | 啟動 WebUI + 執行一次完整分析 |
| `python main.py --webui-only` | 僅啟動 WebUI，手動觸發分析 |

**永久啟用**：在 `.env` 中設置：
```env
WEBUI_ENABLED=true
```

### 功能特性

- 📝 **配置管理** - 查看/修改 `.env` 裡的自選股列表
- 🚀 **快速分析** - 頁面輸入股票代碼，一鍵觸發分析
- 📊 **實時進度** - 分析任務狀態實時更新，支持多任務並行
- 🔗 **API 接口** - 支持程序化調用

### API 接口

| 接口 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 配置管理頁面 |
| `/health` | GET | 健康檢查 |
| `/analysis?code=xxx` | GET | 觸發單隻股票異步分析 |
| `/tasks` | GET | 查詢所有任務狀態 |
| `/task?id=xxx` | GET | 查詢單個任務狀態 |

**調用示例**：
```bash
# 健康檢查
curl http://127.0.0.1:8000/health

# 觸發分析（台股）
curl "http://127.0.0.1:8000/analysis?code=2330.TW"

# 觸發分析（港股）
curl "http://127.0.0.1:8000/analysis?code=0700.HK"

# 觸發分析（美股）
curl "http://127.0.0.1:8000/analysis?code=AAPL"

# 查詢任務狀態
curl "http://127.0.0.1:8000/task?id=<task_id>"
```

### 自定義配置

修改默認端口或允許局域網訪問：

```env
WEBUI_HOST=0.0.0.0    # 默認 127.0.0.1
WEBUI_PORT=8888       # 默認 8000
```

### 支持的股票代碼格式

| 類型 | 格式 | 示例 |
|------|------|------|
| 台股 | 4位數字 + .TW | `2330.TW`、`2317.TW`、`2454.TW` |
| 港股 | 4位數字 + .HK | `0700.HK`、`9988.HK` |
| A股 | 6位數字 + .SS/.SZ | `600519.SS`、`000001.SZ` |
| 美股 | 股票代號 | `AAPL`、`TSLA`、`GOOGL` |

### 注意事項

- 瀏覽器訪問：`http://127.0.0.1:8000`（或您配置的端口）
- 分析完成後自動推送通知到配置的渠道
- 此功能在 GitHub Actions 環境中會自動禁用

---

## 常見問題

### Q: 推送消息被截斷？
A: 企業微信/飛書有消息長度限制，系統已自動分段發送。如需完整內容，可配置飛書雲文檔功能。

### Q: 數據獲取失敗？
A: AkShare 使用爬蟲機制，可能被臨時限流。系統已配置重試機制，一般等待幾分鐘後重試即可。

### Q: 如何添加自選股？
A: 修改 `STOCK_LIST` 環境變量，多個代碼用逗號分隔。

### Q: GitHub Actions 沒有執行？
A: 檢查是否啟用了 Actions，以及 cron 表達式是否正確（注意是 UTC 時間）。

---

更多問題請 [提交 Issue](https://github.com/ZhuLinsen/daily_stock_analysis/issues)
