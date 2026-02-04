import apiClient from './index';
import type {AnalysisRequest, AnalysisResult} from '../types/analysis';

// Helper to map snake_case to camelCase
const mapAnalysisResult = (data: any): AnalysisResult => {
    // Handle case where data might already be in the expected format (e.g. from mock)
    if (data.stockCode && data.summary?.analysisSummary) return data;

    const report = data.report || {};
    const summary = report.summary || {};

    return {
        queryId: data.query_id || data.queryId,
        stockCode: data.stock_code || data.stockCode,
        stockName: data.stock_name || data.stockName,
        summary: {
            analysisSummary: summary.analysis_summary || summary.analysisSummary,
            operationAdvice: summary.operation_advice || summary.operationAdvice,
            trendPrediction: summary.trend_prediction || summary.trendPrediction,
            sentimentScore: summary.sentiment_score || summary.sentimentScore,
        },
        createdAt: data.created_at || data.createdAt,
    };
};

export const analysisApi = {
    analyze: async (data: AnalysisRequest): Promise<AnalysisResult> => {
        // Map request to snake_case
        const requestData = {
            stock_code: data.stockCode,
            report_type: data.reportType || 'detailed',
        };

        const response = await apiClient.post<any>('/api/v1/analysis/analyze', requestData);
        // Determine if wrapped in ApiResponse or direct
        const responseData = response.data;
        // Spec says 200 OK returns AnalysisResult directly?
        // Spec: responses.200.content.application/json.schema.$ref = AnalysisResult
        // So it might return the object directly.

        return mapAnalysisResult(responseData);
    },

    getStatus: async (taskId: string) => {
        return apiClient.get(`/api/v1/analysis/status/${taskId}`);
    },
};
