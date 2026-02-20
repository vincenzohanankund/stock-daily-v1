import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  WatchlistItem,
  WatchlistMutationResponse,
} from '../types/analysis';

export const stocksApi = {
  getWatchlist: async (
    includeQuote = true, 
    refreshAsync = false
  ): Promise<{
    total: number;
    items: WatchlistItem[];
    refreshTask?: {
      taskId: string;
      status: string;
      completed: boolean;
      progressDone: number;
      progressTotal: number;
      error?: string;
    };
  }> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/stocks/watchlist', {
      params: { 
        include_quote: includeQuote,
        refresh_async: refreshAsync
      },
    });

    const data = toCamelCase<{ 
      total: number; 
      items: WatchlistItem[];
      refreshTask?: any;
    }>(response.data);
    
    return {
      total: data.total,
      items: (data.items || []).map((item) => toCamelCase<WatchlistItem>(item)),
      refreshTask: data.refreshTask ? toCamelCase(data.refreshTask) : undefined
    };
  },

  getRefreshStatus: async (taskId?: string): Promise<{
    taskId: string;
    status: string;
    completed: boolean;
    progressDone: number;
    progressTotal: number;
    error?: string;
  }> => {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/stocks/watchlist/refresh', {
      params: taskId ? { task_id: taskId } : undefined
    });
    return toCamelCase(response.data);
  },

  addWatchlistStock: async (stockCode: string): Promise<WatchlistMutationResponse> => {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/stocks/watchlist', {
      stock_code: stockCode,
    });
    return toCamelCase<WatchlistMutationResponse>(response.data);
  },

  removeWatchlistStock: async (stockCode: string): Promise<WatchlistMutationResponse> => {
    const response = await apiClient.delete<Record<string, unknown>>(`/api/v1/stocks/watchlist/${stockCode}`);
    return toCamelCase<WatchlistMutationResponse>(response.data);
  },

  replaceWatchlist: async (stockCodes: string[]): Promise<WatchlistMutationResponse> => {
    const response = await apiClient.put<Record<string, unknown>>('/api/v1/stocks/watchlist', {
      stock_codes: stockCodes,
    });
    return toCamelCase<WatchlistMutationResponse>(response.data);
  },
};
