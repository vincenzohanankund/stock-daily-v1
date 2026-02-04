# 🚀 启动方式
## 方式1: 直接运行
python server.py
## 方式2: 使用 uvicorn（推荐开发时使用）
uvicorn server:app --reload --host 0.0.0.0 --port 8000
服务启动后：
- API 文档: http://localhost:8000/docs (Swagger UI)
- 根路由: http://localhost:8000/
- 健康检查: http://localhost:8000/api/health

All files have been created successfully. Let me provide a summary of everything that was created:
Summary of Created Files
I have successfully created the complete backend architecture with the following structure:
1. api/ Directory Structure (16 files)
```
api/
├── __init__.py                     # API 模块初始化
├── deps.py                         # 依赖注入（数据库 Session、Config）
├── v1/
│   ├── __init__.py                 # v1 模块导出
│   ├── router.py                   # v1 路由聚合
│   ├── endpoints/
│   │   ├── __init__.py
│   │   ├── health.py               # GET /api/v1/health
│   │   ├── analysis.py             # POST /api/v1/analysis/analyze
│   │   ├── history.py              # GET /api/v1/history, GET /api/v1/history/{query_id}
│   │   └── stocks.py               # GET /api/v1/stocks/{code}/quote
│   └── schemas/
│       ├── __init__.py             # 导出所有 Pydantic 模型
│       ├── common.py               # HealthResponse, ErrorResponse, SuccessResponse
│       ├── analysis.py             # AnalyzeRequest, AnalysisResultResponse, TaskAccepted, TaskStatus
│       ├── history.py              # HistoryItem, HistoryListResponse, AnalysisReport
│       └── stocks.py               # StockQuote, StockHistoryResponse, KLineData
└── middlewares/
    ├── __init__.py
    └── error_handler.py            # 全局异常处理中间件
2. src/services/ Directory (4 files)
src/services/
├── __init__.py
├── analysis_service.py             # 分析服务，调用 pipeline 执行分析
├── history_service.py              # 历史查询服务
└── stock_service.py                # 股票数据服务
3. src/repositories/ Directory (3 files)
src/repositories/
├── __init__.py
├── analysis_repo.py                # 分析历史数据访问层
└── stock_repo.py                   # 股票数据访问层
```
4. Updated server.py
- 导入了 api.v1.api_v1_router
- 使用 app.include_router(api_v1_router) 注册 v1 路由
- 添加了全局异常处理器
关键特性
1. 遵循 API Spec: 所有接口严格按照 docs/architecture/api_spec.json 实现
2. 字段名使用 snake_case: 如 stock_code, report_type, sentiment_score
3. 完整的类型注解: 所有公共函数都有类型注解和 Google 风格 docstring
4. 依赖注入: 使用 FastAPI Depends 注入数据库 Session 和配置
5. 错误处理: 统一的异常处理中间件和错误响应格式
6. 调用现有模块: 
   - src/storage.py - 数据库操作
   - src/analyzer.py - AI 分析器
   - src/core/pipeline.py - 分析流水线
   - data_provider/base.py - 数据获取器

运行前端 npm run dev 验证页面