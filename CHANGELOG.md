# Changelog

所有重要更改都會記錄在此文件中。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 計劃中
- Web 管理界面

## [1.6.0] - 2026-01-19

### 新增
- 🖥️ WebUI 管理界面及 API 支持（PR #72）
  - 全新 Web 架構：分層設計（Server/Router/Handler/Service）
  - 核心 API：支持 `/analysis` (觸發分析), `/tasks` (查詢進度), `/health` (健康檢查)
  - 交互界面：支持頁面直接輸入代碼並觸發分析，實時展示進度
  - 運行模式：新增 `--webui-only` 模式，僅啟動 Web 服務
  - 解決了 [#70](https://github.com/ZhuLinsen/daily_stock_analysis/issues/70) 的核心需求（提供觸發分析的接口）
- ⚙️ GitHub Actions 配置靈活性增強（[#79](https://github.com/ZhuLinsen/daily_stock_analysis/issues/79)）
  - 支持從 Repository Variables 讀取非敏感配置（如 STOCK_LIST, GEMINI_MODEL）
  - 保持對 Secrets 的向下兼容

### 修復
- 🐛 修復企業微信/飛書報告截斷問題（[#73](https://github.com/ZhuLinsen/daily_stock_analysis/issues/73)）
  - 移除 notification.py 中不必要的長度硬截斷邏輯
  - 依賴底層自動分片機制處理長消息
- 🐛 修復 GitHub Workflow 環境變量缺失（[#80](https://github.com/ZhuLinsen/daily_stock_analysis/issues/80)）
  - 修復 `CUSTOM_WEBHOOK_BEARER_TOKEN` 未正確傳遞到 Runner 的問題

## [1.5.0] - 2026-01-17

### 新增
- 📲 單股推送模式（[#55](https://github.com/ZhuLinsen/daily_stock_analysis/issues/55)）
  - 每分析完一隻股票立即推送，不用等全部分析完
  - 命令行參數：`--single-notify`
  - 環境變量：`SINGLE_STOCK_NOTIFY=true`
- 🔐 自定義 Webhook Bearer Token 認證（[#51](https://github.com/ZhuLinsen/daily_stock_analysis/issues/51)）
  - 支持需要 Token 認證的 Webhook 端點
  - 環境變量：`CUSTOM_WEBHOOK_BEARER_TOKEN`

## [1.4.0] - 2026-01-17

### 新增
- 📱 Pushover 推送支持（PR #26）
  - 支持 iOS/Android 跨平臺推送
  - 通過 `PUSHOVER_USER_KEY` 和 `PUSHOVER_API_TOKEN` 配置
- 🔍 博查搜索 API 集成（PR #27）
  - 中文搜索優化，支持 AI 摘要
  - 通過 `BOCHA_API_KEYS` 配置
- 📊 Efinance 數據源支持（PR #59）
  - 新增 efinance 作為數據源選項
- 🇭🇰 港股支持（PR #17）
  - 支持 5 位代碼或 HK 前綴（如 `hk00700`、`hk1810`）

### 修復
- 🔧 飛書 Markdown 渲染優化（PR #34）
  - 使用交互卡片和格式化器修復渲染問題
- ♻️ 股票列表熱重載（PR #42 修復）
  - 分析前自動重載 `STOCK_LIST` 配置
- 🐛 釘釘 Webhook 20KB 限制處理
  - 長消息自動分塊發送，避免被截斷
- 🔄 AkShare API 重試機制增強
  - 添加失敗緩存，避免重複請求失敗接口

### 改進
- 📝 README 精簡優化
  - 高級配置移至 `docs/full-guide.md`


## [1.3.0] - 2026-01-12

### 新增
- 🔗 自定義 Webhook 支持
  - 支持任意 POST JSON 的 Webhook 端點
  - 自動識別釘釘、Discord、Slack、Bark 等常見服務格式
  - 支持配置多個 Webhook（逗號分隔）
  - 通過 `CUSTOM_WEBHOOK_URLS` 環境變量配置

### 修復
- 📝 企業微信長消息分批發送
  - 解決自選股過多時內容超過 4096 字符限制導致推送失敗的問題
  - 智能按股票分析塊分割，每批添加分頁標記（如 1/3, 2/3）
  - 批次間隔 1 秒，避免觸發頻率限制

## [1.2.0] - 2026-01-11

### 新增
- 📢 多渠道推送支持
  - 企業微信 Webhook
  - 飛書 Webhook（新增）
  - 郵件 SMTP（新增）
  - 自動識別渠道類型，配置更簡單

### 改進
- 統一使用 `NOTIFICATION_URL` 配置，兼容舊的 `WECHAT_WEBHOOK_URL`
- 郵件支持 Markdown 轉 HTML 渲染

## [1.1.0] - 2026-01-11

### 新增
- 🤖 OpenAI 兼容 API 支持
  - 支持 DeepSeek、通義千問、Moonshot、智譜 GLM 等
  - Gemini 和 OpenAI 格式二選一
  - 自動降級重試機制

## [1.0.0] - 2026-01-10

### 新增
- 🎯 AI 決策儀表盤分析
  - 一句話核心結論
  - 精確買入/止損/目標點位
  - 檢查清單（✅⚠️❌）
  - 分持倉建議（空倉者 vs 持倉者）
- 📊 大盤覆盤功能
  - 主要指數行情
  - 漲跌統計
  - 板塊漲跌榜
  - AI 生成覆盤報告
- 🔍 多數據源支持
  - AkShare（主數據源，免費）
  - Tushare Pro
  - Baostock
  - YFinance
- 📰 新聞搜索服務
  - Tavily API
  - SerpAPI
- 💬 企業微信機器人推送
- ⏰ 定時任務調度
- 🐳 Docker 部署支持
- 🚀 GitHub Actions 零成本部署

### 技術特性
- Gemini AI 模型（gemini-3-flash-preview）
- 429 限流自動重試 + 模型切換
- 請求間延時防封禁
- 多 API Key 負載均衡
- SQLite 本地數據存儲

---

[Unreleased]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ZhuLinsen/daily_stock_analysis/releases/tag/v1.0.0
