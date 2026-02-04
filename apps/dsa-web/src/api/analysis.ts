import apiClient from './index';
import type {
  AnalysisRequest,
  AnalysisResult,
  AnalysisReport,
  ReportMeta,
  ReportSummary,
  ReportStrategy,
  ReportDetails,
  TaskStatus,
} from '../types/analysis';

// ============ 数据映射函数 ============

const mapReportMeta = (data: Record<string, unknown>): ReportMeta => ({
  queryId: (data.query_id || data.queryId || '') as string,
  stockCode: (data.stock_code || data.stockCode || '') as string,
  stockName: (data.stock_name || data.stockName || '') as string,
  reportType: (data.report_type || data.reportType || 'detailed') as 'simple' | 'detailed',
  createdAt: (data.created_at || data.createdAt || '') as string,
});

const mapReportSummary = (data: Record<string, unknown>): ReportSummary => ({
  analysisSummary: (data.analysis_summary || data.analysisSummary || '') as string,
  operationAdvice: (data.operation_advice || data.operationAdvice || '') as string,
  trendPrediction: (data.trend_prediction || data.trendPrediction || '') as string,
  sentimentScore: (data.sentiment_score || data.sentimentScore || 50) as number,
  sentimentLabel: (data.sentiment_label || data.sentimentLabel) as ReportSummary['sentimentLabel'],
});

const mapReportStrategy = (data: Record<string, unknown>): ReportStrategy => ({
  idealBuy: (data.ideal_buy || data.idealBuy) as string | undefined,
  secondaryBuy: (data.secondary_buy || data.secondaryBuy) as string | undefined,
  stopLoss: (data.stop_loss || data.stopLoss) as string | undefined,
  takeProfit: (data.take_profit || data.takeProfit) as string | undefined,
});

const mapReportDetails = (data: Record<string, unknown>): ReportDetails => ({
  newsContent: (data.news_content || data.newsContent) as string | undefined,
  rawResult: (data.raw_result || data.rawResult) as Record<string, unknown> | undefined,
  contextSnapshot: (data.context_snapshot || data.contextSnapshot) as Record<string, unknown> | undefined,
});

const mapAnalysisReport = (data: Record<string, unknown>): AnalysisReport => {
  const meta = (data.meta || {}) as Record<string, unknown>;
  const summary = (data.summary || {}) as Record<string, unknown>;
  const strategy = data.strategy as Record<string, unknown> | undefined;
  const details = data.details as Record<string, unknown> | undefined;

  return {
    meta: mapReportMeta(meta),
    summary: mapReportSummary(summary),
    strategy: strategy ? mapReportStrategy(strategy) : undefined,
    details: details ? mapReportDetails(details) : undefined,
  };
};

const mapAnalysisResult = (data: Record<string, unknown>): AnalysisResult => {
  // 如果数据已经是预期格式（如来自 mock），直接返回
  if (data.report && typeof data.report === 'object') {
    return {
      queryId: (data.query_id || data.queryId) as string,
      stockCode: (data.stock_code || data.stockCode) as string,
      stockName: (data.stock_name || data.stockName) as string,
      report: mapAnalysisReport(data.report as Record<string, unknown>),
      createdAt: (data.created_at || data.createdAt) as string,
    };
  }

  // 处理旧格式（直接包含 summary 等字段）
  const summary = (data.summary || {}) as Record<string, unknown>;

  return {
    queryId: (data.query_id || data.queryId || '') as string,
    stockCode: (data.stock_code || data.stockCode || '') as string,
    stockName: (data.stock_name || data.stockName || '') as string,
    report: {
      meta: {
        queryId: (data.query_id || data.queryId || '') as string,
        stockCode: (data.stock_code || data.stockCode || '') as string,
        stockName: (data.stock_name || data.stockName || '') as string,
        reportType: (data.report_type || data.reportType || 'detailed') as 'simple' | 'detailed',
        createdAt: (data.created_at || data.createdAt || '') as string,
      },
      summary: mapReportSummary(summary),
      strategy: data.strategy ? mapReportStrategy(data.strategy as Record<string, unknown>) : undefined,
      details: data.details ? mapReportDetails(data.details as Record<string, unknown>) : undefined,
    },
    createdAt: (data.created_at || data.createdAt) as string,
  };
};

// ============ API 接口 ============

export const analysisApi = {
  /**
   * 触发股票分析
   * @param data 分析请求参数
   */
  analyze: async (data: AnalysisRequest): Promise<AnalysisResult> => {
    const requestData = {
      stock_code: data.stockCode,
      report_type: data.reportType || 'detailed',
      force_refresh: data.forceRefresh || false,
      async_mode: data.asyncMode || false,
    };

    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/analysis/analyze',
      requestData
    );

    return mapAnalysisResult(response.data);
  },

  /**
   * 获取异步任务状态
   * @param taskId 任务 ID
   */
  getStatus: async (taskId: string): Promise<TaskStatus> => {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/analysis/status/${taskId}`
    );

    const data = response.data;
    return {
      taskId: (data.task_id || data.taskId) as string,
      status: (data.status as TaskStatus['status']) || 'pending',
      progress: data.progress as number | undefined,
      result: data.result ? mapAnalysisResult(data.result as Record<string, unknown>) : undefined,
      error: data.error as string | undefined,
    };
  },
};
