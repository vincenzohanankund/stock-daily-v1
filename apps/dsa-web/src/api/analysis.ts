import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  AnalysisRequest,
  AnalysisResult,
  AnalysisReport,
  TaskStatus,
} from '../types/analysis';

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

    const result = toCamelCase<AnalysisResult>(response.data);

    // 确保 report 字段正确转换
    if (result.report) {
      result.report = toCamelCase<AnalysisReport>(result.report);
    }

    return result;
  },

  /**
   * 获取异步任务状态
   * @param taskId 任务 ID
   */
  getStatus: async (taskId: string): Promise<TaskStatus> => {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/analysis/status/${taskId}`
    );

    const data = toCamelCase<TaskStatus>(response.data);

    // 确保嵌套的 result 也被正确转换
    if (data.result) {
      data.result = toCamelCase<AnalysisResult>(data.result);
      if (data.result.report) {
        data.result.report = toCamelCase<AnalysisReport>(data.result.report);
      }
    }

    return data;
  },
};
