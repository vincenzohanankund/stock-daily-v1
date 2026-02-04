import apiClient from './index';
import type {
  HistoryListResponse,
  HistoryItem,
  HistoryFilters,
  AnalysisReport,
  ReportSummary,
  ReportStrategy,
  ReportDetails,
  ReportMeta,
} from '../types/analysis';

// ============ 数据映射函数 ============

/** 将 snake_case API 响应映射为 camelCase 类型 */
const mapHistoryItem = (data: Record<string, unknown>): HistoryItem => ({
  queryId: (data.query_id || data.queryId) as string,
  stockCode: (data.stock_code || data.stockCode) as string,
  stockName: (data.stock_name || data.stockName) as string | undefined,
  reportType: (data.report_type || data.reportType) as string | undefined,
  sentimentScore: (data.sentiment_score || data.sentimentScore) as number | undefined,
  operationAdvice: (data.operation_advice || data.operationAdvice) as string | undefined,
  createdAt: (data.created_at || data.createdAt) as string,
});

const mapHistoryListResponse = (data: Record<string, unknown>): HistoryListResponse => ({
  total: data.total as number,
  page: data.page as number,
  limit: data.limit as number,
  items: ((data.items as Record<string, unknown>[]) || []).map(mapHistoryItem),
});

const mapReportMeta = (data: Record<string, unknown>): ReportMeta => ({
  queryId: (data.query_id || data.queryId) as string,
  stockCode: (data.stock_code || data.stockCode) as string,
  stockName: (data.stock_name || data.stockName) as string,
  reportType: (data.report_type || data.reportType || 'detailed') as 'simple' | 'detailed',
  createdAt: (data.created_at || data.createdAt) as string,
  currentPrice: (data.current_price || data.currentPrice) as number | undefined,
  changePct: (data.change_pct || data.changePct) as number | undefined,
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

// ============ API 接口 ============

export interface GetHistoryListParams extends HistoryFilters {
  page?: number;
  limit?: number;
}

export const historyApi = {
  /**
   * 获取历史分析列表
   * @param params 筛选和分页参数
   */
  getList: async (params: GetHistoryListParams = {}): Promise<HistoryListResponse> => {
    const { stockCode, startDate, endDate, page = 1, limit = 20 } = params;

    const queryParams: Record<string, string | number> = { page, limit };
    if (stockCode) queryParams.stock_code = stockCode;
    if (startDate) queryParams.start_date = startDate;
    if (endDate) queryParams.end_date = endDate;

    const response = await apiClient.get<Record<string, unknown>>('/api/v1/history', {
      params: queryParams,
    });

    return mapHistoryListResponse(response.data);
  },

  /**
   * 获取历史报告详情
   * @param queryId 分析记录唯一标识
   */
  getDetail: async (queryId: string): Promise<AnalysisReport> => {
    const response = await apiClient.get<Record<string, unknown>>(`/api/v1/history/${queryId}`);
    return mapAnalysisReport(response.data);
  },
};
