import axios from 'axios';

export type ApiError = Error & {
  status?: number;
  code?: string;
  detail?: unknown;
};

export const createApiError = (
  message: string,
  status?: number,
  code?: string,
  detail?: unknown
): ApiError => {
  const error = new Error(message) as ApiError;
  error.status = status;
  error.code = code;
  error.detail = detail;
  return error;
};

// 统一错误映射，区分网络错误 / 4xx / 5xx
export const normalizeApiError = (error: unknown): ApiError => {
  if (error instanceof Error && 'status' in error) {
    return error as ApiError;
  }

  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const data = error.response?.data as { error?: string; message?: string; detail?: unknown } | undefined;

    if (!status) {
      return createApiError('网络连接失败，请检查服务状态或稍后重试');
    }

    if (status >= 500) {
      return createApiError(data?.message || '服务异常，请稍后重试', status, data?.error, data?.detail);
    }

    if (status >= 400) {
      return createApiError(data?.message || '请求参数有误，请检查输入', status, data?.error, data?.detail);
    }
  }

  if (error instanceof Error) {
    return createApiError(error.message);
  }

  return createApiError('未知错误，请稍后重试');
};
