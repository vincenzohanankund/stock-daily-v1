# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AI-powered Stock Analysis System** (A股/港股/美股智能分析系统) that automatically analyzes selected stocks and pushes decision dashboards to messaging platforms. It supports A-shares, Hong Kong stocks, and US stocks.

## Common Commands

### Running the Application

```bash
# Normal run (full analysis)
python main.py

# Debug mode
python main.py --debug

# Only fetch data, no AI analysis
python main.py --dry-run

# Analyze specific stocks
python main.py --stocks 600519,AAPL,TSLA

# Single stock push mode (push after each stock)
python main.py --single-notify

# Skip notifications
python main.py --no-notify

# WebUI mode
python main.py --webui
python main.py --webui-only  # WebUI only, manual trigger

# Market review only
python main.py --market-review

# Scheduled mode
python main.py --schedule
```

### Testing

```bash
# Quick test (single stock)
./test.sh quick

# Market review only
./test.sh market

# A-stock analysis
./test.sh a-stock

# Hong Kong stock analysis
./test.sh hk-stock

# US stock analysis
./test.sh us-stock

# Mixed markets
./test.sh mixed

# Syntax check
./test.sh syntax

# Static analysis (flake8)
./test.sh flake8

# All tests
./test.sh all
```

### Code Quality

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Static analysis with flake8
flake8 . --max-line-length=120

# Security scan with bandit
bandit -r . -f json
```

## High-Level Architecture

### Core Design Pattern: Pipeline with Strategy Pattern

The system uses a **pipeline architecture** where `StockAnalysisPipeline` (in `src/core/pipeline.py`) orchestrates the entire analysis flow:

1. **Data Fetching** - `DataFetcherManager` (Strategy Pattern) manages multiple data sources with automatic failover
2. **Technical Analysis** - `StockTrendAnalyzer` calculates MA indicators, volume analysis, and trend signals
3. **News Search** - `SearchService` performs multi-dimensional intelligence gathering
4. **AI Analysis** - `GeminiAnalyzer` generates investment decisions using Gemini/OpenAI APIs
5. **Notification** - `NotificationService` delivers results via multiple channels

### Key Components

#### `src/core/pipeline.py` - Main Orchestrator

The heart of the system. Key methods:
- `fetch_and_save_stock_data()` - Fetches data with breakpoint resume support
- `analyze_stock()` - Complete analysis flow with realtime quotes, chip distribution, trend analysis, and news search
- `run()` - Concurrent analysis with ThreadPoolExecutor (max_workers=3 to avoid bans)
- `_send_notifications()` - Generates dashboard reports and pushes to all configured channels

#### `data_provider/` - Multi-Source Data Fetching (Strategy Pattern)

Implements automatic failover with priority-based source selection:

**Priority with TUSHARE_TOKEN:**
1. TushareFetcher (Priority 0) - highest when token configured
2. EfinanceFetcher (Priority 0)
3. AkshareFetcher (Priority 1)
4. BaostockFetcher (Priority 3)
5. YfinanceFetcher (Priority 4)

**Priority without TUSHARE_TOKEN:**
1. EfinanceFetcher (Priority 0)
2. AkshareFetcher (Priority 1)
3. TushareFetcher (Priority 2)
4. BaostockFetcher (Priority 3)
5. YfinanceFetcher (Priority 4)

**Base Classes:**
- `BaseFetcher` (in `base.py`) - Abstract base defining `get_daily_data()`, `get_realtime_quote()`, `get_chip_distribution()`
- `DataFetcherManager` - Strategy manager that auto-switches on failure

**Important:** Realtime quotes have separate priority config (`REALTIME_SOURCE_PRIORITY`):
- `akshare_sina`, `tencent` - Lightweight per-stock queries (recommended for front)
- `efinance`, `akshare_em` - Bulk market data (use with prefetch for 5+ stocks)

#### `src/config.py` - Singleton Configuration Management

Uses dataclass with environment variable loading:
- All secrets from `.env` or GitHub Actions Secrets
- Smart proxy handling: auto-sets `NO_PROXY` for Chinese financial data sources
- Hot reload: `refresh_stock_list()` re-reads STOCK_LIST at runtime
- Multi-key support: search APIs support comma-separated load balancing

#### `bot/` - Command-Based Bot System

**Pattern:** Command Pattern with unified interface

**Base Class:** `bot/commands/base.py` - `BotCommand` abstract class
- Properties: `name`, `aliases`, `description`, `usage`, `admin_only`
- Method: `execute(message, args) -> BotResponse`

**Platform Implementations:**
- `dingding.py` - DingTalk bot with Stream mode
- `feishu_stream.py` - Feishu bot with Stream mode (no public IP needed)
- `discord.py` - Discord bot with slash commands

**Available Commands:**
- `analyze` - Analyze single stock
- `batch` - Batch analyze stock list
- `market` - Market review
- `status` - System status
- `config` - View/manage configuration

#### `src/` - Core Business Logic

- `analyzer.py` - AI analysis engine (Gemini/OpenAI), implements trading philosophy (BIAS > 5% = danger, MA alignment checks)
- `notification.py` - Multi-channel notification (WeChat, Feishu, Telegram, Email, PushPlus, Custom Webhook, Pushover, Discord)
- `search_service.py` - News search with Tavily/SerpAPI/Bocha, multi-dimensional intelligence gathering
- `stock_analyzer.py` - Technical analysis helper (MA5/MA10/MA20, volume, bias calculation)
- `market_analyzer.py` - Market overview analysis (indices, sectors, northbound capital)
- `storage.py` - SQLite database with caching and breakpoint resume

### Data Flow

```
Config (env) → DataFetcherManager (multi-source with failover)
            → StockTrendAnalyzer (MA signals, bias checks)
            → SearchService (multi-dimensional news)
            → GeminiAnalyzer (AI decision with trading rules)
            → NotificationService (multi-channel push)
