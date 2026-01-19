# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **A/H股智能分析系统** (Chinese Stock Intelligence Analysis System) - a comprehensive stock analysis platform that uses AI to analyze selected stocks and push daily reports to multiple channels. The system is designed for Chinese stock markets (A-shares and Hong Kong stocks) and features a multi-layered architecture with data fetching, AI analysis, and notification capabilities.

**Key Features:**
- AI-powered decision dashboard with precise buy/sell points
- Multi-source data fetching with automatic failover
- Market review and sector analysis
- Multi-channel notifications (WeChat, Feishu, Telegram, Email, custom webhooks)
- Zero-cost deployment via GitHub Actions
- WebUI for configuration management

## Common Development Commands

### Running the Application

```bash
# Normal mode - full analysis (stocks + market review)
python main.py

# Debug mode - detailed logging
python main.py --debug

# Dry run - fetch data only, skip AI analysis
python main.py --dry-run

# Analyze specific stocks
python main.py --stocks 600519,300750

# Market review only
python main.py --market-review

# Skip market review
python main.py --no-market-review

# Disable notifications
python main.py --no-notify

# Single stock notification mode (push after each stock)
python main.py --single-notify

# Schedule mode - daily automatic execution
python main.py --schedule

# Start WebUI + run analysis once
python main.py --webui

# Start WebUI only (manual trigger via API)
python main.py --webui-only
```

### WebUI Management

```bash
# Access WebUI at http://127.0.0.1:8000
# API endpoints:
# GET / - Configuration management page
# GET /health - Health check
# GET /analysis?code=xxx - Trigger single stock analysis
# GET /tasks - Query all task status
# GET /task?id=xxx - Query single task status
```

### Testing and Validation

```bash
# Environment testing (validates config, database, APIs)
python test_env.py
```

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# WebUI mode
docker-compose up -d webui

# Analyzer/scheduler mode
docker-compose up -d analyzer

# View logs
docker-compose logs -f webui

# Stop services
docker-compose down
```

### Code Quality

```bash
# Format code with Black (line length: 120)
black .

# Sort imports with isort
isort .

# Lint with flake8
flake8 .
```

## Architecture Overview

The system follows a **layered architecture** with clear separation of concerns:

### 1. Data Layer (`data_provider/`)

**Pattern:** Strategy Pattern with automatic failover

- **BaseFetcher** (`base.py`): Abstract base class defining the interface
- **DataFetcherManager**: Manages multiple data sources with priority-based failover

**Data Source Priority:**
1. EfinanceFetcher (priority 0) - Highest priority, real-time data
2. AkshareFetcher (priority 1) - Free, no auth required
3. TushareFetcher (priority 2) - Requires token, more stable
4. BaostockFetcher (priority 3) - Free backup source
5. YfinanceFetcher (priority 4) - Supports US/HK stocks

**Key Features:**
- Random delays between requests (anti-blocking)
- Exponential backoff retry mechanism
- Data standardization across all sources
- Built-in technical indicator calculation (MA5/MA10/MA20, volume ratio)

**Standard Columns:** `['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg', 'ma5', 'ma10', 'ma20', 'volume_ratio']`

### 2. Storage Layer (`storage.py`)

**Pattern:** Singleton with SQLAlchemy ORM

**Components:**
- **DatabaseManager**: Singleton database connection manager
- **StockDaily**: ORM model for daily stock data with unique constraint (code + date)
- **Smart Updates**: Checkpoint/resume functionality - skips already fetched data

**Key Methods:**
- `has_today_data(code, date)`: Check if data exists (for resume logic)
- `save_daily_data(df, code)`: Save/Update with UPSERT logic
- `get_analysis_context(code)`: Get context for AI analysis (today + yesterday comparison)

### 3. Business Logic Layer

**Main Pipeline** (`main.py`):
- **StockAnalysisPipeline**: Orchestrates the entire workflow
  - Fetch and save stock data (with resume capability)
  - Analyze stocks with AI (enhanced with real-time quotes, chip distribution, trend analysis)
  - Search news/intelligence
  - Send notifications

**AI Analysis** (`analyzer.py`):
- **GeminiAnalyzer**: Primary AI analyzer using Google Gemini
- **Fallback**: Supports OpenAI-compatible APIs (DeepSeek, Qwen, etc.)
- **System Prompt**: Built-in trading philosophy (trend following, no chasing highs)
- **Retry Logic**: Handles 429 rate limits with exponential backoff
- **Model Switching**: Automatic fallback to secondary model on quota issues

**Trend Analysis** (`stock_analyzer.py`):
- **StockTrendAnalyzer**: Technical trend analysis based on trading philosophy
- Evaluates: MA alignment, bias rate, volume status, buy signals
- Returns structured signal score and risk factors

**Market Analysis** (`market_analyzer.py`):
- **MarketAnalyzer**: Daily market review
- Major indices, sector performance, northbound capital flow

**Search Service** (`search_service.py`):
- **SearchService**: Multi-source news search (Tavily, Bocha, SerpAPI)
- Comprehensive intelligence gathering with multiple search queries

### 4. Configuration Layer (`config.py`)

**Pattern:** Singleton with dataclass

**Configuration Hierarchy:**
1. System environment variables (highest priority)
2. `.env` file
3. Code defaults (lowest priority)

**Key Config Categories:**
- AI models: Gemini (primary), OpenAI-compatible (fallback)
- Search engines: Tavily, Bocha, SerpAPI
- Notifications: WeChat, Feishu, Telegram, Email, Pushover, Custom
- Data sources: Tushare token
- System: max_workers, schedule, debug flags
- WebUI: host, port

**Special Methods:**
- `refresh_stock_list()`: Hot-reload stock list from `.env` (for WebUI changes)
- `validate()`: Returns warnings for missing/invalid config

### 5. Notification Layer (`notification.py`)

**Pattern:** Multi-channel with platform-specific formatting

**Supported Channels:**
- WeChat Work (企业微信)
- Feishu (飞书)
- Telegram
- Email (SMTP)
- Pushover (iOS/Android)
- Custom Webhooks (DingTalk, Discord, Slack, etc.)

**Key Features:**
- **Decision Dashboard Format**: One-sentence conclusion + precise buy/sell points + checklist
- **Auto-detection**: Automatically finds configured channels
- **Message Splitting**: Handles platform message length limits
- **Single Stock Mode**: Push after each stock analysis (configurable)

### 6. Web Layer (`web/`)

**Components:**
- **server.py**: HTTP server
- **router.py**: Request routing
- **handlers.py**: Request handlers
- **services.py**: Business logic
- **templates.py**: HTML templates

**Features:**
- Configuration management (edit stock list via WebUI)
- Manual analysis trigger
- Real-time task status tracking
- API endpoints for programmatic access

## Data Flow

```
User Command/Trigger
    ↓
