import apiClient from './index';

export const historyApi = {
  getList: async (page = 1, pageSize = 10) => {
    return apiClient.get('/api/v1/history', { params: { page, limit: pageSize } });
  },

  getDetail: async (id: string) => {
    return apiClient.get(`/api/v1/history/${id}`);
  },
};