```

### Trading Philosophy (Built into System)

The system encodes specific trading strategies in `src/analyzer.py`:
- **No chasing highs**: BIAS > 5% marked as dangerous
- **Trend trading**: MA5 > MA10 > MA20 multi-head arrangement
- **Precise entry/exit**: Buy price, stop-loss, target price
- **Checklist style**: Each condition marked with ✅⚠️❌

### Multi-Market Support

- **A-shares**: Shanghai (600xxx, 601xxx) and Shenzhen (000xxx, 002xxx, 300xxx)
- **Hong Kong**: 5-digit codes (e.g., 00700 for Tencent)
- **US**: Standard symbols (AAPL, TSLA) with YFinance conversion

## Important Conventions

### Code Style
- **Python 3.10+** required
- **Black** formatter with 120 character line length
- **isort** import sorting with black profile
- **flake8** static analysis (ignore: E501, W503, E203, E402)
- **docstrings** required for public classes/functions
- Chinese comments allowed

### Error Handling & Resilience

- **Exponential backoff retry** - Built into all API calls
- **Graceful degradation** - APIs fail without breaking the system
- **Per-stock failure isolation** - Single stock failure doesn't stop entire process
- **Daily log rotation** - Logs organized by date
- **Circuit breaker pattern** - For unstable APIs (chip distribution)

### Anti-Ban Strategy

- **Low concurrency**: `max_workers=3` by default
- **Random sleep jitter**: Between API calls
- **Request delays**: Configurable via environment
- **Rate limiting**: Per-source rate limits (Tushare: 80/min)

### Configuration Management

All configuration via environment variables (`.env` file or GitHub Actions Secrets):
- At least one AI model: `GEMINI_API_KEY` or `OPENAI_API_KEY`
- At least one notification channel (can configure multiple)
- `STOCK_LIST` - comma-separated stock codes
- Search APIs optional but recommended

### Deployment Options

1. **GitHub Actions** - Free serverless execution (recommended)
2. **Local Docker** - Containerized deployment
3. **Local Python** - Direct execution
4. **WebUI** - Local management interface at http://127.0.0.1:8000

## Testing Strategy

- `test.sh` with multiple scenarios (quick, market, individual markets, mixed)
- Code quality checks (syntax, flake8)
- Integration tests with actual API calls
- Fallback mechanism validation

## Security Considerations

- API keys stored in environment variables/secrets
- No hardcoded credentials
- Input validation for stock codes
- Rate limiting and retry mechanisms
- Secure email configuration with OAuth where possible