main.py (parse arguments, setup logging)
    ↓
StockAnalysisPipeline.run()
    ↓
┌─────────────────────────────────────────┐
│ For each stock (threaded, max_workers=3) │
├─────────────────────────────────────────┤
│ 1. fetch_and_save_stock_data()          │
│    → DataFetcherManager.get_daily_data() │
│    → Try each fetcher by priority       │
│    → Save to database (skip if exists)   │
│                                         │
│ 2. analyze_stock()                      │
│    → Get real-time quote (量比/换手率)  │
│    → Get chip distribution               │
│    → Trend analysis (交易理念)          │
│    → Search news/intelligence            │
│    → Get analysis context from DB        │
│    → Call AI with enhanced context       │
│                                         │
│ 3. Single stock notification (optional) │
└─────────────────────────────────────────┘
    ↓
3. Send aggregated notification (decision dashboard)
    ↓
4. Run market review (if enabled)
    ↓
5. Generate Feishu cloud doc (if configured)
```

## AI Analysis Flow

```
Enhanced Context = {
    Technical data (from DB): OHLCV, MA, volume_ratio
    + Real-time quote: price, volume_ratio, turnover_rate, PE, PB
    + Chip distribution: profit_ratio, concentration
    + Trend analysis: trend_status, buy_signal, bias_ma5, risk_factors
    + Stock name: from real-time quote or mapping table
}
    ↓
Gemini/OpenAI API
    ↓
