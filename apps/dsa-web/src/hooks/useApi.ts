import { useState, useCallback } from 'react';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

export function useApi<T, P extends any[]>(
  apiFunction: (...args: P) => Promise<T>
) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async (...args: P) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const result = await apiFunction(...args);
      setState({ data: result, loading: false, error: null });
      return result;
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      setState({ data: null, loading: false, error: err });
      throw err;
    }
  }, [apiFunction]);

  return { ...state, execute };
}