AnalysisResult = {
    sentiment_score (0-100)
    trend_prediction (强烈看多/看多/震荡/看空/强烈看空)
    operation_advice (买入/加仓/持有/减仓/卖出/观望)
    confidence_level (高/中/低)
    dashboard: { core_conclusion, data_perspective, intelligence, battle_plan }
    ... detailed analysis fields
}
```

## Trading Philosophy (Built into System Prompt)

**Core Principles:**
1. **Strict Entry (不追高)**: Never buy when bias from MA5 > 5%
2. **Trend Following**: Only trade stocks with MA5 > MA10 > MA20 alignment
3. **Efficiency Priority**: Focus on stocks with good chip concentration
4. **Buy Point Preference**: Prefer pullback to MA5/MA10 support with shrinking volume

**Risk Detection:**
- Shareholder/management reduction announcements
- Performance forecast losses/declines
- Regulatory penalties/investigations
- Industry policy negatives
- Large unlock volumes

## Important Implementation Notes

### 1. Anti-Blocking Measures

**Data Fetching:**
- Random delays between requests (`akshare_sleep_min: 2.0`, `akshare_sleep_max: 5.0`)
- Low concurrency default (`max_workers: 3`)
- Exponential backoff on failures

**AI API:**
- Request delay (`gemini_request_delay: 2.0`)
- Max retries (`gemini_max_retries: 5`)
- Retry with exponential backoff (`gemini_retry_delay: 5.0`)
- Automatic model switching on quota issues

### 2. Stock Code Format

- **A-shares**: 6 digits (e.g., `600519`, `000001`, `300750`)
- **Hong Kong stocks**: `hk` prefix + 5 digits (e.g., `hk00700`, `hk09988`)

### 3. Environment Variables

**Minimum Required:**
- `GEMINI_API_KEY` or `OPENAI_API_KEY` (at least one)
- `STOCK_LIST` (comma-separated stock codes)
- At least one notification channel

**Optional but Recommended:**
- `TAVILY_API_KEYS` (for news search)
- `TUSHARE_TOKEN` (more stable data source)

### 4. Database Schema

**Table: stock_daily**
- `code` (indexed): Stock code
- `date` (indexed): Trading date
- Unique constraint: (code, date)
- Columns: open, high, low, close, volume, amount, pct_chg, ma5, ma10, ma20, volume_ratio, data_source
- Timestamps: created_at, updated_at

### 5. Logging

**Log Files:**
- `logs/stock_analysis_YYYYMMDD.log`: Regular logs (INFO level, 10MB rotation)
- `logs/stock_analysis_debug_YYYYMMDD.log`: Debug logs (DEBUG level, 50MB rotation)

**Log Format:** `%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s`

### 6. Code Style

**Configuration (pyproject.toml):**
- Black: line-length = 120, target Python 3.10+
- isort: profile = "black", line_length = 120

### 7. GitHub Actions

**Workflow:** `.github/workflows/daily_analysis.yml`
- Default schedule: Weekdays 18:00 Beijing time (UTC 10:00)
- Supports manual trigger with mode selection

**Repository Variables (for non-sensitive config):**
- `STOCK_LIST`, `MAX_WORKERS`, `MARKET_REVIEW_ENABLED`, `SCHEDULE_TIME`, `SINGLE_STOCK_NOTIFY`, etc.

## Module Interaction Examples

### Adding a New Data Source

1. Create a new fetcher class inheriting from `BaseFetcher` in `data_provider/`
2. Implement `_fetch_raw_data()` and `_normalize_data()` methods
3. Set appropriate `priority` and `name` class attributes
4. Add to `DataFetcherManager._init_default_fetchers()`

### Adding a New Notification Channel

1. Add config fields to `Config` dataclass in `config.py`
2. Implement send method in `NotificationService` class in `notification.py`
3. Add to `get_available_channels()` and `send()` method
4. Update `NotificationChannel` enum if needed

### Modifying AI System Prompt

The `SYSTEM_PROMPT` in `GeminiAnalyzer` class (`analyzer.py`) defines the AI's behavior and output format. Any changes to the trading philosophy or output structure should be made here.

## File Structure Summary

```
daily_stock_analysis/
├── main.py                 # Main entry point, orchestrates pipeline
├── analyzer.py             # AI analysis layer (Gemini/OpenAI)
├── market_analyzer.py      # Market review analysis
├── stock_analyzer.py       # Technical trend analysis
├── search_service.py       # News/intelligence search
├── notification.py         # Multi-channel notifications
├── scheduler.py            # Task scheduling
├── storage.py              # Database layer (SQLite + SQLAlchemy)
├── config.py               # Configuration management (singleton)
├── feishu_doc.py           # Feishu document generation
├── webui.py                # WebUI entry point
├── test_env.py             # Environment testing utilities
├── data_provider/          # Data source adapters
│   ├── base.py             # Abstract base class + manager
│   ├── akshare_fetcher.py
│   ├── tushare_fetcher.py
│   ├── baostock_fetcher.py
│   ├── efinance_fetcher.py
│   └── yfinance_fetcher.py
├── web/                    # WebUI components
│   ├── server.py
│   ├── router.py
│   ├── handlers.py
│   ├── services.py
│   └── templates.py
├── .github/workflows/      # CI/CD pipelines
├── docs/                   # Documentation
├── requirements.txt        # Dependencies
└── pyproject.toml         # Black/isort config
```
